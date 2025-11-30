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
/workspace/src/build/camera2zmq /gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image tcp://*:5567 camera/image
```

```bash
python3 /workspace/src/test/test_camera_msgpack.py
```

### Start Services

```bash
# 1. Start Gazebo
gazebo --verbose /workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world

# 2. Start Image Publisher
/workspace/src/build/camera2zmq 
        argv[1] = camera_topic (default = "/gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image")
        argv[2] = zmq_address (default = "tcp://*:5556")
        argv[3] = g_msgpack_topic (default = "camera/image")

# 3. View Published Image (Python)
python3 /workspace/test_camera_msgpack.py

# 4. View Published Camera (C++)
/workspace/src/demos/build/sub_img_msgpack
```

## Camera2ZMQ

```bash
# Default
/workspace/src/build/camera2zmq

# Custom topic
/workspace/src/build/camera2zmq \
  "/gazebo/path/to/camera" \
  "tcp://*:5556" \
  "my_camera"
```

## Gimbal Control

```bash
# Direct Gazebo (radians) - didn't work
gz topic -p /gazebo/default/iris_demo/gimbal_tilt_cmd \
  -m gazebo.msgs.GzString -v 'data: "-1.57"'

# Via MAVLink
python3 /workspace/gimbal_bridge.py  # Terminal 1
MAV> long DO_MOUNT_CONTROL -90 0 0 0 0 0 2  # Terminal 2
```

## Autonomous Flight

```bash
python3 /workspace/fly_to_100m.py
```

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
| Gimbal bridge | `/workspace/src/test/gimbal_bridge.py` |
| Full guide | `/workspace/SETUP_GUIDE.md` |

