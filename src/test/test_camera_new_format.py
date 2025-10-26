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
            # Receive multipart message: (TOPIC, data)
            topic, data = socket.recv_multipart()
            
            print(f"Received message from topic: {topic}")
            
            # Check if it's our expected topic
            if topic != EXPECTED_TOPIC:
                print(f"Warning: Unexpected topic. Got '{topic}', expected '{EXPECTED_TOPIC}'")
            
            # Unpack msgpack data
            frame_bytes = msgpack.unpackb(data, raw=False)
            
            # Convert to numpy array
            frame_array = np.array(frame_bytes, dtype=np.uint8)
            
            print(f"Frame bytes length: {len(frame_bytes)}")
            print(f"Frame array shape after unpack: {frame_array.shape}")
            
            # We need to know the image dimensions to reshape
            # Assuming 640x480 from the Gazebo camera (3 channels BGR)
            HEIGHT = 480
            WIDTH = 640
            CHANNELS = 3
            
            expected_size = HEIGHT * WIDTH * CHANNELS
            
            if len(frame_array) == expected_size:
                # Reshape to (height, width, channels)
                frame = frame_array.reshape((HEIGHT, WIDTH, CHANNELS))
                
                print(f"Reshaped to: {frame.shape}")
                print(f"Frame type: {frame.dtype}")
                
                # Display the frame
                cv2.imshow('Camera Feed (New Format)', frame)
                
                frame_count += 1
                print(f"✓ Frame #{frame_count} received and displayed")
                print("-" * 50)
                
                # Wait 1ms for key press (required for cv2.imshow to work)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nQuitting...")
                    break
            else:
                print(f"Error: Unexpected frame size. Got {len(frame_array)}, expected {expected_size}")
                print("Cannot reshape and display")
                print("-" * 50)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        print(f"\nTotal frames received: {frame_count}")
        cv2.destroyAllWindows()
        socket.close()
        context.term()

if __name__ == "__main__":
    main()

