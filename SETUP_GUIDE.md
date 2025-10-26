# Gazebo ArduPilot SITL Setup and Tools Guide

## Table of Contents
1. [Troubleshooting ArduPilot Plugin](#troubleshooting-ardupilot-plugin)
2. [Installed Packages](#installed-packages)
3. [Camera2ZMQ Publisher](#camera2zmq-publisher)
4. [Autonomous Flight Script](#autonomous-flight-script)
5. [Gimbal Control](#gimbal-control)
6. [Available Tools](#available-tools)

---

## Troubleshooting ArduPilot Plugin

### Problem: ArduPilot Plugin Binding Error
```
[Err] [ArduPilotPlugin.cc:886] [iris_demo] failed to bind with 127.0.0.1:9002 aborting plugin.
```

### Root Cause
The ArduPilot plugin was being loaded **twice**:
1. Once from `model.sdf` (correct)
2. Once from the world file (incorrect - caused duplicate binding on port 9002)

### Solution
**Plugin should be declared in `model.sdf` ONLY, NOT in the world file.**

#### ✅ Correct World File
```xml
<model name="iris_demo">
  <include>
    <uri>model://iris_with_ardupilot</uri>
  </include>
</model>
```

#### ❌ Incorrect World File
```xml
<model name="iris_demo">
  <include>
    <uri>model://iris_with_ardupilot</uri>
    <plugin name="ardupilot_iris" filename="libArduPilotPlugin.so">
      <vehicle>iris</vehicle>
      <udp_port>14560</udp_port>
    </plugin>
  </include>
</model>
```

### Fixed Files
- `/workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world`

### Check opened ports
```bash
sudo netstat -tulpn
```
---

## Installed Packages

### Via APT (apt-get)

```bash
# ZMQ and OpenCV for Python
sudo apt-get install -y python3-zmq python3-opencv python3-numpy

# Python package manager
sudo apt-get install -y python3-pip

# MsgPack (C++ library, already installed)
# libmsgpack-dev
```

**Packages installed:**
- `python3-zmq` - Python ZMQ bindings (pyzmq)
- `python3-opencv` - OpenCV for Python
- `python3-numpy` - NumPy arrays
- `python3-pip` - Python package manager
- `python3-setuptools`, `python3-wheel`, `python3-cffi-backend`, `python3-py` (dependencies)

### Via PIP (pip3)

```bash
# MAVLink for drone communication
pip3 install pymavlink

# MsgPack for Python (serialization)
pip3 install msgpack
```

**Packages installed:**
- `pymavlink==2.4.49` - MAVLink communication library
- `msgpack` - MessagePack serialization for Python
- `lxml`, `fastcrc` (dependencies)

### Quick Reinstall Commands

```bash
# Install all dependencies
sudo apt-get update
sudo apt-get install -y python3-zmq python3-opencv python3-numpy python3-pip libmsgpack-dev
pip3 install pymavlink msgpack
```

---

## Camera2ZMQ Publisher

### Overview
Subscribes to Gazebo camera images and publishes them via ZMQ using msgpack format.

### Features
- ✅ Supports BGR_INT8, RGB_INT8, and L_INT8 pixel formats
- ✅ MsgPack serialization
- ✅ Configurable Gazebo topic, ZMQ address, and msgpack topic name
- ✅ Command-line parameters

### Build

```bash
cd /workspace/src/build
cmake ..
make camera2zmq
```

### Usage

```bash
# Default settings
/workspace/src/build/camera2zmq

# With custom parameters
/workspace/src/build/camera2zmq \
  "/gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image" \
  "tcp://*:5556" \
  "camera/image"
```

### Parameters
1. **Gazebo topic** - Camera image topic to subscribe
   - Default: `/gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image`
2. **ZMQ address** - ZMQ publisher bind address
   - Default: `tcp://*:5556`
3. **MsgPack topic** - Topic name in msgpack message
   - Default: `camera/image`

### MsgPack Message Format

```python
{
    'topic': 'camera/image',  # String - topic identifier
    'rows': 240,              # int - image height
    'cols': 320,              # int - image width
    'type': 16,               # int - OpenCV type (16=CV_8UC3)
    'data': [...]             # bytes - image data array
}
```

### OpenCV Type Codes
- `0` = CV_8UC1 (grayscale)
- `16` = CV_8UC3 (3-channel BGR)

### Subscribers

#### C++ Subscriber (MsgPack)
```bash
/workspace/src/demos/build/sub_img_msgpack
```

#### Python Subscriber (MsgPack)
```bash
python3 /workspace/test_camera_msgpack.py
```

#### Old C++ Subscriber (Legacy format - NOT compatible with msgpack)
```bash
/workspace/src/demos/build/sub_img
```

---

## Autonomous Flight Script

### Overview
Python script to autonomously arm, take off to 100m, hold for 5 minutes, and RTL (Return to Launch).

### Location
`/workspace/fly_to_100m.py`

### Features
- ✅ Connects to SITL via MAVLink (127.0.0.1:14550)
- ✅ Disables arming checks
- ✅ Arms vehicle
- ✅ Takes off to 100 meters
- ✅ Holds position for 5 minutes with status updates
- ✅ Returns to launch and lands
- ✅ Emergency RTL on Ctrl+C

### Usage

```bash
# Run the script
python3 /workspace/fly_to_100m.py
```

### Mission Sequence
1. Connect to SITL on UDP 127.0.0.1:14550
2. Set mode to GUIDED
3. Disable arming checks
4. Arm the vehicle
5. Takeoff to 100 meters
6. Hold at 100m for 5 minutes (status every 30 seconds)
7. RTL (Return to Launch)
8. Wait for landing
9. Mission complete

### Sample Output
```
Connecting to vehicle...
Heartbeat from system (system 1 component 1)
Setting mode to GUIDED...
Arming vehicle...
Vehicle ARMED!
Taking off to 100 meters...
Current altitude: 15.2m / Target: 100m
...
✓ Reached 100 meters! Holding for 5 minutes...
Holding at 100.1m - Time remaining: 5:00
Holding at 99.8m - Time remaining: 4:30
...
Initiating RTL (Return to Launch)...
Waiting for landing...
Current altitude: 45.3m
...
Landed!
✓ Mission complete! Drone has returned and landed.
```

---

## Gimbal Control

### Overview
The gimbal is loaded and working! Control it via Gazebo topics or MAVLink.

### Gimbal Status
The gimbal publishes its current angle to:
```
/gazebo/default/iris_demo/gimbal_tilt_status
```

Check it with:
```bash
gz topic -e /gazebo/default/iris_demo/gimbal_tilt_status
```

### Direct Gazebo Control

```bash
# Point gimbal forward (0 radians)
gz topic -p /gazebo/default/iris_demo/gimbal_tilt_cmd \
  -m gazebo.msgs.GzString -v 'data: "0"'

# Point gimbal down 90 degrees (1.57 radians)
gz topic -p /gazebo/default/iris_demo/gimbal_tilt_cmd \
  -m gazebo.msgs.GzString -v 'data: "-1.57"'

# Point gimbal 45 degrees down (-0.785 radians)
gz topic -p /gazebo/default/iris_demo/gimbal_tilt_cmd \
  -m gazebo.msgs.GzString -v 'data: "-0.785"'
```

### Angle Convention (Radians)
- `0` = Forward (horizontal)
- `-1.57` ≈ -90° = Straight down
- `1.57` ≈ 90° = Straight up
- `-0.785` ≈ -45° = Tilted 45° down

### MAVLink Control via MAVProxy

#### 1. Start the Gimbal Bridge
```bash
python3 /workspace/gimbal_bridge.py
```

This bridges MAVLink gimbal commands to Gazebo topics.

#### 2. MAVLink Commands (in MAVProxy)

**Using long command format:**
```bash
# Point gimbal forward (0 degrees)
MAV> long DO_MOUNT_CONTROL 0 0 0 0 0 0 2

# Point gimbal down 90 degrees
MAV> long DO_MOUNT_CONTROL -90 0 0 0 0 0 2

# Point gimbal 45 degrees down
MAV> long DO_MOUNT_CONTROL -45 0 0 0 0 0 2

# Point gimbal 30 degrees up
MAV> long DO_MOUNT_CONTROL 30 0 0 0 0 0 2
```

**Command format:**
```
long DO_MOUNT_CONTROL <pitch> <roll> <yaw> 0 0 0 2
```
- **pitch**: -90 to +90 degrees (negative = down, positive = up)
- **roll**: 0 (not used)
- **yaw**: 0 (not used)
- Last `2` = MAV_MOUNT_MODE_MAVLINK_TARGETING

### Gimbal Model Info
- Model: `gimbal_small_2d`
- Plugin: `libGimbalSmall2dPlugin.so`
- Joint: `tilt_joint`
- Camera attached to: `tilt_link`

---

## Available Tools

### Gazebo Commands

```bash
# List all topics
gz topic -l

# Echo a topic (continuous)
gz topic -e /gazebo/default/iris_demo/gimbal_tilt_status

# Get model info
gz model -m iris_demo -i
```

### Camera Tools

| Tool | Format | Location |
|------|--------|----------|
| camera2zmq | MsgPack | `/workspace/src/build/camera2zmq` |
| sub_img_msgpack (C++) | MsgPack | `/workspace/src/demos/build/sub_img_msgpack` |
| test_camera_msgpack.py | MsgPack | `/workspace/src/test/test_camera_msgpack.py` |
| sub_img (C++) | Legacy | `/workspace/src/demos/build/sub_img` |

### Flight Scripts

| Script | Description | Location |
|--------|-------------|----------|
| fly_to_100m.py | Autonomous flight to 100m + RTL | `/workspace/sr/test/fly_to_100m.py` |
| gimbal_bridge.py | MAVLink to Gazebo gimbal bridge | `/workspace/src/test/gimbal_bridge.py` |

### Utility Scripts - doesn't work

| Script | Description | Location |
|--------|-------------|----------|
| tilt_camera.sh | Shell script to tilt camera | `/workspace/src/test/src/test/tilt_camera.sh` |

---

## Quick Start Guide

### 1. Start Gazebo with Iris
```bash
gazebo --verbose /workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world
```

### 2. Start ArduPilot SITL (Optional)
```bash
sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map
```

### 3. Start Camera Publisher
```bash
/workspace/src/build/camera2zmq
```

### 4. View Camera Feed
```bash
# Python viewer
python3 /workspace/src/test/test_camera_msgpack.py

# OR C++ viewer
/workspace/src/demos/build/sub_img_msgpack
```

### 5. Control Gimbal (Optional) - doesn't work
```bash
# Terminal 1: Start bridge
python3 /workspace/src/test/gimbal_bridge.py

# Terminal 2 (MAVProxy): Control gimbal
MAV> long DO_MOUNT_CONTROL -90 0 0 0 0 0 2
```

### 6. Run Autonomous Flight (Optional)
```bash
python3 /workspace/src/test/fly_to_100m.py
```

---

## File Structure

```
/workspace/
├── src/
│   ├── camera2zmq.cpp              # Camera publisher (msgpack)
│   ├── build/
│   │   └── camera2zmq              # Built executable
│   ├── demos/
│   │   ├── sub_img.cpp             # Legacy subscriber
│   │   ├── sub_img_msgpack.cpp     # MsgPack subscriber
│   │   └── build/
│   │       ├── sub_img
│   │       └── sub_img_msgpack
│   └── ardupilot_gazebo/
│   |   └── worlds/
│   |        ├── iris_fixed.world
│   |        └── iris_arducopter_runway.world
├   └── test/
|       └── fly_to_100m.py                  # Autonomous flight script
|       ├── gimbal_bridge.py                # MAVLink gimbal bridge
|       ├── test_camera_msgpack.py          # Python camera viewer
├── QUICK_REFERENCE.md
└── SETUP_GUIDE.md                  # This file


```

---


## Notes

- The ArduPilot plugin configuration is in `/workspace/src/ardupilot_gazebo/models/iris_with_ardupilot/model.sdf`
- Gimbal model `gimbal_small_2d` is loaded from system Gazebo models (not in workspace)
- ZMQ default ports: 5556 (camera), 5555 (demos)
- MAVLink default ports: 14550 (SITL), 9002/9003 (ArduPilot plugin FDM)

---

## Credits

This setup uses:
- ArduPilot SITL
- Gazebo 11
- ardupilot_gazebo plugin
- ZMQ for messaging
- MsgPack for serialization
- OpenCV for image processing
- MAVLink for drone communication

---

Last Updated: 2025-10-21

