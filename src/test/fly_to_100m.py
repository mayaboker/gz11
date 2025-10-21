#!/usr/bin/env python3
"""
Script to arm and fly Iris drone to 100 meters altitude
"""
from pymavlink import mavutil
import time
import sys

# Connect to the Vehicle
print("Connecting to vehicle...")
# Default SITL connection is UDP on port 14550
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')

# Wait for heartbeat to confirm connection
print("Waiting for heartbeat...")
master.wait_heartbeat()
print(f"Heartbeat from system (system {master.target_system} component {master.target_component})")

def set_mode(mode):
    """Set flight mode"""
    # Get mode ID
    if mode not in master.mode_mapping():
        print(f"Unknown mode: {mode}")
        print(f"Available modes: {list(master.mode_mapping().keys())}")
        sys.exit(1)
    
    mode_id = master.mode_mapping()[mode]
    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id)
    
    print(f"Setting mode to {mode}...")
    
    # Wait for ACK
    ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
    if ack:
        print(f"Mode change ACK: {ack}")
    return True

def arm_vehicle():
    """Arm the vehicle"""
    print("Arming vehicle...")
    
    # Disable pre-arm checks for SITL
    master.mav.param_set_send(
        master.target_system,
        master.target_component,
        b'ARMING_CHECK',
        0,
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32
    )
    time.sleep(0.5)
    
    # Send arm command
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,  # confirmation
        1,  # arm (1 to arm, 0 to disarm)
        0, 0, 0, 0, 0, 0)
    
    # Wait for arming confirmation
    print("Waiting for arming...")
    master.motors_armed_wait()
    print("Vehicle ARMED!")

def takeoff(altitude):
    """Command vehicle to takeoff to specified altitude"""
    print(f"Taking off to {altitude} meters...")
    
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,  # confirmation
        0, 0, 0, 0,  # params 1-4
        0, 0,  # latitude, longitude (not used, will use current position)
        altitude)  # altitude
    
    # Wait for ACK
    ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
    if ack:
        print(f"Takeoff ACK: {ack}")

def get_altitude():
    """Get current altitude"""
    msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=3)
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
    set_mode('RTL')
    
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
    try:
        # Set mode to GUIDED
        set_mode('GUIDED')
        time.sleep(1)
        
        # Arm vehicle
        arm_vehicle()
        time.sleep(1)
        
        # Takeoff to 100 meters
        takeoff(100)
        
        # Wait for altitude
        wait_for_altitude(100, tolerance=2.0)
        
        print("\n✓ Reached 100 meters! Holding for 5 minutes...")
        hold_time = 300  # 5 minutes = 300 seconds
        
        # Count down while holding
        for remaining in range(hold_time, 0, -30):
            mins = remaining // 60
            secs = remaining % 60
            current_alt = get_altitude()
            print(f"Holding at {current_alt:.1f}m - Time remaining: {mins}:{secs:02d}")
            time.sleep(30)  # Update every 30 seconds
        
        # Return to Launch
        rtl()
        
        # Wait for landing
        wait_for_landing()
        
        print("\n✓ Mission complete! Drone has returned and landed.")
        
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

