# Gazebo 9 Wind Plugin Slice

This branch is for the minimal Gazebo 9 / Ubuntu 18.04 wind-control setup. It is not a full project migration.

## Target Environment

- Ubuntu 18.04
- Gazebo 9
- Python 3.6.9
- ArduPilot SITL using the `gazebo-iris` frame


## Container

For this branch, run the Ubuntu 18.04 / Gazebo 9 image instead of the Gazebo 11 container. The working image/container names are:

```text
image:     ubuntu18-gazebo9:latest
container: gz9
```

If using the local launcher, start it from the host:

```bash
/home/user/18.04/gz9/check_windplugin_gz9.run
```

Then enter the running container from another host terminal:

```bash
docker exec -it gz9 bash
```

Inside the container, confirm the expected versions:

```bash
gazebo --version
python3 --version
```

Expected major versions are Gazebo 9 and Python 3.6.x.

## Dependencies

On Ubuntu 18.04, install the Gazebo/plugin build dependencies and Python runtime pieces before building:

```bash
sudo apt-get update
sudo apt-get install -y \
  gazebo9 \
  libgazebo9-dev \
  libzmq3-dev \
  libmsgpack-dev \
  python3-zmq \
  python3-msgpack
```

For the wind plugin and wind UI, do not run a broad `pip install -r requirements.txt` as the first check. On Python 3.6, modern `opencv-python` may fall back to a very slow source build. OpenCV is only needed for camera tests, not for the wind plugin.

If camera tests are needed later, prefer apt packages in this container:

```bash
sudo apt-get install -y python3-opencv python3-numpy
```

If `python3-msgpack` is not available in your package setup, install only the wind UI runtime pieces in your Python 3.6 environment:

```bash
python3 -m pip install msgpack pyzmq
```

`libzmq3-dev` provides the ZeroMQ C library, but some Ubuntu 18.04 setups do not provide a `cppzmq-dev` package for the C++ header `zmq.hpp`.

If CMake/build fails with:

```text
fatal error: zmq.hpp: No such file or directory
```

install the cppzmq header manually. One common approach is to copy `zmq.hpp` from the upstream cppzmq project into a system include directory:

```bash
sudo cp zmq.hpp /usr/local/include/zmq.hpp
```

or place it in a project include directory and add that directory to the compiler include path. The wind plugin only needs the header plus `libzmq3-dev`; there is no separate cppzmq library to link.

## Included Pieces

The required pieces are:

- `src/ardupilot_gazebo/src/WindForcePlugin.cc`
- `src/ardupilot_gazebo/CMakeLists.txt`
- `src/ardupilot_gazebo/models/iris_with_ardupilot/model.sdf`
- `src/ardupilot_gazebo/worlds/iris_arducopter_runway.world`
- `src/test/wind_operator_ui.py`
- `src/test/wind_controller.py`
- `src/test/wind_status.py`

The UI is optional but recommended. `wind_controller.py` and `wind_status.py` are useful command-line fallbacks.

## Compatibility Notes

`WindForcePlugin.cc` uses compatibility wrappers for older and newer `cppzmq` headers:

- older Ubuntu 18 style APIs: `socket.recv(&msg, flags)` and `socket.send(msg, flags)`
- newer APIs: `recv_result_t`, `recv_flags`, and `send_flags`

`wind_operator_ui.py` is Python 3.6-compatible. It does not use `http.server.ThreadingHTTPServer`, which only exists in newer Python versions.

## Build Only The Wind Plugin

Build the wind plugin target only. Do not run a plain `make` / full build for this minimal gz9 slice, because unrelated plugins such as `PublishPoseZMQPlugin` may still use newer cppzmq APIs on Ubuntu 18.04.

From inside the `gz9` container:

```bash
cd /workspace/src/ardupilot_gazebo
mkdir -p build-gz9
cd build-gz9
cmake ..
make WindForcePlugin -j$(nproc)
```

Equivalent CMake command:

```bash
cmake --build . --target WindForcePlugin
```

Make sure Gazebo can find the built plugin:

```bash
export GAZEBO_PLUGIN_PATH=/workspace/src/ardupilot_gazebo/build-gz9:$GAZEBO_PLUGIN_PATH
export GAZEBO_MODEL_PATH=/workspace/src/ardupilot_gazebo/models:$GAZEBO_MODEL_PATH
```

If you install the plugins instead, use the install path configured by CMake/Gazebo.

## Run The Example World

For the first plugin check, `gzserver` is enough. The full Gazebo GUI can fail in Docker if OpenGL/GLX is not configured correctly.

```bash
gzserver --verbose /workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world
```

Check the Gazebo console for:

```text
[WindForcePlugin] Loaded
```

The example Iris model loads:

```xml
<plugin name="wind_force" filename="libWindForcePlugin.so">
```

from:

```text
src/ardupilot_gazebo/models/iris_with_ardupilot/model.sdf
```

If `gzserver` fails with GLX/OpenGL errors such as `GLXBadContext`, install software rendering support and run it through Xvfb:

```bash
sudo apt-get update
sudo apt-get install -y libgl1-mesa-dri libgl1-mesa-glx mesa-utils xvfb

export LIBGL_ALWAYS_SOFTWARE=1
xvfb-run -s "-screen 0 1280x1024x24" \
  gzserver --verbose /workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world
```

## Run The Operator UI

Run the UI on port `8091` for the Gazebo 9 check. This can run on the host or inside the container as long as the ZMQ endpoints are reachable.

```bash
cd /workspace
python3 src/test/wind_operator_ui.py --listen-port 8091
```

Open from the host browser:

```text
http://127.0.0.1:8091/
```

If the port is already occupied, the UI prints the address and suggests checking the owner with:

```bash
lsof -iTCP:8091 -sTCP:LISTEN
```

Use `Live` when you want slider changes to be sent immediately. Use `Send` for one manual update.

## ZMQ Endpoints

The plugin subscribes for commands on:

```text
tcp://127.0.0.1:5570 topic wind/control
```

The plugin publishes status on:

```text
tcp://*:5571 topic wind/status
```

The UI expects the same defaults.

## Immediate Wind Test

To apply full wind immediately, use:

```text
Ramp start m = 0
Ramp end m   = 0
```

Then set wind speed and direction, and click `Send` or enable `Live`.

Command-line equivalent:

```bash
python3 src/test/wind_controller.py \
  --knots 20 \
  --direction 90 \
  --ramp-start-altitude 0 \
  --ramp-end-altitude 0 \
  --rate 0
```

Watch status from another shell in the same container:

```bash
docker exec -it gz9 bash
cd /workspace
python3 src/test/wind_status.py
```

A successful minimal check is:

```text
gz9 container -> build WindForcePlugin -> gzserver loads plugin -> UI sends command -> status receives command
```

## Force Model

The plugin applies one horizontal force to `iris::base_link`:

```text
force = 0.5 * air_density * drag_coefficient * reference_area * relative_speed^2
```

Then the result is clamped by:

```text
max_force
```

Default tuning values:

```text
air_density      = 1.225
drag_coefficient = 1.1
reference_area   = 0.12
max_force        = 80 N
```

## What This Branch Does Not Migrate

This branch does not attempt to migrate all tools, demos, camera bridges, or unrelated plugins to Gazebo 9. The goal is only:

- the wind force plugin
- the Iris model/world that loads it
- the Python 3.6-compatible wind operator UI
