#!/usr/bin/env python3
"""
Simple receiver for the pose published by PublishPoseZMQPlugin.
"""
import argparse
import math
import time

import msgpack
import zmq


def parse_args():
    parser = argparse.ArgumentParser(
        description="Receive model pose over ZMQ/msgpack and print it."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="ZMQ publisher host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5556,
        help="ZMQ publisher port (default: 5556)",
    )
    parser.add_argument(
        "--topic",
        default="camera/pose",
        help="ZMQ topic filter (default: camera/pose)",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=5.0,
        help="Maximum print rate in Hz (default: 5.0)",
    )
    parser.add_argument(
        "--degrees",
        action="store_true",
        help="Print roll/pitch/yaw in degrees instead of radians",
    )
    return parser.parse_args()


def format_angle(value, use_degrees):
    return math.degrees(value) if use_degrees else value


def unpack_pose(payload):
    data = msgpack.unpackb(payload, raw=False)
    if isinstance(data, dict):
        return (
            float(data["x"]),
            float(data["y"]),
            float(data["z"]),
            float(data["roll"]),
            float(data["pitch"]),
            float(data["yaw"]),
        )
    if isinstance(data, (list, tuple)) and len(data) == 6:
        return tuple(float(v) for v in data)
    raise ValueError(f"Unsupported pose payload: {data!r}")


def main():
    args = parse_args()
    address = f"tcp://{args.host}:{args.port}"
    min_period = 0.0 if args.rate <= 0 else 1.0 / args.rate
    angle_unit = "deg" if args.degrees else "rad"

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, args.topic.encode("utf-8"))
    socket.setsockopt(zmq.RCVHWM, 10)
    socket.connect(address)

    print(f"Listening for pose messages on {address} topic='{args.topic}'")
    print("Press Ctrl+C to quit\n")

    last_print = 0.0
    try:
        while True:
            parts = socket.recv_multipart()
            if len(parts) != 2:
                print(f"Warning: expected 2 message parts, got {len(parts)}")
                continue

            topic_msg, payload_msg = parts
            now = time.time()
            if now - last_print < min_period:
                continue

            topic = topic_msg.decode("utf-8", errors="replace")
            x, y, z, roll, pitch, yaw = unpack_pose(payload_msg)
            roll = format_angle(roll, args.degrees)
            pitch = format_angle(pitch, args.degrees)
            yaw = format_angle(yaw, args.degrees)

            print(
                f"{topic} "
                f"x={x:8.3f} y={y:8.3f} z={z:8.3f} "
                f"roll={roll:8.3f} pitch={pitch:8.3f} yaw={yaw:8.3f} {angle_unit}"
            )
            last_print = now
    except KeyboardInterrupt:
        print("\nStopped pose receiver.")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    main()
