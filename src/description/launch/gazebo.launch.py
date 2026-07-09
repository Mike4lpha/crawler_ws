import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    pkg = get_package_share_directory("description")

    # ........................... PATHS ...................................

    urdf_file        = os.path.join(pkg, "urdf",   "my_bot.urdf.xacro")
    rviz_config_file = os.path.join(pkg, "config", "rviz.rviz")
    world_file       = os.path.join(pkg, "worlds", "my_world.sdf")

    ## both sdf and world works fine, but preffers a .world extension

    # ........................... LAUNCH ARGS ...................................

    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="true",
        description="Use simulation clock"
    )

    # ........................... ROBOT DESCRIPTION ...................................

    robot_description = Command(["xacro ", urdf_file])

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": use_sim_time,
        }],
    )

    # ........................... GAZEBO CLASSIC ...................................

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory("gazebo_ros"),
                "launch",
                "gazebo.launch.py"
            )
        ]),
        launch_arguments={
            "world": world_file,
            "verbose": "false",
        }.items(),
    )

    # spawn robot in Gazebo Classic
    spawn_robot = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        name="spawn_robot",
        output="screen",
        arguments=[
            "-entity",       "inspection_bot",
            "-topic",        "robot_description",
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ........................... RVIZ ...................................

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ........................... CONTROLLERS ...................................

    # joint_state_broadcaster = Node(
    #     package="controller_manager",
    #     executable="spawner",
    #     arguments=["joint_state_broadcaster"],
    #     parameters=[{"use_sim_time": use_sim_time}],
    # )

    # diff_drive_controller = Node(
    #     package="controller_manager",
    #     executable="spawner",
    #     arguments=["diff_drive_controller"],
    #     parameters=[{"use_sim_time": use_sim_time}],
    #     remappings=[
    #         ("/diff_drive_controller/cmd_vel_unstamped", "/cmd_vel"),
    #     ],
    # )

    # pan_controller = Node(
    #     package="controller_manager",
    #     executable="spawner",
    #     arguments=["pan_controller"],
    #     parameters=[{"use_sim_time": use_sim_time}],
    # )

    # controllers = TimerAction(
    #     period=5.0,
    #     actions=[
    #         joint_state_broadcaster,
    #         diff_drive_controller,
    #         pan_controller,
    #     ]
    # )

    # ........................... LAUNCH DESCRIPTION ...................................

    return LaunchDescription([
        declare_use_sim_time,

        robot_state_publisher,   # 1. publish robot description
        gazebo,                  # 2. start Gazebo Classic
        spawn_robot,             # 3. spawn robot
        rviz,                    # 4. start RViz
        # controllers,             # 5. start controllers (delayed)
    ])