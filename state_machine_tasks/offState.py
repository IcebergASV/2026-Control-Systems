import time
from pymavlink import mavutil

# IMPORTANTNOTE: Do not run commands against the real boat until you’ve verified channel mapping and safe PWM on a bench with props removed.

def off_state(connection, thruster_channels, safe_pwm=1500, verify_timeout=3, wait_after_override=0.5):
    """
    Parameters:
      - connection: mavutil connection (same object you pass to Pixhawk_Read/Write)
      - thruster_channels: list of 1-based RC/servo channel indices controlling thrusters (e.g., [1,2,3,4])
      - safe_pwm: PWM value to set for each thruster (default 1500 neutral)
      - verify_timeout: seconds to wait for feedback messages
      - wait_after_override: seconds to wait after sending override before reading feedback
    Returns:
      - True if off sequence succeeded (thrusters set and vehicle disarmed), False otherwise.
    Notes:
      - This function uses RC_CHANNELS_OVERRIDE by default. If your firmware ignores overrides,
        switch to sending MAV_CMD_DO_SET_SERVO per-channel (see commented alternative below).
    """

    # 1) Basic heartbeat check (vehicle responsive)
    hb = connection.recv_match(type='HEARTBEAT', blocking=True, timeout=3)
    if hb is None:
        print("No heartbeat from vehicle; aborting off sequence.")
        return False

    # 2) Build RC override payload (18 channels, 0 = no override)
    overrides = [0] * 18
    for ch in thruster_channels:
        if 1 <= ch <= 18:
            overrides[ch - 1] = int(safe_pwm)
        else:
            print(f"Channel {ch} out of range (1-18). Aborting.")
            return False

    # 3) Send RC_CHANNELS_OVERRIDE
    connection.mav.rc_channels_override_send(
        connection.target_system,
        connection.target_component,
        *overrides
    )

    # 4) Wait briefly for outputs to settle
    time.sleep(wait_after_override)

    # 5) Verify servo outputs changed (SERVO_OUTPUT_RAW)
    servo = connection.recv_match(type='SERVO_OUTPUT_RAW', blocking=True, timeout=verify_timeout)
    if servo is None:
        print("No SERVO_OUTPUT_RAW feedback; cannot verify thruster outputs.")
        # Not fatal here — continue to attempt disarm, but warn user
    else:
        # Check each requested channel's raw value (fields are servo1_raw ... servo18_raw)
        mismatch = False
        for ch in thruster_channels:
            field_name = f"servo{ch}_raw"
            if hasattr(servo, field_name):
                val = getattr(servo, field_name)
                if val != 0 and abs(val - safe_pwm) > 50:  # tolerance
                    print(f"Warning: channel {ch} servo output {val} differs from requested {safe_pwm}.")
                    mismatch = True
            else:
                # Some mavlink versions expose servo fields differently; skip strict check
                pass

        if mismatch:
            print("One or more thruster outputs did not match requested safe PWM. Proceeding to disarm anyway.")

    # 6) Send disarm command (MAV_CMD_COMPONENT_ARM_DISARM)
    connection.mav.command_long_send(
        connection.target_system,
        connection.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        mavutil.mavlink.MAV_BOOL_FALSE,  # param1 = 0 -> disarm
        0,0,0,0,0,0
    )

    # 7) Wait for COMMAND_ACK
    ack = connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=verify_timeout)
    if ack is None:
        print("No COMMAND_ACK received for disarm command.")
        return False

    # 8) Check ack result
    if hasattr(ack, 'result'):
        if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("Disarm command accepted by vehicle.")
        else:
            print(f"Disarm command returned result code {ack.result}.")
            # continue to verify heartbeat state anyway

    # 9) Verify heartbeat shows disarmed
    hb2 = connection.recv_match(type='HEARTBEAT', blocking=True, timeout=verify_timeout)
    if hb2 is None:
        print("No heartbeat after disarm; cannot confirm disarmed state.")
        return False

    armed_flag = bool(hb2.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
    if not armed_flag:
        print("Vehicle is disarmed and thrusters were commanded to safe PWM.")
        return True
    else:
        print("Vehicle still reports armed. Off sequence incomplete.")
        return False


# -------------------------
# Alternative: per-servo DO_SET_SERVO (uncomment and use if RC override is ignored)
# def set_servo_pwm(connection, channel, pwm, timeout=3):
#     connection.mav.command_long_send(
#         connection.target_system,
#         connection.target_component,
#         mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
#         0,
#         channel,  # param1 = servo number (1-based)
#         pwm,      # param2 = PWM
#         0,0,0,0,0
#     )
#     ack = connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=timeout)
#     return ack is not None and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED
#
# To use DO_SET_SERVO instead of RC override, loop set_servo_pwm for each thruster channel before disarm.