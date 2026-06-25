# WindForcePlugin Explained

This document explains how `WindForcePlugin.cc` works at a high level and then walks through the code in smaller pieces. It is meant to be a reference you can ask questions against. For example: "I do not understand section 4" or "why is relative wind calculated that way?"

Related files:

- `src/ardupilot_gazebo/src/WindForcePlugin.cc`
- `src/ardupilot_gazebo/models/iris_with_ardupilot/model.sdf`
- `src/test/wind_controller.py`
- `src/test/wind_status.py`
- `src/test/wind_operator_ui.py`

## 1. What The Plugin Does

`WindForcePlugin` adds an artificial wind force to the simulated drone in Gazebo.

It does not change ArduPilot's internal wind estimate directly. Instead, it applies a physical force to a Gazebo link, currently `iris::base_link`. ArduPilot then reacts to the vehicle being pushed around, just like it would react to any other simulated external force.

Simple mental model:

```text
wind_controller.py
      |
      | ZMQ/msgpack command
      v
WindForcePlugin inside Gazebo
      |
      | computes wind force every Gazebo update
      v
iris::base_link gets pushed
      |
      v
ArduPilot sees the vehicle move/drift and tries to correct
```

## 2. Where It Is Loaded

The plugin is loaded from the Iris model SDF:

```xml
<plugin name="wind_force" filename="libWindForcePlugin.so">
  <link_name>iris::base_link</link_name>
  <control_endpoint>tcp://127.0.0.1:5570</control_endpoint>
  <control_topic>wind/control</control_topic>
  <status_endpoint>tcp://*:5571</status_endpoint>
  <status_topic>wind/status</status_topic>
  <status_rate>2</status_rate>
  <speed_knots>0</speed_knots>
  <direction_deg>0</direction_deg>
  <ramp_start_altitude>0</ramp_start_altitude>
  <ramp_end_altitude>100</ramp_end_altitude>
  <air_density>1.225</air_density>
  <drag_coefficient>1.1</drag_coefficient>
  <reference_area>0.12</reference_area>
  <max_force>80</max_force>
</plugin>
```

These values are the plugin's initial settings. Some of them can be changed later by sending commands over ZMQ.

## 3. The Two ZMQ Channels

There are two separate ZMQ paths.

```text
Control path:

src/test/wind_controller.py
  PUB tcp://127.0.0.1:5570 topic "wind/control"
        |
        v
WindForcePlugin
  SUB connects to tcp://127.0.0.1:5570


Status path:

WindForcePlugin
  PUB binds tcp://*:5571 topic "wind/status"
        |
        v
src/test/wind_status.py
  SUB connects to tcp://127.0.0.1:5571
```

The control channel changes the simulated wind.

The status channel lets you see what the plugin thinks it is doing. The browser UI in `src/test/wind_operator_ui.py` uses both channels: it sends commands on the control channel and reads live status from the status channel.

## 4. Startup Flow

When Gazebo loads the plugin, it calls:

```cpp
void Load(physics::ModelPtr _model, sdf::ElementPtr _sdf)
```

The startup sequence is:

```text
Gazebo loads model
      |
      v
WindForcePlugin::Load()
      |
      +--> remember the Gazebo model
      |
      +--> find the link to push, usually iris::base_link
      |
      +--> read settings from model.sdf
      |
      +--> create ZMQ subscriber for wind commands
      |
      +--> create ZMQ publisher for wind status
      |
      +--> register OnUpdate() to run every simulation update
```

The most important line conceptually is this:

```cpp
this->updateConnection = event::Events::ConnectWorldUpdateBegin(...);
```

That tells Gazebo: "call my `OnUpdate()` function every simulation tick."

## 5. Main Runtime Loop

After startup, almost everything happens inside:

```cpp
void OnUpdate(const common::UpdateInfo &info)
```

Each Gazebo update does this:

```text
OnUpdate()
  |
  +--> ReceiveControl()
  |      Read any new ZMQ wind commands.
  |
  +--> Read current altitude.
  |
  +--> Convert target wind from knots to meters/second.
  |
  +--> Scale wind based on altitude ramp.
  |
  +--> Convert direction degrees into an XY velocity vector.
  |
  +--> Compare wind velocity to vehicle velocity.
  |
  +--> Compute force magnitude.
  |
  +--> Apply force to the selected Gazebo link.
  |
  +--> Publish status at status_rate Hz.
```

