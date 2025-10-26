# Camera2ZMQ Changes - Grayscale Multipart Format

**Date:** October 26, 2025  
**Summary:** Modified camera2zmq to convert images to grayscale and use ZMQ multipart message format matching Python reference implementation.

---

## Overview

The camera2zmq publisher has been updated to match a specific Python message format that:
1. Converts all camera frames to grayscale (but keeps 3-channel BGR format)
2. Sends messages as ZMQ multipart: `(TOPIC, msgpack_data)`
3. Packs only the raw frame bytes (not a dictionary structure)

---

## Changes Made

### 1. Modified Camera Publisher (`/workspace/src/camera2zmq.cpp`)

#### Image Processing Changes
- **Added grayscale conversion** matching Python code:
  ```python
  frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
  ```

- **C++ Implementation:**
  ```cpp
  // Convert to grayscale if not already grayscale, then back to 3-channel BGR
  if (img.channels() == 3) {
      cv::cvtColor(img, img, cv::COLOR_BGR2GRAY);
      cv::cvtColor(img, img, cv::COLOR_GRAY2BGR);
  } else if (img.channels() == 1) {
      // If already grayscale, convert to 3-channel BGR
      cv::cvtColor(img, img, cv::COLOR_GRAY2BGR);
  }
  ```

#### Message Format Changes
- **Changed from:** Dictionary with metadata (topic, rows, cols, type, data)
- **Changed to:** Multipart message with topic and raw frame bytes

**Old Format:**
```cpp
// Packed as map: {topic: "...", rows: X, cols: Y, type: Z, data: [...]}
pk.pack_map(5);
pk.pack("topic"); pk.pack(g_msgpack_topic);
pk.pack("rows"); pk.pack(rows);
// ... etc
socket.send(zmq_msg);
```

**New Format:**
```cpp
// Convert frame to bytes
std::vector<unsigned char> frame_bytes(img.data, ...);

// Pack with msgpack (just the bytes)
msgpack::pack(frame_bytes);

// Send as multipart: (TOPIC, data)
socket.send(topic_msg, zmq::send_flags::sndmore);
socket.send(data_msg, zmq::send_flags::none);
```

#### Python Reference Code
```python
# Original Python format being matched:
pb_obj = msg.image_stamped_pb2.ImageStamped()
pb_obj.ParseFromString(data)
dbytes = np.frombuffer(pb_obj.image.data, dtype=np.uint8)
image_prop = (pb_obj.image.height, pb_obj.image.width, RGB_IMAGE)
frame = np.reshape(dbytes, newshape=image_prop)
frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
pub_im = frame.tobytes()
data = msgpack.packb(frame)
socket.send_multipart((TOPIC, data))
```

---

### 2. Created New C++ Subscriber (`/workspace/src/demos/sub_img_multipart.cpp`)

**Purpose:** Receive and display images in the new multipart format

**Features:**
- Receives ZMQ multipart messages: `(TOPIC, msgpack_data)`
- Unpacks msgpack to get raw frame bytes
- Reshapes to 640×480×3 image
- Displays with OpenCV
- Press ESC to exit

**Usage:**
```bash
/workspace/src/demos/build/sub_img_multipart [zmq_address] [expected_topic]

# Defaults:
#   zmq_address: tcp://localhost:5556
#   expected_topic: camera/image
```

**Code Structure:**
```cpp
// Receive multipart
socket.recv(topic_msg);
socket.recv(data_msg);

// Unpack msgpack
msgpack::unpack(data);
std::vector<unsigned char> frame_bytes;
obj.convert(frame_bytes);

// Reshape to image
cv::Mat frame(HEIGHT, WIDTH, CV_8UC3, frame_bytes.data());
cv::imshow("Camera Feed", frame);
```

---

### 3. Created New Python Subscriber (`/workspace/test_camera_new_format.py`)

**Purpose:** Python equivalent of the C++ subscriber for testing

**Features:**
- Receives multipart messages
- Unpacks msgpack data
- Reshapes to numpy array
- Displays with OpenCV
- Press 'q' or Ctrl+C to exit

