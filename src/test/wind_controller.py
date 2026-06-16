#!/usr/bin/env python3
"""
Send Gazebo wind commands to WindForcePlugin.

Direction is in the Gazebo world XY plane:
  0 degrees   = +X
  90 degrees  = +Y
  180 degrees = -X
  270 degrees = -Y
"""
import argparse
import time

import msgpack
import zmq


def parse_args():
    parser = argparse.ArgumentParser(
        description="Control Gazebo-side wind in knots."
    )
    parser.add_argument(
        "--endpoint",
        default="tcp://127.0.0.1:5570",
        help="ZMQ PUB endpoint to bind (default: tcp://127.0.0.1:5570)",
    )
    parser.add_argument(
        "--topic",
        default="wind/control",
        help="ZMQ topic used by WindForcePlugin (default: wind/control)",
    )
    parser.add_argument(
        "--knots",
        type=float,
        required=True,
        help="Target wind speed in knots at or above ramp end altitude.",
    )
    parser.add_argument(
        "--direction",
        type=float,
        default=0.0,
        help="Wind direction in Gazebo world degrees: 0=+X, 90=+Y.",
    )
    parser.add_argument(
        "--ramp-start-altitude",
        type=float,
        default=0.0,
        help="Altitude in meters where wind starts increasing.",
    )
    parser.add_argument(
        "--ramp-end-altitude",
        type=float,
        default=100.0,
        help="Altitude in meters where wind reaches --knots.",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="Publish rate in Hz. Use 0 to send once and exit.",
    )
    parser.add_argument(
        "--drag-coefficient",
        type=float,
        default=None,
        help="Override plugin drag coefficient. Higher means stronger wind force.",
    )
    parser.add_argument(
        "--reference-area",
        type=float,
        default=None,
        help="Override plugin reference area in square meters. Higher means stronger wind force.",
    )
    parser.add_argument(
        "--max-force",
        type=float,
        default=None,
        help="Override plugin force clamp in Newtons.",
    )
    return parser.parse_args()


def build_command(args):
    command = {
        "speed_knots": args.knots,
        "direction_deg": args.direction,
        "ramp_start_altitude": args.ramp_start_altitude,
        "ramp_end_altitude": args.ramp_end_altitude,
    }
    if args.drag_coefficient is not None:
        command["drag_coefficient"] = args.drag_coefficient
    if args.reference_area is not None:
        command["reference_area"] = args.reference_area
    if args.max_force is not None:
        command["max_force"] = args.max_force
    return command


def main():
    args = parse_args()
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(args.endpoint)

    command = build_command(args)
    payload = msgpack.packb(command, use_bin_type=True)
    topic = args.topic.encode("utf-8")

    print(f"Publishing wind commands on {args.endpoint} topic='{args.topic}'")
    tuning = []
    if args.drag_coefficient is not None:
        tuning.append(f"Cd={args.drag_coefficient:.3f}")
    if args.reference_area is not None:
        tuning.append(f"area={args.reference_area:.3f} m^2")
    if args.max_force is not None:
        tuning.append(f"max_force={args.max_force:.1f} N")
    tuning_text = " " + " ".join(tuning) if tuning else ""
    print(
        f"wind={args.knots:.2f} kt direction={args.direction:.1f} deg "
        f"ramp={args.ramp_start_altitude:.1f}..{args.ramp_end_altitude:.1f} m"
        f"{tuning_text}"
    )

    # Give subscribers a moment to connect before the first command.
    time.sleep(0.5)

    try:
        if args.rate <= 0:
            socket.send_multipart([topic, payload])
            return

        period = 1.0 / args.rate
        while True:
            socket.send_multipart([topic, payload])
            time.sleep(period)
    except KeyboardInterrupt:
        print("\nStopped wind controller.")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    main()
