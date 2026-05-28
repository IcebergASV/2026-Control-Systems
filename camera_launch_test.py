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
        self.execute = ExecuteProcess(cmd=[], output='screen', shell = False)
        self.perform = self.setup.perform(None)
        self.action = self.action()


    def generate_launch_description(self):
        # Includes the camera driver launch so the camera node can run in the same launch 
        realsense_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare("realsense2_camera"), "launch", "rs_launch.py"])
            )
        )
        return realsense_launch

    def output_folder_maker(self):
        # Creates a output folder with a timestamp using datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bag_dir = f"/home/jetson/camera_recording_{timestamp}"
        return bag_dir

    def recorder(self):
        # Recorder: Will run until you manually stop it (CTRL-C in the launch terminal) <<< Important
        recorder_cmd = self.perform() + f'ros2 bag record /camera/camera/color/image_raw /camera/camera/depth/image_rect_raw -o {self.output_folder_maker()}'
        recorder = ExecuteProcess(
            cmd=['bash', '-lc', recorder_cmd],
            output='screen',
            shell=False
        )
        return recorder

    def converter(self):
        # Converter: Will start immediately and let it watch for playback/frames
        converter_cmd = self.perform() + 'python3 ~/convert_bag_to_video.py'
        converter = self.execute(
            cmd=['bash', '-lc', converter_cmd],
            output='screen',
            shell=False
        )
        return converter

    def player(self):
        # Player: Will be launched when recorder exits (After you stop recording)
        player_cmd = self.perform() + f'ros2 bag play {self.output_folder_maker()}'
        player = self.execute(
            cmd=['bash', '-lc', player_cmd],
            output='screen',
            shell=False
        )
        return player

    def start_player(self):
        # When the recorder exits, start the player
        start_player_on_recorder_exit = RegisterEventHandler(
            OnProcessExit(
                target_action= recorder,
                on_exit=[LogInfo(msg=['Recorder exited, starting playback...']), player]
            )
        )
        return start_player_on_recorder_exit
        
    def stop_converter(self):
        # When the player exits, stop the converter (Uses pkill)
        stop_converter_on_player_exit = RegisterEventHandler(
            OnProcessExit(
                target_action= player,
                on_exit=[LogInfo(msg=['Playback finished, stopping converter...']),
                        ExecuteProcess(cmd=['bash', '-lc', 'pkill -f convert_bag_to_video.py || true'], output='screen')]
            )
        )
        return stop_converter_on_player_exit


def launch_action():
    ld = LaunchDescription()
    ld.add_action(realsense_launch)
    ld.add_action(converter)
    ld.add_action(recorder)
    ld.add_action(start_player_on_recorder_exit)
    ld.add_action(stop_converter_on_player_exit)

    return ld

#Function calls
launch = Camera_launch()

generate_launch = launch.generate_launch_description()
output_folder = launch.output_folder_maker()
recorder = launch.recorder()
converter = launch.converter()
player = launch.player()
start = launch.start_player()
stop_converter = launch.stop_converter()
launch_action = launch.launch_action()