**Usage:**
```bash
python3 /workspace/test_camera_new_format.py
```

**Code Structure:**
```python
# Receive multipart
topic, data = socket.recv_multipart()

# Unpack msgpack
frame_bytes = msgpack.unpackb(data, raw=False)
frame_array = np.array(frame_bytes, dtype=np.uint8)

# Reshape
frame = frame_array.reshape((HEIGHT, WIDTH, CHANNELS))
cv2.imshow('Camera Feed', frame)
```

---

### 4. Updated CMakeLists.txt (`/workspace/src/demos/CMakeLists.txt`)

**Added build target for new subscriber:**
```cmake
add_executable(sub_img_multipart sub_img_multipart.cpp)
target_include_directories(sub_img_multipart PRIVATE 
    ${ZMQ_INCLUDE_DIRS} 
    ${OpenCV_INCLUDE_DIRS} 
    ${MSGPACK_INCLUDE_DIRS})
target_link_libraries(sub_img_multipart PRIVATE 
    ${ZMQ_LIBRARIES} 
    Threads::Threads 
    ${OpenCV_LIBRARIES})
```

---

### 5. Fixed Image Dimensions

**Issue:** Initial hardcoded dimensions were incorrect
- **Was:** 320×240×3 = 230,400 bytes
- **Fixed to:** 640×480×3 = 921,600 bytes

**Files Updated:**
- `/workspace/src/demos/sub_img_multipart.cpp` - Changed HEIGHT/WIDTH constants
- `/workspace/test_camera_new_format.py` - Changed HEIGHT/WIDTH variables

---

## File Summary

### Modified Files
1. `/workspace/src/camera2zmq.cpp` - Camera publisher with grayscale conversion and multipart format
2. `/workspace/src/demos/CMakeLists.txt` - Added new subscriber build target

### New Files
1. `/workspace/src/demos/sub_img_multipart.cpp` - C++ multipart subscriber
2. `/workspace/test_camera_new_format.py` - Python multipart subscriber
3. `/workspace/CHANGES_GRAYSCALE_MULTIPART.md` - This document

### Built Executables
1. `/workspace/src/build/camera2zmq` - Updated publisher
2. `/workspace/src/demos/build/sub_img_multipart` - New C++ subscriber

---

## Testing Instructions

### Full Pipeline Test

**Terminal 1 - Start Gazebo:**
```bash
gazebo --verbose /workspace/src/ardupilot_gazebo/worlds/iris_arducopter_runway.world
```

**Terminal 2 - Start Camera Publisher:**
```bash
/workspace/src/build/camera2zmq

# Optional custom parameters:
# /workspace/src/build/camera2zmq \
#   "/gazebo/path/to/camera" \
#   "tcp://*:5556" \
#   "camera/image"
```

**Terminal 3 - Start Subscriber (C++):**
```bash
/workspace/src/demos/build/sub_img_multipart

# Or with custom parameters:
# /workspace/src/demos/build/sub_img_multipart tcp://localhost:5556 camera/image
```

**OR Terminal 3 - Start Subscriber (Python):**
```bash
python3 /workspace/test_camera_new_format.py
```

### Expected Output

**Publisher:**
```
Camera2ZMQ Publisher (MsgPack)
==============================
Gazebo topic: /gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image
ZMQ address: tcp://*:5556
MsgPack topic: camera/image

Received image: 640x480 format: 3
Converted to grayscale (3-channel)
Published frame via ZMQ multipart: 480x640 topic: camera/image
```

**Subscriber:**
```
Received from topic: camera/image
Frame bytes length: 921600
Reshaped to: 480x640 channels: 3
✓ Frame #1 received and displayed
```

---

## Technical Details

### Image Format Specification

| Property | Value |
|----------|-------|
| Resolution | 640×480 |
| Channels | 3 (BGR) |
| Bit Depth | 8 bits per channel |
| Total Bytes | 921,600 |
| OpenCV Type | CV_8UC3 |
| Color | Grayscale (but 3-channel) |

### ZMQ Message Structure

**Multipart Message:**
```
Part 1 (Topic):  "camera/image" (string)
Part 2 (Data):   msgpack([byte, byte, ...]) (921600 bytes)
```

