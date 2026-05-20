import pyrealsense2 as rs
import numpy as np

class RealSenseCamera:
    def __init__(self):
        self.control = rs.pipeline()
        self.config = rs.config()

    def start(self):
        self.control.start(self.config)
        print("Camera started.")

    def stop(self):
        self.control.stop()
        print("Camera stopped.")

    def getColorFrame(self):
        frames = self.control.wait_for_frames()
        color_frame = frames.get_color_frame()
        return color_frame
    
    def getDepthFrame(self):
        frames = self.control.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        return depth_frame
    
    def getDepthMargins(self, depth_frame):
        width = depth_frame.get_width()
        height = depth_frame.get_height()
        margins = width, height
        return margins
    
    def depthDataArray(self, depth_frame):
        depth_data = np.asanyarray(depth_frame.get_data())
        return depth_data
    
    def colorDataArray(self, color_frame):
        color_data = np.asanyarray(color_frame.get_data())
        return color_data
    
camera = RealSenseCamera()
camera.start()

for i in range(5):
    camera.getDepthFrame()  # Buffer time for auto-exposure
    
# Example usage:
color_frame = camera.getColorFrame()
depth_frame = camera.getDepthFrame()
margins = camera.getDepthMargins(depth_frame)

depth_data = camera.depthDataArray(depth_frame)
color_data = camera.colorDataArray(color_frame)

camera.stop()




