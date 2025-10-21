#!/usr/bin/env python3
"""
Test script to receive camera images via ZMQ with msgpack
"""
import zmq
import msgpack
import numpy as np
import cv2

# Connect to ZMQ
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.setsockopt(zmq.SUBSCRIBE, b"")

print("Listening for camera images via ZMQ (msgpack format)")
print("Press 'q' to quit\n")

frame_count = 0

while True:
    try:
        # Receive msgpack message
        msg_bytes = socket.recv()
        
        # Debug: print first 100 bytes
        # print(f"Received {len(msg_bytes)} bytes: {msg_bytes[:100]}")
        
        # Unpack msgpack - use raw=True to keep bytes as bytes
        data = msgpack.unpackb(msg_bytes, raw=False, strict_map_key=False)
        
        # Debug: print data keys and types
        # print(f"Data keys: {data.keys()}")
        # for k, v in data.items():
        #     print(f"  {k}: type={type(v)}, len={len(v) if hasattr(v, '__len__') else 'N/A'}")
        
        # Extract data
        topic = data['topic']
        rows = int(data['rows'])
        cols = int(data['cols'])
        cv_type = int(data['type'])
        img_data = data['data']
        
        # Convert to numpy array - handle both list and bytes
        if isinstance(img_data, (list, tuple)):
            img_array = np.array(img_data, dtype=np.uint8)
        else:
            img_array = np.frombuffer(img_data, dtype=np.uint8)
        
        # Reshape based on type
        if cv_type == 16:  # CV_8UC3 (3 channels)
            img = img_array.reshape(rows, cols, 3)
        elif cv_type == 0:  # CV_8UC1 (1 channel grayscale)
            img = img_array.reshape(rows, cols)
        else:
            print(f"Unknown type: {cv_type}")
            continue
        
        frame_count += 1
        print(f"Frame {frame_count}: {rows}x{cols} topic='{topic}'")
        
        # Display image
        cv2.imshow('Camera Feed (MsgPack)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

cv2.destroyAllWindows()
socket.close()
context.term()
print(f"\nReceived {frame_count} frames")

