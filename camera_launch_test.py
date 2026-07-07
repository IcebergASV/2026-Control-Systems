#!/usr/bin/env python3
import time
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, LogInfo, IncludeLaunchDescription
from launch.event_handlers import OnProcessExit
from launch.substitutions import TextSubstitution, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource


class Camera_launch:
    def __init__(self):
        # Path to the workspace setup 
        self.setup = TextSubstitution(text="source ~/ros2_ws/install/setup.bash && ")
        self.perform = self.setup.perform(None)

        # Creates a output folder
        self.bag_dir = self.output_folder_maker()

        # Placeholders for the processes
        self.recorder_process = None
        self.converter_process = None
        self.player_process = None


    def generate_launch_description(self):
        # Includes the camera driver launch so the camera node can run in the same launch 
        realsense_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    FindPackageShare("realsense2_camera"),
                    "launch",
                    "rs_launch.py"
                ])
            )
        )

        # Build all actions
        converter = self.converter()
        recorder = self.recorder()
        player = self.player()
        start_player_handler = self.start_player()
        stop_converter_handler = self.stop_converter()

        # Build launch description
        ld = LaunchDescription()
        ld.add_action(realsense_launch)
        ld.add_action(converter)
        ld.add_action(recorder)
        ld.add_action(start_player_handler)
        ld.add_action(stop_converter_handler)

        return ld


    def output_folder_maker(self):
        # Creates a output folder with a timestamp using time 
        # When it ends the timestamp will be for however long the Jetson was running for in seconds
        timestamp = int(time.monotonic())
        return f"/home/jetson/camera_recording_{timestamp}"


    def recorder(self):
        # Recorder: Will run until you manually stop it (CTRL-C in the launch terminal) <<< Important
        recorder_cmd = (
            self.perform +
            f"ros2 bag record /camera/camera/color/image_raw "
            f"/camera/camera/depth/image_rect_raw -o {self.bag_dir}"
        )

        self.recorder_process = ExecuteProcess(
            cmd=['bash', '-lc', recorder_cmd],
            output='screen'
        )
        return self.recorder_process


    def converter(self):
        # Converter: Will start immediately and let it watch for playback/frames
        converter_cmd = self.perform + "python3 ~/convert_bag_to_video.py"

        self.converter_process = ExecuteProcess(
            cmd=['bash', '-lc', converter_cmd],
            output='screen'
        )
        return self.converter_process


    def player(self):
        # Player: Will be launched when recorder exits (After you stop recording)
        player_cmd = self.perform + f"ros2 bag play {self.bag_dir}"

        self.player_process = ExecuteProcess(
            cmd=['bash', '-lc', player_cmd],
            output='screen'
        )
        return self.player_process


    def start_player(self):
        # When the recorder exits, start the player
        return RegisterEventHandler(
            OnProcessExit(
                target_action=self.recorder_process,
                on_exit=[
                    LogInfo(msg=['Recorder exited, starting playback...']),
                    self.player_process
                ]
            )
        )


    def stop_converter(self):
        # When the player exits, stop the converter (Uses pkill)
        return RegisterEventHandler(
            OnProcessExit(
                target_action = self.player_process,
                on_exit = [
                    LogInfo(msg = ['Playback finished, stopping converter...']),
                    ExecuteProcess(
                        cmd=['bash', '-lc', 'pkill -f convert_bag_to_video.py || true'],
                        output='screen'
                    )
                ]
            )
        )
    
# Launchs the program
def generate_launch_description():
    launch = Camera_launch()
    return launch.generate_launch_description()
