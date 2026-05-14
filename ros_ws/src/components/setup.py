from setuptools import find_packages, setup

package_name = "components"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ros",
    maintainer_email="josephjoel3099@gmail.com",
    description="TODO: Package description",
    license="TODO: License declaration",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "scanner = components.scanner:main",
            "door = components.door:main",
            "emergency_stop = components.emergency_stop:main",
            "stack_light = components.stack_light:main",
            "robot_cell = components.robot_cell_client:main",
        ],
    },
)
