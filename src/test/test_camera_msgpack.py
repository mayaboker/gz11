#!/usr/bin/env python3
"""
Test script to receive camera images via ZMQ with msgpack
Receives multipart messages: [topic, msgpack-encoded-bytes]
"""
import zmq
import msgpack
import numpy as np
import cv2

# Connect to ZMQ
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5567")
socket.setsockopt(zmq.SUBSCRIBE, b"")

print("Listening for camera images via ZMQ (msgpack format)")
print("Press 'q' to quit\n")

frame_count = 0

while True:
    try:
        # Receive multipart message: [topic, frame_bytes]
        topic_msg = socket.recv()
        frame_msg = socket.recv()
        
        topic = topic_msg.decode('utf-8')
        
        # Unpack msgpack - expecting raw byte array
        frame_bytes = msgpack.unpackb(frame_msg, raw=False)
        
        # Convert to numpy array
        if isinstance(frame_bytes, (list, tuple)):
            img_array = np.array(frame_bytes, dtype=np.uint8)
        else:
            img_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        
        # Frames are sent as BGR or grayscale 3-channel BGR
        # Determine shape - assuming frames are reshaped by the sender
        # The sender converts to 3-channel BGR, so we need to figure out dimensions
        total_pixels = len(img_array) // 3  # Assuming 3 channels (BGR)
        
        # Common camera sizes: 640x480, 320x240, etc.
        # Try to infer dimensions (aspect ratio ~4:3 or similar)
        # For now, assume standard dimensions or use a fallback
        
        # Better approach: the image dimensions should be consistent with Gazebo camera
        # Default is typically 640x480 for Gazebo cameras
        rows, cols = 480, 640
        
        # Reshape to (rows, cols, 3) for BGR image
        if len(img_array) == rows * cols * 3:
            img = img_array.reshape(rows, cols, 3)
        else:
            # If size doesn't match, try to infer
            print(f"Warning: Expected {rows * cols * 3} bytes, got {len(img_array)}")
            # Try other common sizes
            if len(img_array) == 640 * 480 * 3:
                img = img_array.reshape(480, 640, 3)
            elif len(img_array) == 320 * 240 * 3:
                img = img_array.reshape(240, 320, 3)
            else:
                # Fallback: assume square-ish
                side = int(np.sqrt(len(img_array) // 3))
                img = img_array.reshape(side, side, 3)
        
        frame_count += 1
        print(f"Frame {frame_count}: {img.shape} topic='{topic}' size={len(frame_bytes)} bytes")
        
        # Display image
        cv2.imshow('Camera Feed (MsgPack)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    except KeyboardInterrupt:
        break
    except zmq.error.Again:
        # Timeout, continue
        continue
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

cv2.destroyAllWindows()
socket.close()
context.term()
print(f"\nReceived {frame_count} frames")

