# This script will be used to send and receive messages from the Pixhawk
# It will be used to retrieve ASV mission-related information and set missions

from pymavlink import mavutil
from dataclasses import dataclass
from typing import Optional, Final

@dataclass
class VesselPosition:
    lat: float
    long: float
    heading: float
    time_ms: int

@dataclass
class VesselMode:
    mode_id: int
    mode_name: str
    armed: bool

@dataclass
class MissionWaypoint:
    seq: int
    command: int
    lat: float
    long: float
    alt: float
    is_current: bool
    autocontinue: bool

@dataclass
class Mission:
    waypoints: list[MissionWaypoint]
    count: int

@dataclass
class GPSStatus:
    fix_type: int
    fix_name: str
    satellites_visible: int
    hdop: float
    is_healthy: bool

@dataclass
class EKF:
    estimator_attitude: bool
    estimator_vel_horiz: bool
    estimator_pos_horiz_abs: bool
    estimator_gps_glitch: bool
    vel_ratio: float
    pos_horiz_ratio: float 
    mag_ratio: float
    pos_horiz_accuracy: float
    is_healthy: bool

@dataclass
class Battery:
    battery_remaining: int
    voltages: list[int]
    is_healthy: bool

class Pixhawk_Check_Status:

    GPS_FIX_TYPE_MAP = {
        "GPS_FIX_TYPE_NO_GPS": 0,
        "GPS_FIX_TYPE_NO_FIX": 1,
        "GPS_FIX_TYPE_2D_FIX": 2,
        "GPS_FIX_TYPE_3D_FIX": 3,
        "GPS_FIX_TYPE_DGPS": 4,
        "GPS_FIX_TYPE_RTK_FLOAT": 5,
        'GPS_FIX_TYPE_RTK_FIXED': 6,
        "GPS_FIX_TYPE_STATIC": 7,
        "GPS_FIX_TYPE_PPP": 8
    }

    def __init__(self, connection):

        self.master = connection

        pass

    def check_heartbeat(self):
        heartbeat = self.master.recv_match(
            type="HEARTBEAT",
            blocking=True,
            timeout=3
        )
        
        return heartbeat is not None

    def check_gps_fix(self):
        gps_msg = self.master.recv_match(
            type="GPS_RAW_INT",
            blocking=True,
            timeout=3
        )

        if gps_msg is None:
            print("Failed to receive GPS fix from Pixhawk before timeout.")
            return None
        
        fix_type = gps_msg.fix_type

        inverted_result_mapping = {value: key for key, value in self.GPS_FIX_TYPE_MAP.items()}
        fix_name = inverted_result_mapping[fix_type]

        if fix_type < 3:
            print(f'Unable to acquire GPS fix: {fix_name, fix_type}')
            is_healthy = False
        else:
            print(f'GPS fix acquired: {fix_name}')
            is_healthy = True

        return GPSStatus(
            fix_type=fix_type,
            fix_name=fix_name,
            satellites_visible=gps_msg.satellites_visible,
            hdop=gps_msg.eph / 100.0,
            is_healthy=is_healthy
        )

    def check_ekf_status(self):

        ekf_msg = self.master.recv_match(
            type="ESTIMATOR_STATUS",
            blocking=True,
            timeout=3
        )

        if ekf_msg is None:
            print("Failed to receive EKF status from Pixhawk before timeout.")
            return None
        else:
            print("EKF status received.")
        
        flags = ekf_msg.flags
        # Check all relevant flags according to ESTIMATOR_STATUS_FLAGS

        estimator_attitude = bool(flags & mavutil.mavlink.ESTIMATOR_ATTITUDE)
        estimator_vel_horiz = bool(flags & mavutil.mavlink.ESTIMATOR_VELOCITY_HORIZ)
        estimator_pos_horiz_abs = bool(flags & mavutil.mavlink.ESTIMATOR_POS_HORIZ_ABS)
        estimator_gps_glitch = bool(flags & mavutil.mavlink.ESTIMATOR_GPS_GLITCH)

        # Pull other relevant EKF data
        vel_ratio = ekf_msg.vel_ratio
        pos_horiz_ratio = ekf_msg.pos_horiz_ratio
        mag_ratio = ekf_msg.mag_ratio

        # This is in meters
        pos_horiz_accuracy = ekf_msg.pos_horiz_accuracy

        is_healthy = (vel_ratio < 1.0 and pos_horiz_ratio < 1.0 and estimator_pos_horiz_abs and estimator_vel_horiz and
                      estimator_attitude and not estimator_gps_glitch)


        return EKF(
            estimator_attitude=estimator_attitude,
            estimator_vel_horiz=estimator_vel_horiz,
            estimator_pos_horiz_abs=estimator_pos_horiz_abs,
            estimator_gps_glitch=estimator_gps_glitch,
            vel_ratio=vel_ratio,
            pos_horiz_ratio=pos_horiz_ratio,
            mag_ratio=mag_ratio,
            pos_horiz_accuracy=pos_horiz_accuracy,
            is_healthy=is_healthy
        )

    def check_battery(self):

        battery_msg = self.master.recv_match(
            type="BATTERY_STATUS",
            blocking=True,
            timeout=3
        )

        if battery_msg is None:
            print("Failed to receive battery status from Pixhawk before timeout.")
            return None
        else:
            print("Battery status received.")

        battery_remaining = battery_msg.battery_remaining
        voltages = battery_msg.voltages

        is_healthy = battery_remaining >= 90

        return Battery(
            battery_remaining=battery_remaining,
            voltages=voltages,
            is_healthy=is_healthy
        )

    def safety_check(self):

        if not self.check_heartbeat:
            return False

        gps_fix = self.check_gps_fix()
        if gps_fix is None or not gps_fix.is_healthy:
            return False
        
        ekf_status = self.check_ekf_status()
        if ekf_status is None or not ekf_status.is_healthy:
            return False

        battery = self.check_battery()
        if battery is None or not battery.is_healthy:
            return False
        
        return True

