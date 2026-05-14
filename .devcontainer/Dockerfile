FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-humble-rmw-cyclonedds-cpp \
    python3-pip \
    python3-dev \
    bash-completion \
    locales \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    httpx \
    websockets \
    pydantic

RUN useradd -m -s /bin/bash ros \
    && echo "ros ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN rosdep init || true && rosdep update

RUN echo "source /opt/ros/humble/setup.bash" >> /home/ros/.bashrc \
    && echo "export ROS_DOMAIN_ID=0" >> /home/ros/.bashrc \
    && echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> /home/ros/.bashrc

WORKDIR /workspaces/ws_sereact
USER ros