That is the whole plugin in one picture.

## 6. Wind Speed And Altitude Ramp

The configured wind speed is `targetWindKnots`.

The plugin converts knots to meters per second:

```cpp
knots * 0.514444
```

Then it scales the wind by altitude:

```text
below ramp_start_altitude: wind scale = 0
at ramp_end_altitude:      wind scale = 1
between them:              linearly interpolated
```

With the current SDF:

```text
ramp_start_altitude = 0 m
ramp_end_altitude   = 100 m
```

That means:

```text
Altitude 0 m:    0% of target wind
Altitude 50 m:  50% of target wind
Altitude 100 m: 100% of target wind
Above 100 m:    100% of target wind
```

Example with a target of 20 knots:

```text
Altitude 0 m:    0 knots applied
Altitude 50 m:  10 knots applied
Altitude 100 m: 20 knots applied
```

## 7. Wind Direction

Direction is in the Gazebo world XY plane:

```text
0 degrees   = +X
90 degrees  = +Y
180 degrees = -X
270 degrees = -Y
```

The plugin converts the angle into a velocity vector:

```cpp
windVelocity.x = windSpeed * cos(directionRad)
windVelocity.y = windSpeed * sin(directionRad)
windVelocity.z = 0
```

Diagram:

```text
                 +Y
                  ^
                  | 90 deg
                  |
180 deg <---------+---------> 0 deg / +X
                  |
                  | 270 deg
                  v
                 -Y
```

There is no vertical wind in this plugin. Wind is always horizontal.

## 8. Relative Wind

This is one of the most important lines:

```cpp
relativeWind = windVelocity - this->link->WorldLinearVel();
```

Meaning:

```text
relative wind = wind movement through the world - vehicle movement through the world
```

Why this matters:

- If the drone is hovering still and the wind is 10 m/s, relative wind is about 10 m/s.
- If the drone is flying with the wind at 10 m/s, relative wind is closer to 0.
- If the drone is flying into the wind, relative wind is larger.

The force is based on this relative wind, not just the commanded wind speed.

## 9. Force Calculation

The plugin uses a simple drag-style equation:

```cpp
forceMagnitude =
  0.5 * airDensity * dragCoefficient * referenceArea
  * relativeSpeed * relativeSpeed;
```

In shorter notation:

```text
force = 0.5 * rho * Cd * A * v^2
```

Where:

```text
rho = air_density
Cd  = drag_coefficient
A   = reference_area
v   = relative wind speed
```

Then it clamps the force:

```cpp
forceMagnitude = Clamp(forceMagnitude, 0.0, maxForce);
```

With the current SDF, `max_force` is `80 N`, so the plugin will not apply more than 80 newtons.

Finally, it applies the force in the relative wind direction:

```cpp
force = relativeWind.Normalized() * forceMagnitude;
this->link->AddForce(force);
```

Diagram:

```text
windVelocity -------->

droneVelocity ---->

relativeWind = windVelocity - droneVelocity

force is applied in the relativeWind direction
```

## 10. Control Messages

`wind_controller.py` sends msgpack maps like this:

```python
{
    "speed_knots": 20.0,
    "direction_deg": 90.0,
    "ramp_start_altitude": 0.0,
    "ramp_end_altitude": 100.0,
}
```

Optional tuning fields:

```python
{
    "drag_coefficient": 1.1,
    "reference_area": 0.12,
    "max_force": 80.0,
}
```

The plugin only changes fields that are present in the command. Missing fields keep their previous values.

Example command:

```bash
python3 src/test/wind_controller.py --knots 20 --direction 90
```

This means:

```text
Target wind: 20 knots
Direction: +Y
Ramp: default 0 to 100 m
```

## 11. Status Messages

The plugin publishes status messages with these fields:

```text
altitude_m
actual_wind_knots
actual_wind_mps
target_wind_knots
direction_deg
ramp_start_altitude
ramp_end_altitude
relative_speed_mps
force_n
drag_coefficient
reference_area
received_control_count
```

