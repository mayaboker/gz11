#!/usr/bin/env python3
"""Print live wind status from WindForcePlugin."""
import argparse

import msgpack
import zmq


def parse_args():
    parser = argparse.ArgumentParser(
        description="Subscribe to WindForcePlugin status messages."
    )
    parser.add_argument(
        "--endpoint",
        default="tcp://127.0.0.1:5571",
        help="Wind status endpoint (default: tcp://127.0.0.1:5571)",
    )
    parser.add_argument(
        "--topic",
        default="wind/status",
        help="Status topic filter (default: wind/status)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, args.topic.encode("utf-8"))
    socket.connect(args.endpoint)

    print(f"Listening for wind status on {args.endpoint} topic='{args.topic}'")
    print("Press Ctrl+C to quit\n")

    try:
        while True:
            parts = socket.recv_multipart()
            if len(parts) != 2:
                print(f"Warning: expected 2 parts, got {len(parts)}")
                continue

            topic, payload = parts
            data = msgpack.unpackb(payload, raw=False)
            print(
                f"{topic.decode('utf-8', errors='replace')} "
                f"alt={data['altitude_m']:7.2f} m "
                f"wind={data['actual_wind_knots']:6.2f} kt "
                f"target={data['target_wind_knots']:6.2f} kt "
                f"dir={data['direction_deg']:6.1f} deg "
                f"rel={data['relative_speed_mps']:6.2f} m/s "
                f"force={data['force_n']:7.2f} N "
                f"CdA={data['drag_coefficient'] * data['reference_area']:.3f} "
                f"cmds={data.get('received_control_count', 0)}"
            )
    except KeyboardInterrupt:
        print("\nStopped wind status viewer.")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    main()
