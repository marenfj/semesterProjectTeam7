from sense_hat import SenseHat
import time
import math

sense = SenseHat()
sense.set_imu_config(True, True, True)

threshold = 200
interval = 0.1

def get_gyroscope():
    gyro = sense.get_gyroscope_raw()
    return gyro['x'], gyro['y'], gyro['z']

def detect_rapid_rotation(x, y, z):
    magnitude = math.sqrt(x**2 + y**2 + z**2)
    return magnitude > threshold

try:
    while True:
        gyro_x, gyro_y, gyro_z = get_gyroscope()
        
        if detect_rapid_rotation(gyro_x, gyro_y, gyro_z):
            sense.show_message("Oh no! It would seem I've tripped, maybe I could get some assistance?", text_colour=[255, 0, 0])
        
        time.sleep(interval)

except KeyboardInterrupt:
    sense.clear()
