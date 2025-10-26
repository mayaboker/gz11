#!/usr/bin/env python3
"""
ZMQ Camera Subscriber - Matching New Format
Receives multipart messages: (TOPIC, msgpack_data)
"""

import zmq
import msgpack
import numpy as np
import cv2

# Configuration
ZMQ_ADDRESS = "tcp://localhost:5556"
EXPECTED_TOPIC = b"camera/image"  # Topic as bytes

def main():
    print("ZMQ Camera Subscriber (New Format)")
    print("=" * 50)
    print(f"Connecting to: {ZMQ_ADDRESS}")
    print(f"Expected topic: {EXPECTED_TOPIC.decode()}")
    print()
    
    # Setup ZMQ subscriber
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(ZMQ_ADDRESS)
    
    # Subscribe to all topics (empty string)
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    
    print("Waiting for images...")
    print("Press Ctrl+C to exit")
    print()
    
    frame_count = 0
    
    try:
        while True:
            # Receive multipart message: [topic, data]
            parts = socket.recv_multipart()
            
            if len(parts) < 2:
                print("ERROR: Expected 2 parts but got", len(parts))
                continue
            
            # Extract the data part (second element)
            # parts[0] is the topic, parts[1] is the msgpack data
            data = parts[1]
            
            # Unpack msgpack data
            try:
                # Use Unpacker to handle the msgpack stream properly
                unpacker = msgpack.Unpacker(raw=False)
                unpacker.feed(data)
                frame_bytes = next(unpacker)
            except Exception as e:
                print(f"Msgpack unpack error: {e}")
                continue
            
            # Convert bytes to numpy array
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            
            # We need to know the image dimensions to reshape
            # Assuming 640x480 from the Gazebo camera (3 channels BGR)
            HEIGHT = 480
            WIDTH = 640
            CHANNELS = 3
            
            expected_size = HEIGHT * WIDTH * CHANNELS
            
            if len(frame_array) == expected_size:
                # Reshape to (height, width, channels)
                frame = frame_array.reshape((HEIGHT, WIDTH, CHANNELS))
                
                # Display the frame
                cv2.imshow('Camera Feed (New Format)', frame)
                
                frame_count += 1
                if frame_count % 30 == 0:  # Print every 30 frames (~1 second at 30fps)
                    print(f"✓ Received {frame_count} frames")
                
                # Wait 1ms for key press (required for cv2.imshow to work)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nQuitting...")
                    break
            else:
                print(f"Error: Unexpected frame size. Got {len(frame_array)}, expected {expected_size}")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        print(f"\nTotal frames received: {frame_count}")
        cv2.destroyAllWindows()
        socket.close()
        context.term()

if __name__ == "__main__":
    main()

