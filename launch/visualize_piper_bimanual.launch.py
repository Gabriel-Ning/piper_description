# Copyright 2026
# SPDX-License-Identifier: Apache-2.0
"""Visualize the dual-arm Piper + experiment-table cell."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os
import sys
import xacro


def _optional_xacro_args(context, *names):
    """Forward launch args to xacro only when the user set them."""
    mappings = {}
    for name in names:
        value = LaunchConfiguration(name).perform(context)
        if value:
            mappings[name] = value
    return mappings


def _nodes(context):
    share = get_package_share_directory("piper_description")
    xacro_path = os.path.join(
        share, "urdf", "piper_bimanual_manipulation.urdf.xacro"
    )
    mappings = {
        "enable_left": "true",
        "enable_right": "true",
        "enable_left_gripper": LaunchConfiguration("enable_grippers").perform(context),
        "enable_right_gripper": LaunchConfiguration("enable_grippers").perform(context),
        "use_fake_hardware": "true",
    }
    mappings.update(
        _optional_xacro_args(
            context, "left_xyz", "right_xyz", "left_rpy", "right_rpy"
        )
    )
    robot_description = xacro.process_file(
        xacro_path, mappings=mappings
    ).toprettyxml(indent="  ")
    joint_states_topic = LaunchConfiguration("joint_states_topic").perform(context)
    use_gui = LaunchConfiguration("use_joint_state_gui")
    return [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description}],
            remappings=[("joint_states", joint_states_topic)],
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            name="joint_state_publisher_gui",
            condition=IfCondition(use_gui),
            parameters=[{"robot_description": robot_description}],
            remappings=[("joint_states", joint_states_topic)],
            # python_qt_binding expects CONDA_PREFIX, while pixi exposes the
            # environment through sys.prefix instead.
            additional_env={"CONDA_PREFIX": os.environ.get("CONDA_PREFIX", sys.prefix)},
        ),
        Node(
            package="joint_state_publisher",
            executable="joint_state_publisher",
            name="joint_state_publisher",
            condition=UnlessCondition(use_gui),
            parameters=[{"robot_description": robot_description}],
            remappings=[("joint_states", joint_states_topic)],
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            arguments=[
                "-d",
                os.path.join(share, "rviz", "visualize_piper.rviz"),
            ],
            condition=IfCondition(LaunchConfiguration("use_rviz")),
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("enable_grippers", default_value="true"),
            DeclareLaunchArgument("left_xyz", default_value=""),
            DeclareLaunchArgument("right_xyz", default_value=""),
            DeclareLaunchArgument("left_rpy", default_value=""),
            DeclareLaunchArgument("right_rpy", default_value=""),
            DeclareLaunchArgument("use_joint_state_gui", default_value="true"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument(
                "joint_states_topic",
                default_value="/piper_description/joint_states",
            ),
            OpaqueFunction(function=_nodes),
        ]
    )
