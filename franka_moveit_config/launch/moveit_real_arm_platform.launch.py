#  Copyright (c) 2021 Franka Emika GmbH
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# This file is an adapted version of
# https://github.com/ros-planning/moveit_resources/blob/ca3f7930c630581b5504f3b22c40b4f82ee6369d/panda_moveit_config/launch/demo.launch.py

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription,
                            Shutdown)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import yaml


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    try:
        with open(absolute_file_path, 'r') as file:
            return yaml.safe_load(file)
    except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
        return None


def generate_launch_description():
    robot_ip_parameter_name = 'robot_ip'
    use_fake_hardware_parameter_name = 'use_fake_hardware'
    load_gripper_parameter_name = 'load_gripper'
    fake_sensor_commands_parameter_name = 'fake_sensor_commands'
    load_camera_parameter_name = 'load_camera'
    planner_parameter_name = 'planner'

    camera_id_parameter_name = 'serial'
    camera_model_parameter_name = 'camera_type'

    robot_ip = LaunchConfiguration(robot_ip_parameter_name)
    use_fake_hardware = LaunchConfiguration(use_fake_hardware_parameter_name)
    load_gripper = LaunchConfiguration(load_gripper_parameter_name)
    fake_sensor_commands = LaunchConfiguration(fake_sensor_commands_parameter_name)
    load_camera = LaunchConfiguration(load_camera_parameter_name)

    camera_id = LaunchConfiguration(camera_id_parameter_name)
    camera_model = LaunchConfiguration(camera_model_parameter_name)

    planner_ = LaunchConfiguration(planner_parameter_name)

    # Command-line arguments
    db_arg = DeclareLaunchArgument(
        'db', default_value='False', description='Database flag'
    )

    # planning_context
    franka_xacro_file = os.path.join(get_package_share_directory('franka_description'), 'robots',
                                     'panda_arm_platform.urdf.xacro')
    robot_description_config = Command(
        [FindExecutable(name='xacro'), ' ', franka_xacro_file, ' hand:=', load_gripper, ' camera:=', load_camera, ' camera_model:=', camera_model,
         ' robot_ip:=', robot_ip, ' use_fake_hardware:=', use_fake_hardware,
         ' fake_sensor_commands:=', fake_sensor_commands])

    robot_description = {'robot_description': robot_description_config}

    franka_semantic_xacro_file = os.path.join(get_package_share_directory('franka_moveit_config'),
                                              'srdf',
                                              'panda_arm_platform.srdf.xacro')
    robot_description_semantic_config = Command(
        [FindExecutable(name='xacro'), ' ', franka_semantic_xacro_file, ' hand:=', load_gripper, ' camera:=', load_camera]
    )
    robot_description_semantic = {
        'robot_description_semantic': robot_description_semantic_config
    }

    kinematics_yaml = load_yaml(
        'franka_moveit_config', 'config/kinematics.yaml'
    )

    # Planning Functionality
    ompl_planning_pipeline_config = {
        'move_group': {
            'planning_plugin': 'ompl_interface/OMPLPlanner',
            'request_adapters': 'default_planner_request_adapters/AddTimeOptimalParameterization '
                                'default_planner_request_adapters/ResolveConstraintFrames '
                                'default_planner_request_adapters/FixWorkspaceBounds '
                                'default_planner_request_adapters/FixStartStateBounds '
                                'default_planner_request_adapters/FixStartStateCollision '
                                'default_planner_request_adapters/FixStartStatePathConstraints',
            'start_state_max_bounds_error': 0.1,
        }
    }
    ompl_planning_yaml = load_yaml(
        'franka_moveit_config', 'config/ompl_planning.yaml'
    )
    ompl_planning_pipeline_config['move_group'].update(ompl_planning_yaml)

    pilz_planning_pipeline_config = {
        'move_group': {
            'planning_plugin': 'pilz_industrial_motion_planner/CommandPlanner',
            'request_adapters': 'default_planner_request_adapters/AddTimeOptimalParameterization '
                                'default_planner_request_adapters/ResolveConstraintFrames '
                                'default_planner_request_adapters/FixWorkspaceBounds '
                                'default_planner_request_adapters/FixStartStateBounds '
                                'default_planner_request_adapters/FixStartStateCollision '
                                'default_planner_request_adapters/FixStartStatePathConstraints',
            'start_state_max_bounds_error': 0.1,
        }
    }
    pilz_planning_yaml = load_yaml(
        'franka_moveit_config', 'config/ompl_planning.yaml'
    )
    pilz_planning_pipeline_config['move_group'].update(pilz_planning_yaml)

    # Trajectory Execution Functionality
    moveit_simple_controllers_yaml = load_yaml(
        'franka_moveit_config', 'config/panda_controllers.yaml'
    )
    moveit_controllers = {
        'moveit_simple_controller_manager': moveit_simple_controllers_yaml,
        'moveit_controller_manager': 'moveit_simple_controller_manager'
                                     '/MoveItSimpleControllerManager',
    }

    trajectory_execution = {
        'moveit_manage_controllers': True,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.01,
    }

    planning_scene_monitor_parameters = {
        'publish_planning_scene': True,
        'publish_geometry_updates': True,
        'publish_state_updates': True,
        'publish_transforms_updates': True,
    }

    combined_planning_pipelines_config = {
        'move_group': {
            'planning_plugin': planner_,
            'request_adapters': 'default_planner_request_adapters/AddTimeOptimalParameterization '
                                'default_planner_request_adapters/ResolveConstraintFrames '
                                'default_planner_request_adapters/FixWorkspaceBounds '
                                'default_planner_request_adapters/FixStartStateBounds '
                                'default_planner_request_adapters/FixStartStateCollision '
                                'default_planner_request_adapters/FixStartStatePathConstraints'
                                'default_planning_request_adapters/CheckStartStateBounds'
                                'default_planning_request_adapters/CheckStartStateCollision'
                                'default_planning_request_adapters/ValidateWorkspaceBounds',
            'start_state_max_bounds_error': 0.1,
            'default_planner_config': 'PTP',
        },
        'robot_description_planning':{
            'cartesian_limits': {
                'max_trans_vel': 0.2,
                'max_trans_acc': 1.0,
                'max_trans_dec': -1.0,
                'max_rot_vel': 0.5
            }
        }
    }
    combined_planning_yaml = load_yaml(
        'franka_moveit_config', 'config/ompl_planning.yaml'
    )
    combined_planning_pipelines_config['move_group'].update(combined_planning_yaml)

    # Start the actual move_group node/action server
    run_move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            combined_planning_pipelines_config,
            trajectory_execution,
            moveit_controllers,
            planning_scene_monitor_parameters,
            {"publish_robot_description_semantic": True},
        ],
    )

    # RViz
    rviz_base = os.path.join(get_package_share_directory('franka_moveit_config'), 'rviz')
    rviz_full_config = os.path.join(rviz_base, 'moveit.rviz')

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='log',
        arguments=['-d', rviz_full_config],
        parameters=[
            robot_description,
            robot_description_semantic,
            ompl_planning_pipeline_config,
            kinematics_yaml,
        ],
    )

    # Publish TF
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
        remappings=[('joint_states', 'franka/joint_states')],
    )

    ros2_controllers_path = os.path.join(
        get_package_share_directory('franka_moveit_config'),
        'config',
        'panda_mock_ros_controllers.yaml' if use_fake_hardware else 'panda_ros_controllers.yaml',
    )

    ros2_control_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[robot_description, ros2_controllers_path], #[ros2_controllers_path]
        remappings=[('joint_states', 'franka/joint_states')],
        output={
            'stdout': 'screen',
            'stderr': 'screen',
        },
        on_exit=Shutdown(),
    )

    # Load controllers
    load_controllers = []
    for controller in ['panda_arm_controller', 'joint_state_broadcaster']:
        load_controllers += [
            ExecuteProcess(
                cmd=['ros2 run controller_manager spawner {}'.format(controller)],
                shell=True,
                output='screen',
            )
        ]

    # Warehouse mongodb server
    db_config = LaunchConfiguration('db')
    mongodb_server_node = Node(
        package='warehouse_ros_mongo',
        executable='mongo_wrapper_ros.py',
        parameters=[
            {'warehouse_port': 33829},
            {'warehouse_host': 'localhost'},
            {'warehouse_plugin': 'warehouse_ros_mongo::MongoDatabaseConnection'},
        ],
        output='screen',
        condition=IfCondition(db_config)
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[
            {'source_list': ['franka/joint_states', 'panda_gripper/joint_states'], 'rate': 30}],
    )
    robot_arg = DeclareLaunchArgument(
        robot_ip_parameter_name,
        description='Hostname or IP address of the robot.')

    use_fake_hardware_arg = DeclareLaunchArgument(
        use_fake_hardware_parameter_name,
        default_value='false',
        description='Use fake hardware')
    
    load_camera_arg = DeclareLaunchArgument(
            load_camera_parameter_name,
            default_value='true',
            description='Use Flir camera as an end-effector, otherwise, the robot is loaded '
                        'without an end-effector.')  
    
    planner_arg = DeclareLaunchArgument(
            planner_parameter_name,
            default_value='ompl_interface/OMPLPlanner',
            description='Choose planner to be used for arm control ') 

    load_gripper_arg = DeclareLaunchArgument(
            load_gripper_parameter_name,
            default_value='false',
            description='Use Franka Gripper as an end-effector, otherwise, the robot is loaded '
                        'without an end-effector.')
    
    camera_id_arg = DeclareLaunchArgument(
            camera_id_parameter_name,
            default_value="'22141921'", 
            description='Camera id, serial number.')

    camera_model_arg = DeclareLaunchArgument(
            camera_model_parameter_name,
            default_value='blackfly_s', 
            description='Camera model, example blackfly_s.')   
    
    fake_sensor_commands_arg = DeclareLaunchArgument(
        fake_sensor_commands_parameter_name,
        default_value='false',
        description="Fake sensor commands. Only valid when '{}' is true".format(
            use_fake_hardware_parameter_name))
    
    gripper_launch_file = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([PathJoinSubstitution(
            [FindPackageShare('franka_gripper'), 'launch', 'gripper.launch.py'])]),
        launch_arguments={'robot_ip': robot_ip,
                          use_fake_hardware_parameter_name: use_fake_hardware}.items(),
        condition=IfCondition(load_gripper)
    )

    camera_launch_file = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([PathJoinSubstitution(
            [FindPackageShare('spinnaker_camera_driver'), 'launch', 'driver_node.launch.py'])]),
        launch_arguments={'camera_type': camera_model,
                          'serial': camera_id}.items(),
        condition=IfCondition(load_camera)
    )

    return LaunchDescription(
        [robot_arg,
         use_fake_hardware_arg,
         fake_sensor_commands_arg,
         load_gripper_arg,
         load_camera_arg,
         planner_arg,
         camera_id_arg,
         camera_model_arg,
         db_arg,
         rviz_node,
         run_move_group_node,
         robot_state_publisher,
         ros2_control_node,
         mongodb_server_node,
         joint_state_publisher,
         gripper_launch_file,
         camera_launch_file,
         *load_controllers])
