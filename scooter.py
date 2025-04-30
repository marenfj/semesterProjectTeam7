import time
import datetime
import threading
import math
import json
import os
from sense_hat import SenseHat, ACTION_PRESSED
import paho.mqtt.client as mqtt

# Constants provided in the specification
BROKER_ADDRESS = "mqtt20.iik.ntnu.no"
SCOOTER_ID = "scooter123"
CRASH_THRESHOLD = 2.5
TOPIC_ALERTS = f"scooter/{SCOOTER_ID}/alerts"
PANIC_MP3_PATH = "panic.mp3"         # Path to the alarm (panic) sound
NOTIFIED_MP3_PATH = "notified.mp3"     # Path to the notified sound
CANCELLED_MP3_PATH = "cancelled.mp3"

class EScooterSystem:
    def __init__(self):
        # Initialize Sense HAT and clear LEDs at startup
        self.sense = SenseHat()
        self.sense.clear()
        
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        self.state = "IDLE"  # States: IDLE, ALERT_PENDING, CANCELLED
        self.alert_timer = None
        self.timeout_timer = None
        self.alert_lock = threading.RLock()
        self.alert_start_time = None

        # Connect to MQTT broker
        try:
            self.mqtt_client.connect(BROKER_ADDRESS)
            self.mqtt_client.loop_start()
            print(f"Connected to MQTT Broker at {BROKER_ADDRESS}")
        except Exception as e:
            print("Error connecting to MQTT Broker:", e)
        
        # Set up the joystick (middle button)
        # In IDLE, a press triggers alert mode.
        # In ALERT_PENDING, a press cancels the alert.
        self.sense.stick.direction_middle = self.panic_button_pressed

    def panic_button_pressed(self, event):
        if event.action != ACTION_PRESSED:
            return
        with self.alert_lock:
            if self.state == "IDLE":
                print("Panic button pressed: starting alert mode.")
                self.start_alert(alert_type="panic")
            elif self.state == "ALERT_PENDING":
                print("Panic button pressed during alert: cancelling alert and sending cancellation message.")
                self.cancel_alert_and_notify()

    def alarm_sound_loop(self):
        """Play the alarm sound (panic.mp3) repeatedly for the first 30 seconds."""
        start_time = datetime.datetime.now()
        while self.state == "ALERT_PENDING" and (datetime.datetime.now() - start_time).total_seconds() < 30:
            print("Playing alarm sound (panic)")
            os.system(f"play {PANIC_MP3_PATH}")
            # Loop repeats as long as conditions hold.

    def notified_sound_loop(self):
        """After 30 seconds, play the notified sound repeatedly until timeout (one hour) or cancellation."""
        print("Starting notified sound loop")
        while self.state == "ALERT_PENDING":
            print("Playing notified sound")
            os.system(f"play {NOTIFIED_MP3_PATH}")
            time.sleep(1) 


    def start_notified_sound_loop(self):
        with self.alert_lock:
            if self.state == "ALERT_PENDING":
                threading.Thread(target=self.notified_sound_loop, daemon=True).start()

    def start_alert(self, alert_type):
        """
        Enter ALERT_PENDING state:
         - Start blinking LEDs.
         - Start playing the alarm sound (panic.mp3) repeatedly for 30 seconds.
         - Start a timer for 30 seconds to launch the notified sound loop if not cancelled.
         - Also, start a one-hour timeout timer.
        """
        with self.alert_lock:
            self.state = "ALERT_PENDING"
            self.alert_start_time = datetime.datetime.now()
        threading.Thread(target=self.blink_red, daemon=True).start()
        threading.Thread(target=self.alarm_sound_loop, daemon=True).start()
        
        # After 30 seconds, if still in ALERT_PENDING, start the notified sound loop.
        self.alert_timer = threading.Timer(30, self.start_notified_sound_loop)
        self.alert_timer.start()

        # One-hour timeout as a backup to reset the system.
        self.timeout_timer = threading.Timer(3600, self.timeout_alert)
        self.timeout_timer.start()

    def blink_red(self):
        """Continuously blink the LED matrix red while in ALERT_PENDING state."""
        red = (255, 0, 0)
        off = (0, 0, 0)
        while self.state == "ALERT_PENDING":
            self.sense.clear(red)
            time.sleep(0.5)
            self.sense.clear(off)
            time.sleep(0.5)

    def cancel_alert_and_notify(self):
        """
        Cancels the alert when the button is pressed during ALERT_PENDING,
        sends a cancellation message to the server, and resets the system.
        """
        with self.alert_lock:
            if self.alert_timer:
                self.alert_timer.cancel()
            if self.timeout_timer:
                self.timeout_timer.cancel()
            self.state = "CANCELLED"
        
        report = {
            "scooter_id": SCOOTER_ID,
            "alert_type": "cancel",
            "timestamp": datetime.datetime.now().isoformat(),
            "location": self.get_location(),
            "acceleration": self.get_current_acceleration()
        }
        message = json.dumps(report)
        self.mqtt_client.publish(TOPIC_ALERTS, message)
        print("Cancellation message sent to server:", message)
        os.system(f"play {CANCELLED_MP3_PATH}")
        self.reset_system()

    def timeout_alert(self):
        """If the alert remains active for one hour, reset the system state."""
        with self.alert_lock:
            if self.state == "ALERT_PENDING":
                print("Alert timed out after one hour. Resetting system.")
                self.state = "IDLE"
        self.sense.clear()

    def get_location(self):
        """Placeholder for GPS integration; returns a fixed location."""
        return {"lat": 63.4305, "lon": 10.3951}

    def get_current_acceleration(self):
        """Read accelerometer data and compute its magnitude."""
        accel = self.sense.get_accelerometer_raw()
        x = accel.get("x", 0)
        y = accel.get("y", 0)
        z = accel.get("z", 0)
        return math.sqrt(x*x + y*y + z*z)

    def monitor_sensors(self):
        """
        Continuously monitor the accelerometer.
        If the measured acceleration exceeds CRASH_THRESHOLD and the system is IDLE,
        trigger alert mode.
        """
        while True:
            if self.state == "IDLE":
                current_accel = self.get_current_acceleration()
                if current_accel > CRASH_THRESHOLD:
                    print(f"Crash detected! Acceleration: {current_accel:.2f}")
                    self.start_alert(alert_type="crash")
            time.sleep(0.1)

    def reset_system(self):
        """Reset the system state back to IDLE and cancel running timers."""
        with self.alert_lock:
            self.state = "IDLE"
            if self.alert_timer:
                self.alert_timer.cancel()
            if self.timeout_timer:
                self.timeout_timer.cancel()
        self.sense.clear()
        print("System reset to IDLE state.")

    def run(self):
        """Start sensor monitoring in a separate thread and keep the main thread alive."""
        sensor_thread = threading.Thread(target=self.monitor_sensors, daemon=True)
        sensor_thread.start()
        while True:
            time.sleep(1)

if __name__ == "__main__":
    system = EScooterSystem()
    system.run()