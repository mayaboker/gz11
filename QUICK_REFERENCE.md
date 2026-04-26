# Quick Reference Card

## Essential Commands

### New computer

On the host:

```bash
xhost +
```

### New container

Inside the container before running anything... 

```bash
ln -s /workspace/.bash_aliases ~/.bash_aliases
```

### Fast test
```bash
pip install -r requirements.txt
```

```bash
gazebo --verbose /workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world
```

```bash
# On the host, start ArduPilot SITL with the Gazebo frame
./Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map -w
```

```bash
/workspace/src/build/camera2zmq /gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image tcp://*:5567 camera/image
```

```bash
python3 /workspace/src/test/test_camera_msgpack.py
```

### Start Services

```bash
# 1. Start Gazebo
gazebo --verbose /workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world

# 1b. Start ArduPilot SITL on the host
./Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map -w

# 2. Start Image Publisher
/workspace/src/build/camera2zmq 
        argv[1] = camera_topic (default = "/gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image")
        argv[2] = zmq_address (default = "tcp://*:5556")
        argv[3] = g_msgpack_topic (default = "camera/image")

# 3. View Published Image (Python)
python3 /workspace/src/test/test_camera_msgpack.py

# 4. View Published Camera (C++)
/workspace/src/demos/build/sub_img_msgpack

# 5. View model pose from PublishPoseZMQPlugin
python3 /workspace/src/test/test_pose_msgpack.py
```

## Camera2ZMQ

```bash
# Default
/workspace/src/build/camera2zmq

# Custom topic
/workspace/src/build/camera2zmq \
  ["/gazebo/path/to/camera"] \
  ["zmq address like tcp://*:5556"] \
  "[g_msgpack_topic]
```


## Gimbal Control
The source code exists but the library is not built for now. So it doesn't work with the gazebo topic publish because there is no compiled plugin.

```bash
# Direct Gazebo (radians) - didn't work
gz topic -p /gazebo/default/iris_demo/gimbal_tilt_cmd \
  -m gazebo.msgs.GzString -v 'data: "-1.57"'

# Via MAVLink
python3 /workspace/src/test/gimbal_bridge.py  # Terminal 1
MAV> long DO_MOUNT_CONTROL -90 0 0 0 0 0 2  # Terminal 2
```

## Autonomous Flight

This command should be run from the  host and not from the docker because there is no pymavlink installed in the docker:

```bash
python3 $PROJECT/test/fly_to_100m.py
```

```bash
# Explicit MAVLink endpoint
python3 /workspace/src/test/fly_to_100m.py --host 127.0.0.1 --port 14550
```

```bash
# Shorter test flight
python3 /workspace/src/test/fly_to_100m.py --port 14550 --altitude 20 --hold-seconds 60
```

Notes:
- `fly_to_100m.py` now accepts `--host`, `--port`, `--altitude`, and `--hold-seconds`
- it waits for `GUIDED` mode to become active before arming
- it prints `STATUSTEXT` / command ACK feedback while arming and taking off
- if `ARMING_CHECK` readback times out, it warns and continues instead of aborting immediately

Manual MAVProxy fallback:

```bash
mode guided
param set ARMING_CHECK 0
arm throttle
takeoff 3
```

## Pose Receiver

```bash
# Subscribe to the model pose published by PublishPoseZMQPlugin
python3 /workspace/src/test/test_pose_msgpack.py
```

```bash
# Print Euler angles in degrees
python3 /workspace/src/test/test_pose_msgpack.py --degrees
```

```bash
# Use a different publisher endpoint or rate
python3 /workspace/src/test/test_pose_msgpack.py --host 127.0.0.1 --port 5556 --topic camera/pose --rate 2
```

Notes:
- the pose receiver listens for the multipart ZMQ topic `camera/pose`
- the payload is `x, y, z, roll, pitch, yaw`
- `z` is the Gazebo world-frame height of the `iris_demo` model, not a MAVLink altitude estimate
- do not use the same ZMQ port for both pose and camera publishers at the same time

## Gazebo Topics

```bash
# List topics
gz topic -l

# Echo topic
gz topic -e /gazebo/default/iris_demo/gimbal_tilt_status

# Publish topic - didn't work
gz topic -p /gazebo/default/iris_demo/gimbal_tilt_cmd \
  -m gazebo.msgs.GzString -v 'data: "0"'

# Model info
gz model -m iris_demo -i
```

## MAVProxy Gimbal Commands -didn't work

```bash
# Point down
MAV> long DO_MOUNT_CONTROL -90 0 0 0 0 0 2

# Point forward
MAV> long DO_MOUNT_CONTROL 0 0 0 0 0 0 2

# Point 45° down
MAV> long DO_MOUNT_CONTROL -45 0 0 0 0 0 2
```

## Build Commands

```bash
# Build camera2zmq
cd /workspace/src/build && cmake .. && make camera2zmq

# Build subscriber
cd /workspace/src/demos/build && cmake .. && make sub_img_msgpack
```

## Package Installation

```bash
# APT packages
sudo apt-get install -y python3-zmq python3-opencv python3-numpy python3-pip

# PIP packages
pip3 install pymavlink
```

## Angle Conversions

| Degrees | Radians | Description |
|---------|---------|-------------|
| 0° | 0 | Forward |
| -45° | -0.785 | 45° down |
| -90° | -1.57 | Straight down |
| 90° | 1.57 | Straight up |

## File Locations

| Item | Path |
|------|------|
| Camera publisher | `/workspace/src/build/camera2zmq` |
| C++ subscriber | `/workspace/src/demos/build/sub_img_msgpack` |
| Python subscriber | `/workspace/src/test/test_camera_msgpack.py` |
| Flight script | `/workspace/src/test/fly_to_100m.py` |
| Pose receiver | `/workspace/src/test/test_pose_msgpack.py` |
| Gimbal bridge | `/workspace/src/test/gimbal_bridge.py` |
| Full guide | `/workspace/SETUP_GUIDE.md` |

