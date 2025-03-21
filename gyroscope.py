import time
import threading
import paho.mqtt.client as mqtt
from sense_hat import SenseHat

BROKER_ADDRESS = "mqtt20.iik.ntnu.no"
SCOOTER_ID = "scooter123"
CRASH_THRESHOLD = 2.5
TOPIC_ALERTS = f"scooter/{SCOOTER_ID}/alerts"

sense = SenseHat()
sense.clear()

panic_mode_active = False
last_panic_press_time = 0
PANIC_CANCEL_WINDOW = 2

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code:", rc)

def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode('utf-8')}")

client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_ADDRESS, 1883, 60)
client.loop_start()

def flash_led(color=(255, 0, 0), duration=2):
    start_time = time.time()
    while (time.time() - start_time) < duration:
        sense.clear(color)
        time.sleep(0.3)
        sense.clear()
        time.sleep(0.3)

def publish_alert(alert_type):
    message = {
        "scooter_id": SCOOTER_ID,
        "alert_type": alert_type,
        "timestamp": time.time()
    }
    client.publish(TOPIC_ALERTS, str(message))
    print("Published:", message)

def detect_crash(accel_data):
    x, y, z = accel_data
    total_g = ((x**2) + (y**2) + (z**2)) ** 0.5 / 9.81  # Convert m/s^2 to Gs
    return total_g > CRASH_THRESHOLD

def handle_joystick(event):
    global panic_mode_active, last_panic_press_time

    if event.action == "pressed" and event.direction == "middle":
        now = time.time()

        # Cancel panic if pressed again within the cancel window
        if panic_mode_active and (now - last_panic_press_time) < PANIC_CANCEL_WINDOW:
            publish_alert("CANCEL")
            panic_mode_active = False
            sense.clear()
            print("Panic canceled.")
            return

        panic_mode_active = True
        last_panic_press_time = now
        publish_alert("PANIC")
        flash_led(color=(255, 0, 0), duration=1)
        print("Panic mode active.")

sense.stick.direction_any = handle_joystick

def main_loop():
    while True:
        raw_accel = sense.get_accelerometer_raw()
        accel_tuple = (raw_accel["x"] * 9.81,
                       raw_accel["y"] * 9.81,
                       raw_accel["z"] * 9.81)

        if detect_crash(accel_tuple):
            print("Crash detected!")
            publish_alert("CRASH")
            flash_led(color=(255, 0, 0), duration=1)

        time.sleep(0.5)

if __name__ == "__main__":
    try:
        print("E-Scooter Pi code running. Press Ctrl+C to stop.")
        main_loop()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        sense.clear()
        client.loop_stop()
        client.disconnect()