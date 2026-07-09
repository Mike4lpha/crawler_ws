import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from launch.actions import SetEnvironmentVariable


def generate_launch_description():

    pkg = get_package_share_directory("description")

    # ........................... PATHS ...................................

    urdf_file        = os.path.join(pkg, "urdf", "my_bot.urdf.xacro")
    rviz_config_file = os.path.join(pkg, "config", "rviz_config.rviz")
    bridge_yaml      = os.path.join(pkg, "config", "bridge.yaml")
    world_file       = os.path.join(pkg, "worlds", "my_world.sdf") 

    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    x_pose       = LaunchConfiguration("x_pose",       default="0.0")
    y_pose       = LaunchConfiguration("y_pose",       default="0.0")
    z_pose       = LaunchConfiguration("z_pose",       default="0.05")

    ## .world also works but "sdf version" needs to be present in .world file. So extension doesn't matter, its basically needs sdf file.

    # ........................... LAUNCH ARGS ...................................

    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="true",
        description="Use simulation clock"
    )

    declare_x = DeclareLaunchArgument("x_pose", default_value="0.0")
    declare_y = DeclareLaunchArgument("y_pose", default_value="0.0")
    declare_z = DeclareLaunchArgument("z_pose", default_value="0.05")

    # ........................... ROBOT DESCRIPTION ...................................

    # process xacro → urdf string
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

    # ........................... IGNITION GAZEBO ...................................

    # launch Ignition with world
    ignition = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare("ros_gz_sim"),
                "launch",
                "gz_sim.launch.py"
            ])
        ]),
        launch_arguments={
            "gz_args": ["-r ", world_file],   # -r = run simulation immediately
            "on_exit_shutdown": "true",
        }.items(),
    )

    # spawn robot in Ignition
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_robot",
        output="screen",
        arguments=[
            "-name",  "inspection_bot",
            "-topic", "robot_description",
            "-x",            x_pose,
            "-y",            y_pose,
            "-z",            z_pose,    
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ........................... BRIDGE ...................................

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ros_gz_bridge",
        output="screen",
        arguments=[
            "--ros-args",
            "-p", ["config_file:=", bridge_yaml],
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ros_gz_image_bridge = Node(
    #     package="ros_gz_bridge",
    #     executable="image_bridge",
    #     arguments=["/camera/image_raw"],
    # )

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

    # joint_state_broadcaster must start before diff_drive_controller
    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    diff_drive_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_controller"],
        parameters=[{"use_sim_time": use_sim_time}],
        remappings=[
            ("/diff_drive_controller/cmd_vel_unstamped", "/cmd_vel"),
        ],
    )

    pan_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["pan_controller"],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # controllers need a delay — ros2_control starts after robot spawns
    controllers = TimerAction(
        period=5.0,   # wait 5s for Ignition + robot to be ready
        actions=[
            joint_state_broadcaster,
            diff_drive_controller,
            pan_controller,
        ]
    )

    # ........................... LAUNCH DESCRIPTION ...................................

    return LaunchDescription([

        # args
        declare_use_sim_time,
        declare_x,
        declare_y,
        declare_z,

        # core — order matters
        robot_state_publisher,   # 1. publish robot description
        ignition,                # 2. start Ignition
        spawn_robot,             # 3. spawn robot in Ignition
        bridge,                  # 4. start bridge
        rviz,                    # 5. start RViz
        controllers,             # 6. start controllers (delayed)
        # ros_gz_image_bridge

    ])