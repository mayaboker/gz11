#!/usr/bin/env python3
"""
Receive camera images via ZMQ/msgpack and show whether frames are changing.
Receives multipart messages: [topic, msgpack-encoded-bytes]
"""
import argparse

import cv2
import msgpack
import numpy as np
import zmq


def parse_args():
    parser = argparse.ArgumentParser(description="View camera frames from camera2zmq.")
    parser.add_argument("--host", default="127.0.0.1", help="ZMQ publisher host")
    parser.add_argument("--port", type=int, default=5556, help="ZMQ publisher port")
    parser.add_argument("--topic", default="", help="Topic filter, empty subscribes to all")
    parser.add_argument("--width", type=int, default=640, help="Expected image width")
    parser.add_argument("--height", type=int, default=480, help="Expected image height")
    return parser.parse_args()


def reshape_frame(frame_bytes, width, height):
    if isinstance(frame_bytes, (list, tuple)):
        img_array = np.array(frame_bytes, dtype=np.uint8)
    else:
        img_array = np.frombuffer(frame_bytes, dtype=np.uint8)

    expected_size = width * height * 3
    if len(img_array) == expected_size:
        return img_array.reshape(height, width, 3)

    common_shapes = [(640, 480), (320, 240), (1280, 720)]
    for candidate_width, candidate_height in common_shapes:
        if len(img_array) == candidate_width * candidate_height * 3:
            return img_array.reshape(candidate_height, candidate_width, 3)

    raise ValueError(f"Unexpected frame size: got {len(img_array)}, expected {expected_size}")


def main():
    args = parse_args()
    address = f"tcp://{args.host}:{args.port}"

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(address)
    socket.setsockopt(zmq.SUBSCRIBE, args.topic.encode("utf-8"))

    print(f"Listening for camera images via ZMQ/msgpack on {address}")
    print(f"Topic filter: {args.topic!r} (empty means all)")
    print("Press 'q' to quit\n")

    frame_count = 0
    previous_frame = None

    try:
        while True:
            parts = socket.recv_multipart()
            if len(parts) != 2:
                print(f"Warning: expected 2 message parts, got {len(parts)}")
                continue

            topic_msg, frame_msg = parts
            topic = topic_msg.decode("utf-8", errors="replace")
            frame_bytes = msgpack.unpackb(frame_msg, raw=False)
            img = reshape_frame(frame_bytes, args.width, args.height)

            frame_count += 1
            mean_abs_diff = None
            if previous_frame is not None and previous_frame.shape == img.shape:
                diff = cv2.absdiff(previous_frame, img)
                mean_abs_diff = float(np.mean(diff))
            previous_frame = img.copy()

            if frame_count == 1 or frame_count % 30 == 0:
                diff_text = "n/a" if mean_abs_diff is None else f"{mean_abs_diff:.3f}"
                print(
                    f"Frame {frame_count}: shape={img.shape} topic='{topic}' "
                    f"mean_abs_diff={diff_text}"
                )

            cv2.imshow("Camera Feed (MsgPack)", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        socket.close()
        context.term()
        print(f"\nReceived {frame_count} frames")


if __name__ == "__main__":
    main()
