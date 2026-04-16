#!/usr/bin/env python3
"""
Script to arm and fly an Iris drone to a target altitude.
"""
import argparse
import sys
import time

from pymavlink import mavutil


master = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Arm ArduPilot SITL, take off, hold position, and RTL."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=14550,
        help="UDP port for MAVLink connection (default: 14550)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for MAVLink connection (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--altitude",
        type=float,
        default=100.0,
        help="Takeoff altitude in meters (default: 100)",
    )
    parser.add_argument(
        "--hold-seconds",
        type=int,
        default=300,
        help="Time to hold position before RTL (default: 300)",
    )
    return parser.parse_args()


def wait_for_heartbeat():
    print("Waiting for heartbeat...")
    master.wait_heartbeat()
    print(
        f"Heartbeat from system {master.target_system} "
        f"component {master.target_component}"
    )


def drain_status_text(timeout=0.2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = master.recv_match(type="STATUSTEXT", blocking=False)
        if msg is None:
            time.sleep(0.02)
            continue
        text = getattr(msg, "text", "").strip()
        if text:
            print(f"STATUSTEXT: {text}")


def wait_until(condition, timeout, description, poll_interval=0.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        drain_status_text()
        if condition():
            return True
        time.sleep(poll_interval)
    raise TimeoutError(f"Timed out while waiting for {description}")


def send_command_long(command, *params):
    full_params = list(params) + [0] * (7 - len(params))
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        command,
        0,
        *full_params,
    )


def wait_command_ack(command, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = master.recv_match(type=["COMMAND_ACK", "STATUSTEXT"], blocking=True, timeout=1)
        if msg is None:
            continue
        if msg.get_type() == "STATUSTEXT":
            text = getattr(msg, "text", "").strip()
            if text:
                print(f"STATUSTEXT: {text}")
            continue
        if msg.command == command:
            print(f"ACK for command {command}: result={msg.result}")
            return msg
    return None


def wait_mode(mode, timeout=10):
    mode_mapping = master.mode_mapping()
    target_mode = mode_mapping[mode]

    def mode_is_set():
        hb = master.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        return hb is not None and getattr(hb, "custom_mode", None) == target_mode

    wait_until(mode_is_set, timeout, f"mode {mode}")

def set_mode(mode):
    """Set flight mode and wait until it becomes active."""
    if mode not in master.mode_mapping():
        print(f"Unknown mode: {mode}")
        print(f"Available modes: {list(master.mode_mapping().keys())}")
        sys.exit(1)

    mode_id = master.mode_mapping()[mode]
    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id,
    )

    print(f"Setting mode to {mode}...")
    wait_mode(mode)
    print(f"Mode is now {mode}")
    return True


def set_parameter(name, value, timeout=5):
    """Set a parameter and verify the new value when possible."""
    encoded_name = name.encode("utf-8")
    master.mav.param_set_send(
        master.target_system,
        master.target_component,
        encoded_name,
        float(value),
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
    )

    # Ask for an explicit readback too; some setups do not immediately emit a
    # matching PARAM_VALUE after PARAM_SET.
    master.mav.param_request_read_send(
        master.target_system,
        master.target_component,
        encoded_name,
        -1,
    )

    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = master.recv_match(type=["PARAM_VALUE", "STATUSTEXT"], blocking=True, timeout=1)
        if msg is None:
            continue
        if msg.get_type() == "STATUSTEXT":
            text = getattr(msg, "text", "").strip()
            if text:
                print(f"STATUSTEXT: {text}")
            continue
        param_id = msg.param_id
        if isinstance(param_id, bytes):
            param_id = param_id.decode("utf-8", errors="ignore")
        param_id = str(param_id).rstrip("\x00")
        if param_id == name:
            print(f"Parameter {name} set to {msg.param_value}")
            return msg.param_value

    print(f"Warning: timed out while verifying parameter {name}; continuing")
    return None

def arm_vehicle():
    """Arm the vehicle and fail with a useful timeout."""
    print("Arming vehicle...")

    # Disable pre-arm checks for SITL
    set_parameter("ARMING_CHECK", 0)

    # Send arm command.
    send_command_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
    wait_command_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)

    print("Waiting for arming...")
    wait_until(master.motors_armed, 20, "vehicle to arm")
    print("Vehicle ARMED!")

def takeoff(altitude):
    """Command vehicle to takeoff to specified altitude"""
    print(f"Taking off to {altitude} meters...")

    send_command_long(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, altitude)
    wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF)

def get_altitude():
    """Get current altitude"""
    msg = master.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=3)
    if msg:
        return msg.relative_alt / 1000.0  # Convert mm to meters
    return 0

def wait_for_altitude(target_alt, tolerance=1.0):
    """Wait until vehicle reaches target altitude"""
    print(f"Waiting to reach {target_alt}m (within {tolerance}m tolerance)...")

    while True:
        current_alt = get_altitude()
        print(f"Current altitude: {current_alt:.1f}m / Target: {target_alt}m")

        if abs(current_alt - target_alt) < tolerance:
            print(f"Reached target altitude: {current_alt:.1f}m")
            break

        time.sleep(2)

def rtl():
    """Return to Launch"""
    print("\nInitiating RTL (Return to Launch)...")
    set_mode("RTL")
    
def wait_for_landing():
    """Wait until vehicle has landed"""
    print("Waiting for landing...")

    while True:
        current_alt = get_altitude()
        print(f"Current altitude: {current_alt:.1f}m")

        if current_alt < 0.5:  # Close to ground
            print("Landed!")
            break

        time.sleep(2)

def main():
    """Main execution"""
    global master
    args = parse_args()
    connect_string = f"udp:{args.host}:{args.port}"

    print(f"Connecting to vehicle on {connect_string}...")
    master = mavutil.mavlink_connection(connect_string)

    try:
        wait_for_heartbeat()

        # Set mode to GUIDED
        set_mode("GUIDED")
        time.sleep(1)

        # Arm vehicle
        arm_vehicle()
        time.sleep(1)

        # Takeoff to 100 meters
        takeoff(args.altitude)

        # Wait for altitude
        wait_for_altitude(args.altitude, tolerance=2.0)

        print(f"\nReached {args.altitude:.1f} meters. Holding for {args.hold_seconds} seconds...")
        hold_time = args.hold_seconds

        # Count down while holding
        for remaining in range(hold_time, 0, -30):
            mins = remaining // 60
            secs = remaining % 60
            current_alt = get_altitude()
            print(f"Holding at {current_alt:.1f}m - Time remaining: {mins}:{secs:02d}")
            time.sleep(min(30, remaining))

        # Return to Launch
        rtl()

        # Wait for landing
        wait_for_landing()

        print("\nMission complete. Drone has returned and landed.")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        print("Switching to RTL...")
        rtl()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

