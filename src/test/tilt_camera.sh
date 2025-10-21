#!/bin/bash
# Script to tilt the camera gimbal

# Usage: ./tilt_camera.sh <angle_in_radians>
# Examples:
#   ./tilt_camera.sh 0      # horizontal (forward)
#   ./tilt_camera.sh -0.5   # tilted down
#   ./tilt_camera.sh -1.57  # pointing down (90 degrees)

ANGLE="${1:-0}"

echo "Tilting camera to angle: $ANGLE radians"
gz topic -p /gazebo/default/iris_demo/gimbal_tilt_cmd -m gazebo.msgs.GzString -v "data: \"$ANGLE\""

echo "Waiting for status..."
sleep 1
gz topic -e /gazebo/default/iris_demo/gimbal_tilt_status -n 1