class Pixhawk_Read: 

    def __init__(self, connection):

        self.master = connection
        self.current_mission: Optional[Mission] = None
        
        pass

    def get_current_position(self) -> Optional[VesselPosition]:

        position = self.master.recv_match(
            type="GLOBAL_POSITION_INT",
            blocking=True,
            timeout=3
        )

        if position is None:
            print("Failed to read positional data from Pixhawk before timeout.")
            return None
            
        return VesselPosition(
            lat = position.lat / 1e7,
            long = position.lon / 1e7,
            heading = position.hdg,
            time_ms = position.time_boot_ms  
        )

    def get_mode(self) -> Optional[VesselMode]:
        # Create dictionary of modes to mode IDs. Invert dictionary as we need to look up a mode from its ID
        mapping = self.master.mode_mapping()
        inverted_mapping = {value: key for key, value in mapping.items()}

        # Wait for heartbeat message
        heartbeat = self.master.recv_match(
            type="HEARTBEAT",
            blocking=True,
            timeout=3
        )

        if heartbeat is None:
            print("Failed to read vessel mode from Pixhawk before timeout.")
            return None
        # Exract fields from heartbeat message
        custom_mode = heartbeat.custom_mode
        base_mode = heartbeat.base_mode

        armed = bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        
        mode_name = inverted_mapping[custom_mode]

        return VesselMode(
            mode_id = custom_mode,
            mode_name = mode_name,
            armed = armed
        )

    def get_current_mission(self) -> Optional[Mission]:

        # Request mission item list from Pixhawk, may need to update mode in the future
        self.master.mav.mission_request_list_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_MISSION_TYPE_MISSION
        )

        # Receive mission count message from Pixhawk, contains current mission data
        mission_count_msg = self.master.recv_match(
            type="MISSION_COUNT",
            blocking=True,
            timeout=3
        )
        # Error handling if mission count is not received
        if mission_count_msg is None:
            print("Failed to read mission count from Pixhawk before timeout.")
            return None

        # Read count field from the mission count message, returns number of waypoints in mission
        num_waypoints = mission_count_msg.count
        waypoints = []

        if num_waypoints == 0:
            print("No waypoints in current mission. Check that a mission is active.")
            return None

        for seq in range(num_waypoints):

            self.master.mav.mission_request_int_send(
                self.master.target_system,
                self.master.target_component,
                seq,
                mavutil.mavlink.MAV_MISSION_TYPE_MISSION
            )

            mission_item_msg = self.master.recv_match(
                type="MISSION_ITEM_INT",
                blocking=True,
                timeout=3
            )
            # Initialize default values
            lat, long, alt, command, autocontinue = None, None, None, None, None
            is_current = False

            # Error handling if mission item int is not received, might need to change in the future
            if mission_item_msg is None:
                print("Failed to read MISSION_ITEM_INT message from Pixhawk before timeout.")
                waypoints.append(MissionWaypoint(
                    seq=seq,
                    command=command,
                    lat=lat,
                    long=long,
                    alt=alt,
                    is_current=is_current,
                    autocontinue=autocontinue
                )
                                 )
                continue

            if mission_item_msg.seq == seq:
                command = mission_item_msg.command
                is_current = mission_item_msg.current
                autocontinue = mission_item_msg.autocontinue
                alt = mission_item_msg.z

                if mission_item_msg.frame == mavutil.mavlink.MAV_FRAME_GLOBAL_INT:
                    lat = mission_item_msg.x / 1e7
                    long = mission_item_msg.y / 1e7

            waypoints.append(MissionWaypoint
                (
                seq=seq,
                command=command,
                lat=lat,
                long=long,
                alt=alt,
                is_current=is_current,
                autocontinue=autocontinue
                )
            )

        self.master.mav.mission_ack_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_MISSION_ACCEPTED,
            mavutil.mavlink.MAV_MISSION_TYPE_MISSION
        )

        self.current_mission = Mission(waypoints=waypoints, count=num_waypoints)

        return Mission(
            waypoints=waypoints,
            count=num_waypoints
        )
    
