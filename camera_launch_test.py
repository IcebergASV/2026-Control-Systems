#!/usr/bin/env python3
from datetime import datetime
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, LogInfo, IncludeLaunchDescription
from launch.event_handlers import OnProcessExit
from launch.substitutions import TextSubstitution, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource

class Camera_launch:
    def __init__(self):
        self.setup = TextSubstitution(text="source ~/ros2_ws/install/setup.bash && ")
        self.execute = ExecuteProcess()
        self.perform = self.setup.perform(None)
        self.event_handler = RegisterEventHandler()
        self.action = self.action()


    def generate_launch_description(self):
        # Includes the camera driver launch so the camera node can run in the same launch 
        realsense_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare("realsense2_camera"), "launch", "rs_launch.py"])
            )
        )

    def output_folder_maker(self):
        # Creates a output folder with a timestamp using datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bag_dir = f"/home/jetson/camera_recording_{timestamp}"

    def recorder(self):
        # Recorder: Will run until you manually stop it (CTRL-C in the launch terminal) <<< Important
        recorder_cmd = self.perform() + f'ros2 bag record /camera/camera/color/image_raw /camera/camera/depth/image_rect_raw -o {bag_dir}'
        recorder = ExecuteProcess(
            cmd=['bash', '-lc', recorder_cmd],
            output='screen',
            shell=False
        )

    def converter(self):
        # Converter: Will start immediately and let it watch for playback/frames
        converter_cmd = self.perform() + 'python3 ~/convert_bag_to_video.py'
        converter = self.execute(
            cmd=['bash', '-lc', converter_cmd],
            output='screen',
            shell=False
        )

    def player(self):
        # Player: Will be launched when recorder exits (After you stop recording)
        player_cmd = self.perform() + f'ros2 bag play {bag_dir}'
        player = self.execute(
            cmd=['bash', '-lc', player_cmd],
            output='screen',
            shell=False
        )

    def start_player(self):
        # When the recorder exits, start the player
        start_player_on_recorder_exit = self.event_handler(
            OnProcessExit(
                target_action= recorder,
                on_exit=[LogInfo(msg=['Recorder exited, starting playback...']), player]
            )
        )
        
    def stop_converter(self):
        # When the player exits, stop the converter (Uses pkill)
        stop_converter_on_player_exit = self.event_handler(
            OnProcessExit(
                target_action= player,
                on_exit=[LogInfo(msg=['Playback finished, stopping converter...']),
                        ExecuteProcess(cmd=['bash', '-lc', 'pkill -f convert_bag_to_video.py || true'], output='screen')]
            )
        )

    def launch_action(self):
        ld = LaunchDescription()
        ld.add_action(realsense_launch)
        ld.add_action(converter)
        ld.add_action(recorder)
        ld.add_action(start_player_on_recorder_exit)
        ld.add_action(stop_converter_on_player_exit)

        return ld
