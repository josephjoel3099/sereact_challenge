#!/bin/bash
set -e

source /opt/ros/humble/setup.bash

ROS2_WS=/workspaces/bin_picking_cell/ros2_ws

# Install rosdep deps if packages exist
if [ -d "$ROS2_WS/src" ] && [ "$(ls -A $ROS2_WS/src)" ]; then
    cd $ROS2_WS
    rosdep install --from-paths src --ignore-src -r -y || true
    colcon build --symlink-install
fi

# Always add to bashrc safely
grep -qxF "source $ROS2_WS/install/setup.bash 2>/dev/null || true" ~/.bashrc \
    || echo "source $ROS2_WS/install/setup.bash 2>/dev/null || true" >> ~/.bashrc

echo "Done! Run: source ~/.bashrc"
