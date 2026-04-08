import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python import get_package_share_directory
import xacro


def generate_launch_description():
    pkg_share = get_package_share_directory('rover_gazebosim')

    # Gazebo resource path
    set_env = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=os.path.join(pkg_share, '..')
    )

    # Plugin path so Gazebo can find ign_ros2_control
    set_plugin_env = SetEnvironmentVariable(
        name='IGN_GAZEBO_SYSTEM_PLUGIN_PATH',
        value='/opt/ros/humble/lib'
    )

    world_path = os.path.join(pkg_share, 'worlds', 'world.sdf')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch', 'gz_sim.launch.py'
            )
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items()
    )

    urdf_file = os.path.join(pkg_share, 'urdf', 'rover.urdf')
    robot_desc_xml = xacro.process_file(urdf_file).toxml()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_desc_xml}]
    )

    # NOTE: joint_state_publisher_gui removed — conflicts with controller
    # Use ros2 topic echo /joint_states to monitor instead

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-string', robot_desc_xml,
            '-name', 'rover',
            '-x', '0', '-y', '0', '-z', '0.5',
            '-R', '0', '-P', '0', '-Y', '0'
        ],
        output='screen'
    )

    # Wait 5s for Gazebo to fully load then spawn broadcasters/controllers
    joint_state_broadcaster = TimerAction(period=5.0, actions=[
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joint_state_broadcaster'],
            output='screen'
        )
    ])

    position_controller = TimerAction(period=6.0, actions=[
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joint_group_position_controller'],
            output='screen'
        )
    ])

    gazebo_bridge = TimerAction(period=7.0, actions=[
        Node(
            package='rover_gazebosim',
            executable='gazebo_bridge',
            name='gazebo_bridge_node',
            output='screen',
            parameters=[{'use_sim_time': True}]
        )
    ])

    return LaunchDescription([
        set_env,
        set_plugin_env,
        gazebo,
        robot_state_publisher,
        spawn_entity,
        joint_state_broadcaster,
        position_controller,
        gazebo_bridge,
    ])