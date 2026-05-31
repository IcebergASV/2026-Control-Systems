import pyrealsense2 as rs
import numpy as np
import readchar as rc
import threading as th        # built-in, no installation required

key_input = None
running = True

def quitThread():
    global key_input, running
    while running:
        key_input = rc.readkey()
        if key_input == 'q':
            running = False

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
        margins = (color_frame.get_width(), color_frame.get_height())
        return color_frame, margins
    
    def getDepthFrame(self):
        frames = self.control.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        margins = (depth_frame.get_width(), depth_frame.get_height())
        return depth_frame, margins
    
    def depthDataArray(self):
        depth_data = np.asanyarray(self.getDepthFrame()[0].get_data())
        return depth_data
    
    def colorDataArray(self):
        color_data = np.asanyarray(self.getColorFrame()[0].get_data())
        return color_data

controlThread = th.Thread(target=quitThread, daemon=True)
controlThread.start()

camera = RealSenseCamera()
try:
    camera.start()
    
except RuntimeError as e:
    print(f"Error starting camera: {e}")
    exit(1)

for i in range(5):
    camera.getDepthFrame()  # Buffer time for auto-exposure

try:
    while running:
        color_frame = camera.getColorFrame()
        depth_frame = camera.getDepthFrame()
        margins = camera.getDepthMargins(depth_frame)
        
        depth_data = camera.depthDataArray(depth_frame)
        color_data = camera.colorDataArray(color_frame)

except KeyboardInterrupt:
    camera.stop()
    exit(1)



