#!/usr/bin/env python3
"""
MAVLink to Gazebo Gimbal Bridge
Listens to MAVLink gimbal commands and forwards them to Gazebo gimbal topic
"""
from pymavlink import mavutil
import subprocess
import time
import threading
import math

# Connect to MAVLink
print("Connecting to MAVLink on 127.0.0.1:14550...")
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
master.wait_heartbeat()
print(f"Connected to system {master.target_system}")

# Current gimbal pitch angle (radians)
current_pitch = 0.0
gimbal_lock = threading.Lock()

def set_gazebo_gimbal(pitch_rad):
    """Send gimbal command to Gazebo"""
    cmd = [
        'gz', 'topic', '-p', '/gazebo/default/iris_demo/gimbal_tilt_cmd',
        '-m', 'gazebo.msgs.GzString',
        '-v', f'data: "{pitch_rad:.6f}"'
    ]
    
    try:
        # Run in background without waiting for completion
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error setting gimbal: {e}")
        return False

def gimbal_control_loop():
    """Continuously send gimbal position to Gazebo"""
    global current_pitch
    
    while True:
        with gimbal_lock:
            pitch = current_pitch
        
        # Send to Gazebo
        set_gazebo_gimbal(pitch)
        time.sleep(0.1)  # Update at 10Hz

# Start gimbal control thread
gimbal_thread = threading.Thread(target=gimbal_control_loop, daemon=True)
gimbal_thread.start()

print("\nGimbal bridge active!")
print("Use MAVProxy commands to control gimbal:")
print("  MAV> gimbal pitch <angle_degrees>")
print("  Example: gimbal pitch -90  (points down)")
print("  Example: gimbal pitch 0    (points forward)")
print("\nPress Ctrl+C to stop\n")

# Listen for MAVLink messages
while True:
    try:
        msg = master.recv_match(blocking=True, timeout=1)
        
        if msg is None:
            continue
        
        msg_type = msg.get_type()
        
        # Handle COMMAND_LONG for gimbal control
        if msg_type == 'COMMAND_LONG':
            if msg.command == mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL:
                # msg.param1 = pitch (degrees)
                # msg.param2 = roll (degrees)  
                # msg.param3 = yaw (degrees)
                # msg.param7 = mount mode
                
                pitch_deg = msg.param1
                pitch_rad = math.radians(pitch_deg)
                
                with gimbal_lock:
                    current_pitch = pitch_rad
                
                print(f"Gimbal pitch set to {pitch_deg}° ({pitch_rad:.3f} rad)")
                
        # Handle MAV_CMD_DO_GIMBAL_MANAGER_PITCHYAW
        elif msg_type == 'COMMAND_LONG' and msg.command == mavutil.mavlink.MAV_CMD_DO_GIMBAL_MANAGER_PITCHYAW:
            pitch_deg = msg.param1
            pitch_rad = math.radians(pitch_deg)
            
            with gimbal_lock:
                current_pitch = pitch_rad
            
            print(f"Gimbal pitch set to {pitch_deg}° ({pitch_rad:.3f} rad)")
            
        # Handle MOUNT_CONFIGURE
        elif msg_type == 'MOUNT_CONFIGURE':
            print(f"Mount configured: mode={msg.mount_mode}")
            
        # Handle MOUNT_CONTROL  
        elif msg_type == 'MOUNT_CONTROL':
            pitch_deg = msg.input_a / 100.0  # Pitch in centidegrees
            pitch_rad = math.radians(pitch_deg)
            
            with gimbal_lock:
                current_pitch = pitch_rad
            
            print(f"Mount control: pitch={pitch_deg}° ({pitch_rad:.3f} rad)")
            
    except KeyboardInterrupt:
        print("\nShutting down gimbal bridge...")
        break
    except Exception as e:
        print(f"Error: {e}")
        continue

print("Gimbal bridge stopped.")