You can view them with:

```bash
python3 src/test/wind_status.py
```

Important fields:

- `target_wind_knots`: the wind requested by the controller.
- `actual_wind_knots`: the wind after altitude ramp scaling.
- `relative_speed_mps`: wind speed relative to the drone link.
- `force_n`: the force currently being applied.
- `received_control_count`: how many valid control messages were received.

If `target_wind_knots` is nonzero but `actual_wind_knots` is low, the drone may be below the ramp altitude.

If `actual_wind_knots` is nonzero but `force_n` is zero, the relative wind may be nearly zero or something is wrong with the target link.


## 12. Browser Operator UI

The browser UI is a convenience wrapper around the same ZMQ messages used by `wind_controller.py` and `wind_status.py`.

Run it from the host when you want to open the page directly in the host browser:

```bash
source /home/user/new/.venv/bin/activate
cd ~/git/gz11
python3 src/test/wind_operator_ui.py --listen-port 8090
```

Then open:

```text
http://127.0.0.1:8090/
```

The UI fields do not change Gazebo until you click `Send`. The `Commands` value in the status panel should increase when the plugin receives the command.

The UI uses compass headings: `0=N`, `90=E`, `180=S`, and `270=W`. Internally it converts those headings to the Gazebo world direction used by the plugin.

`Live` mode sends automatically while you change sliders or inputs. It is rate-limited so dragging a slider feels responsive without flooding Gazebo. `Send` is still available for one manual update.

`Record` captures every wind command that is sent by `Send`, `Live`, or `Zero Wind`. Click `Stop` to save the captured commands as a JSON scenario file. If the native save dialog is unavailable, the UI saves under `~/gz11/wind_scenarios/`; if the server save fails, the browser downloads the file instead. `Play` opens a file picker for that JSON file and replays the commands with the same timing.

The ramp is altitude-based:

```text
current altitude < ramp_start_altitude:  no wind
between start and end:                   partial wind
current altitude >= ramp_end_altitude:   full target wind
```

To apply full wind immediately, set:

```text
ramp_start_altitude = 0
ramp_end_altitude   = 0
```

The UI also shows the tuning relationship:

```text
CdA = drag_coefficient * reference_area
force = 0.5 * air_density * CdA * relative_speed^2
```

`max_force` is a clamp on the final applied force. If the formula calculates `120 N` and `max_force` is `80 N`, the plugin applies `80 N`.


## 13. Important Details And Caveats

This is a simple physical wind approximation, not a full atmospheric model.

It applies one force to one link:

```xml
<link_name>iris::base_link</link_name>
```

It does not model:

- turbulence
- gusts
- vertical wind
- different forces on individual rotors
- aerodynamic lift/drag surfaces beyond this one force
- ArduPilot's internal `SIM_WIND_*` parameters

It is still useful because it physically pushes the vehicle in Gazebo, which lets you test controller behavior under a repeatable disturbance.

## 14. Quick Troubleshooting

If wind does not seem to affect the drone:

1. Check that `libWindForcePlugin.so` was built and is loadable by Gazebo.
2. Check Gazebo console output for `[WindForcePlugin] Loaded`.
3. Run `wind_status.py` and confirm messages arrive.
4. Run `wind_controller.py` and check that `received_control_count` increases.
5. Check `actual_wind_knots`. If it is near zero, the altitude ramp may be reducing the wind.
6. Check `force_n`. If it is zero, either actual wind is zero or relative speed is near zero.
7. Increase `--drag-coefficient`, `--reference-area`, or `--max-force` carefully if the effect is too small.

Example stronger command:

```bash
python3 src/test/wind_controller.py \
  --knots 30 \
  --direction 90 \
  --drag-coefficient 2.0 \
  --reference-area 0.3 \
  --max-force 150
```

## 15. Questions To Ask From Here

Good follow-up questions:

- "Explain section 8 with numbers."
- "Why do we use relative wind instead of target wind?"
- "What does `reference_area` mean for a drone?"
- "How do I make the wind start only above 50 meters?"
- "How can I add gusts?"
- "How can I make wind come from a direction instead of blow toward a direction?"
- "How do I verify this is actually pushing the drone?"

