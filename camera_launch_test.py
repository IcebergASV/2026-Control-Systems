#!/usr/bin/env python3
import os
from datetime import datetime
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, LogInfo
from launch.event_handlers import OnProcessExit
from launch.substitutions import TextSubstitution

from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Path to the workspace setup 
    ROS_SETUP = TextSubstitution(text="source ~/ros2_ws/install/setup.bash && ")

    # Includes the camera driver launch so the camera node can run in the same launch 
    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("realsense2_camera"), "launch", "rs_launch.py"])
        )
    )

    # Creates a output folder with a timestamp using datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bag_dir = f"/home/jetson/camera_recording_{timestamp}"

    # Recorder: Will run until you manually stop it (CTRL-C in the launch terminal) <<< Important
    recorder_cmd = ROS_SETUP.perform(None) + f'ros2 bag record /camera/camera/color/image_raw /camera/camera/depth/image_rect_raw -o {bag_dir}'
    recorder = ExecuteProcess(
        cmd=['bash', '-lc', recorder_cmd],
        output='screen',
        shell=False
    )

    # Converter: Will start immediately and let it watch for playback/frames
    converter_cmd = ROS_SETUP.perform(None) + 'python3 ~/convert_bag_to_video.py'
    converter = ExecuteProcess(
        cmd=['bash', '-lc', converter_cmd],
        output='screen',
        shell=False
    )

    # Player: Will be launched when recorder exits (After you stop recording)
    player_cmd = ROS_SETUP.perform(None) + f'ros2 bag play {bag_dir}'
    player = ExecuteProcess(
        cmd=['bash', '-lc', player_cmd],
        output='screen',
        shell=False
    )

    # When the recorder exits, start the player
    start_player_on_recorder_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=recorder,
            on_exit=[LogInfo(msg=['Recorder exited, starting playback...']), player]
        )
    )

    # When the player exits, stop the converter (Uses pkill)
    stop_converter_on_player_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=player,
            on_exit=[LogInfo(msg=['Playback finished, stopping converter...']),
                     ExecuteProcess(cmd=['bash', '-lc', 'pkill -f convert_bag_to_video.py || true'], output='screen')]
        )
    )

    ld = LaunchDescription()
    ld.add_action(realsense_launch)
    ld.add_action(converter)
    ld.add_action(recorder)
    ld.add_action(start_player_on_recorder_exit)
    ld.add_action(stop_converter_on_player_exit)

    return ld
