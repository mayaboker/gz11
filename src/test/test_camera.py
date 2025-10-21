#!/usr/bin/env python3
import zmq
import numpy as np
import cv2
import struct

context = zmq.Context()
socket = zmq.Socket(context, zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.setsockopt(zmq.SUBSCRIBE, b"")

print("Listening for camera images on tcp://localhost:5556")
print("Press 'q' to quit\n")

while True:
    # Receive metadata
    meta = socket.recv()
    img_data = socket.recv()
    
    rows, cols, cv_type = struct.unpack('iii', meta)
    
    # Reconstruct image
    img = np.frombuffer(img_data, dtype=np.uint8).reshape(rows, cols, 3)
    
    # Calculate average color to detect changes
    avg_color = img.mean(axis=(0,1))
    
    print(f"Image: {rows}x{cols}, Avg BGR: {avg_color}")
    
    cv2.imshow('Camera Feed', img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()