class Pixhawk_Write:

    MAV_RESULT_MAP = {
        "MAV_RESULT_ACCEPTED": 0,
        "MAV_RESULT_TEMPORARILY_REJECTED": 1,
        "MAV_RESULT_DENIED": 2,
        "MAV_RESULT_UNSUPPORTED": 3,
        "MAV_RESULT_FAILED": 4,
        "MAV_RESULT_IN_PROGRESS": 5,
        "MAV_RESULT_CANCELLED": 6,
        "MAV_RESULT_COMMAND_LONG_ONLY": 7,
        "MAV_RESULT_COMMAND_INT_ONLY": 8
    }

    def __init__(self, connection):
        
        self.master = connection
        self.checker = Pixhawk_Check_Status(connection)

        pass

    def set_mode(self, mode_id):
        
        # Perform safety checks prior to changing ASV mode
        is_healthy = self.checker.safety_check()
        if not is_healthy:
            return False


        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE,
            0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
            0, 0, 0, 0, 0
        )

        # If command is received, Pixhawk will send an ack message back
        ack = self.master.recv_match(
                type="COMMAND_ACK",
                blocking=True,
                timeout=3
            )
        
        if ack is None:
            print("Failed to receive command acknowledgement from Pixhawk before timeout.")
            return False
        
        command_id = ack.command
        result = ack.result

        if command_id == mavutil.mavlink.MAV_CMD_DO_SET_MODE:
            print("Pixhawk correctly received the command.")
        else:
            print(f'Pixhawk received an incorrect command - returned {command_id}, expected {mavutil.mavlink.MAV_CMD_DO_SET_MODE}')

        # Result status is defined by MAV_RESULT
        
        inverted_result_mapping = {value: key for key, value in self.MAV_RESULT_MAP.items()}
        result_name = inverted_result_mapping[result]

        print(f'Command executed with result and code: {result_name, result}')

        if result == 2 or result == 4:
            print("Command failed.")

        # Add functionality for it to attempt to execute the command again if failed?

        return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def arm(self):

        # Perform necessary safety checks prior to arming
        is_healthy = self.checker.safety_check()
        if not is_healthy:
            return False

        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            mavutil.mavlink.MAV_BOOL_TRUE,
            0,0,0,0,0,0
        )

        # If command is received, Pixhawk will send an ack message back
        ack = self.master.recv_match(
                type="COMMAND_ACK",
                blocking=True,
                timeout=3
            )
        
        if ack is None:
            print("Failed to receive command acknowledgement from Pixhawk before timeout.")
            return False
        
        command_id = ack.command
        result = ack.result

        if command_id == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
            print("Pixhawk correctly received the arming command.")
        else:
            print(f'Pixhawk received an incorrect command - returned {command_id}, expected {mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM}')

        return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def disarm(self):

        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            mavutil.mavlink.MAV_BOOL_FALSE,
            0,0,0,0,0,0
        )

        # If command is received, Pixhawk will send an ack message back
        ack = self.master.recv_match(
                type="COMMAND_ACK",
                blocking=True,
                timeout=3
            )
        
        if ack is None:
            print("Failed to receive command acknowledgement from Pixhawk before timeout.")
            return False
        
        command_id = ack.command
        result = ack.result

        if command_id == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
            print("Pixhawk correctly received the disarming command.")
        else:
            print(f'Pixhawk received an incorrect command - returned {command_id}, expected {mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM}')

        return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def send_mission(self):

        pass

if __name__ == "__main__":

    # REMEMBER TO REPLACE DEVICE WITH ACTUAL DEVICE CONNECTION LINK
    connection = mavutil.mavlink_connection(
            device="replace with device connection",
            baud=57600,
            source_system=255
        )
    connection.wait_heartbeat()

    read_pixhawk = Pixhawk_Read(connection)
    write_pixhawk = Pixhawk_Write(connection)
    check_pixhawk = Pixhawk_Check_Status(connection)
    
