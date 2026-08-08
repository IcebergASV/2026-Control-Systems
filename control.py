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
    
    def depthDataArray(self, array):
        depth_data = self.getDepthFrame()[0].get_data()
        depth_array = np.append(array, depth_data)
        return depth_array
    
    def colorDataArray(self, array):
        color_data = self.getColorFrame()[0].get_data()
        color_array = np.append(array, color_data)
        return color_array
        
    def get_depth_at_pixel(self, x, y):
        d_frame = self.getDepthFrame()

        try:
            if x < 0 or x >= d_frame[1][0] or y < 0 or y >= d_frame[1][1]:
                raise ValueError("Pixel coordinates are out of bounds.")

            else:
                depth_value = float(d_frame[0].get_distance(x, y))
                return depth_value
            
        except Exception as e:
            print(f"Error occurred while fetching depth at pixel ({x}, {y}): {e}")
            return None

class ZEDCamera:
    def __init__(self):
            self.camera = zed.Camera()
        self.init_params = zed.InitParameters()
        self.init_params.camera_resolution = zed.RESOLUTION.HD2K
        self.init_params.camera_fps = 15
        self.init_params.coordinate_units = zed.UNIT.METER
        self.init_params.depth_mode = zed.DEPTH_MODE.ULTRA
        self.runtime_parameters = zed.RuntimeParameters()
        self.runtime_parameters.sensing_mode = zed.SENSING_MODE.STANDARD

    def startup(self):
        err = self.camera.open(self.init_params)
        if err != zed.ERROR_CODE.SUCCESS:
            print(f"Error starting ZED camera: {err}")
            exit(1)
        print("ZED camera started.")

    def get_depth_at_pixel(self, x, y):
        try:
            if x < 0 or x >= self.camera.get_resolution().width or y < 0 or y >= self.camera.get_resolution().height:
                raise ValueError("Pixel coordinates are out of bounds.")

            depth_value = zed.Mat()
            self.camera.retrieve_measure(depth_value, zed.MEASURE.DEPTH)
            depth_array = depth_value.get_data()
            depth_at_pixel = float(depth_array[y, x])
            return depth_at_pixel

        except Exception as e:
            print(f"Error occurred while fetching depth at pixel ({x}, {y}): {e}")
            return None

    def get_color_at_pixel(self, x, y):
        try:
            if x < 0 or x >= self.camera.get_resolution().width or y < 0 or y >= self.camera.get_resolution().height:
                raise ValueError("Pixel coordinates are out of bounds.")

            color_value = zed.Mat()
            self.camera.retrieve_image(color_value, zed.VIEW.LEFT)
            color_array = color_value.get_data()
            color_at_pixel = color_array[y, x]
            return color_at_pixel

        except Exception as e:
            print(f"Error occurred while fetching color at pixel ({x}, {y}): {e}")
            return None

    def shutdown(self):
        self.camera.close()
        print("ZED camera stopped. Saving video...")
        try:
            self.camera.enable_recording("zed_video.svo", zed.SVO_COMPRESSION_MODE.H264)
            print("Video saved successfully.")
        except Exception as e:
            print(f"Error saving video: {e}")

def RSTest():
    depth_array = np.array([])
    color_array = np.array([])
    
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
            print("Gathering data...")
            
            depth_array = camera.depthDataArray(depth_array)
            color_array = camera.colorDataArray(color_array)
    
    except KeyboardInterrupt:
        pass
    
    finally:
        camera.stop()

def ZEDTest():
    camera = ZEDCamera()
    try:
        camera.startup()
    except RuntimeError as e:
        print(f"Error starting ZED camera: {e}")
        exit(1)

    try:
        while running:
            depth_at_pixel = camera.get_depth_at_pixel(100, 100)
            color_at_pixel = camera.get_color_at_pixel(100, 100)

            print(f"Depth at (100, 100): {depth_at_pixel}")
            print(f"Color at (100, 100): {color_at_pixel}")
            print("\n")
    except KeyboardInterrupt:
        pass
    finally:
        camera.shutdown()

def main():
    global running
    controlThread = th.Thread(target=quitThread, daemon=True)
    controlThread.start()

    choice_dict = {"1" : RSTest(), "2" : ZEDTest()}
    choice = input("Please choose a camera test: press 1 for Realsense and 2 for ZED")

    if choice in choice_dict.keys():
        choice_dict[choice]
    
if __name__ == "__main__":
    main()
