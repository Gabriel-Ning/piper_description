from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
import os
import sys
import xacro


def _optional_xacro_args(context: LaunchContext, *names):
    """Forward launch args to xacro only when the user set them."""
    mappings = {}
    for name in names:
        value = context.perform_substitution(LaunchConfiguration(name))
        if value:
            mappings[name] = value
    return mappings


def robot_state_publisher_spawner(context: LaunchContext):
    share = get_package_share_directory("piper_description")

    with_gripper = LaunchConfiguration("with_gripper")
    use_joint_state_gui = LaunchConfiguration("use_joint_state_gui")
    joint_states_topic = LaunchConfiguration("joint_states_topic")
    with_gripper_str = context.perform_substitution(with_gripper)
    base_xacro = str(
        PathJoinSubstitution([share, "urdf", "piper.urdf.xacro"]).perform(context)
    )
    gripper_xacro = str(
        PathJoinSubstitution([share, "urdf", "piper_with_gripper.urdf.xacro"]).perform(
            context
        )
    )

    base_mappings = {
        "ros2_control": "false",
        "use_fake_hardware": "true",
        **_optional_xacro_args(
            context, "prefix", "connected_to", "xyz", "rpy"
        ),
    }

    if with_gripper_str == "true":
        gripper_mappings = {
            **base_mappings,
            **_optional_xacro_args(
                context, "xyz_ee", "rpy_ee", "tcp_xyz", "tcp_rpy"
            ),
        }
        robot_description = xacro.process_file(
            gripper_xacro, mappings={**gripper_mappings, "load_gripper": "true"}
        ).toprettyxml(indent="  ")
    else:
        robot_description = xacro.process_file(
            base_xacro, mappings=base_mappings
        ).toprettyxml(indent="  ")

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
            condition=IfCondition(use_joint_state_gui),
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
            condition=UnlessCondition(use_joint_state_gui),
            parameters=[{"robot_description": robot_description}],
            remappings=[("joint_states", joint_states_topic)],
        ),
    ]


def generate_launch_description() -> LaunchDescription:
    share = get_package_share_directory("piper_description")
    use_rviz = LaunchConfiguration("use_rviz")
    rviz_config = PathJoinSubstitution([share, "rviz", "visualize_piper.rviz"])

    robot_state_publisher_spawner_opaque_function = OpaqueFunction(
        function=robot_state_publisher_spawner
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["--display-config", rviz_config],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("with_gripper", default_value="false"),
            DeclareLaunchArgument("prefix", default_value=""),
            DeclareLaunchArgument("connected_to", default_value=""),
            DeclareLaunchArgument("xyz", default_value=""),
            DeclareLaunchArgument("rpy", default_value=""),
            DeclareLaunchArgument("xyz_ee", default_value=""),
            DeclareLaunchArgument("rpy_ee", default_value=""),
            DeclareLaunchArgument("tcp_xyz", default_value=""),
            DeclareLaunchArgument("tcp_rpy", default_value=""),
            DeclareLaunchArgument("use_joint_state_gui", default_value="false"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument(
                "joint_states_topic", default_value="/piper_description/joint_states"
            ),
            robot_state_publisher_spawner_opaque_function,
            rviz,
        ]
    )
