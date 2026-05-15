#!/bin/bash
set -e

source /opt/ros/humble/setup.bash

ROS2_WS=/workspaces/ws_sereact/ros_ws

# Start the WMS server in the background
nohup uvicorn api.wms_server:app --port 8081 --log-level debug > log/nohup.out 2>&1 &
echo $! > log/wms_server.pid

# Wait for server to be ready
if ! timeout 60 bash -c '
until curl -s http://localhost:8081/health > /dev/null 2>&1; do
    sleep 0.5
done
'; then
    echo "Server did not become ready within 60 seconds"
    exit 1
fi

echo "WMS server started successfully on port 8081"

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