### MsgPack Format

**What's packed:**
- Raw frame bytes as vector: `[b0, b1, b2, ..., b921599]`

**What's NOT packed:**
- ~~No metadata dictionary~~
- ~~No rows/cols/type information~~
- Receiver must know dimensions (640×480×3)

---

## Backward Compatibility

### Old Format (Still Available)

The old subscribers are still available but incompatible with the new format:

**Old Subscribers (DON'T USE with new publisher):**
- `/workspace/src/demos/build/sub_img_msgpack` - Expects dictionary format
- `/workspace/src/test/test_camera_msgpack.py` - Expects dictionary format

**Old Format Expected:**
```python
{
    'topic': 'camera/image',
    'rows': 480,
    'cols': 640,
    'type': 16,
    'data': [...]
}
```

### Migration Guide

If you need to switch back to the old format, you would need to:
1. Revert `/workspace/src/camera2zmq.cpp` to previous version
2. Rebuild with `cd /workspace/src/build && make camera2zmq`
3. Use old subscribers: `sub_img_msgpack` or `test_camera_msgpack.py`

---

## Build Commands

### Rebuild Everything

```bash
# Build camera publisher
cd /workspace/src/build
cmake ..
make camera2zmq

# Build C++ subscriber
cd /workspace/src/demos/build
cmake ..
make sub_img_multipart
```

### Build Individual Components

```bash
# Just the publisher
cd /workspace/src/build && make camera2zmq

# Just the subscriber
cd /workspace/src/demos/build && make sub_img_multipart
```

---

## Dependencies

### Required Packages
- **Gazebo** - Simulation environment
- **OpenCV** (C++ & Python) - Image processing
- **ZMQ** (C++ & Python) - Messaging
- **MsgPack** (C++ & Python) - Serialization
- **CMake** - Build system
- **TBB** - Threading Building Blocks

### Already Installed
All dependencies should already be installed based on `SETUP_GUIDE.md`

---

## Troubleshooting

### Issue: Wrong Image Dimensions

**Symptom:**
```
Error: Unexpected frame size. Got X, expected Y
```

**Solution:**
Check actual camera resolution in Gazebo and update HEIGHT/WIDTH constants in subscriber code.

### Issue: No Messages Received

**Symptom:**
Subscriber shows "Waiting for images..." but nothing happens

**Checklist:**
1. Is Gazebo running?
2. Is camera2zmq running and showing "Published frame" messages?
3. Are ZMQ addresses matching? (default: tcp://*:5556 for pub, tcp://localhost:5556 for sub)
4. Check firewall settings if using different machines

### Issue: Grayscale Not Visible

**Note:** The images are converted to grayscale but kept as 3-channel BGR. They should appear as grayscale images when displayed. All three channels contain the same grayscale values.

---

## Performance Notes

- **Frame rate:** Limited by Gazebo camera (typically 30 FPS)
- **Latency:** Minimal (< 10ms) for local communication
- **Bandwidth:** ~27 MB/s at 30 FPS (921,600 bytes × 30 = 27.6 MB/s)

---

## Future Enhancements

Possible improvements:
1. Add dynamic resolution detection (avoid hardcoding 640×480)
2. Add compression (JPEG/PNG) for reduced bandwidth
3. Add timestamp metadata
4. Support multiple subscribers with different topics
5. Add frame dropping for bandwidth control

---

## References

- Original setup: `/workspace/SETUP_GUIDE.md`
- Quick reference: `/workspace/QUICK_REFERENCE.md`
- Camera publisher source: `/workspace/src/camera2zmq.cpp`
- C++ subscriber source: `/workspace/src/demos/sub_img_multipart.cpp`
- Python subscriber source: `/workspace/test_camera_new_format.py`

---

## Contact & Support

For issues or questions, refer to:
- Project documentation in `/workspace/SETUP_GUIDE.md`
- Gazebo documentation: http://gazebosim.org/
- ZMQ documentation: https://zeromq.org/
- OpenCV documentation: https://opencv.org/

---

*Last Updated: October 26, 2025*

