import time
import datetime
import threading
import math
import json
from sense_hat import SenseHat, ACTION_PRESSED
import paho.mqtt.client as mqtt

# Constants provided in the specification
BROKER_ADDRESS = "mqtt20.iik.ntnu.no"
SCOOTER_ID = "scooter123"
CRASH_THRESHOLD = 2.5
TOPIC_ALERTS = f"scooter/{SCOOTER_ID}/alerts"

class EScooterSystem:
    def __init__(self):
        # Initialize Sense HAT interface and MQTT client
        self.sense = SenseHat()
        self.mqtt_client = mqtt.Client()
        self.state = "IDLE"  # possible states: IDLE, ALERT_PENDING, EMERGENCY_SENT
        self.alert_timer = None
        self.alert_lock = threading.Lock()
        self.alert_start_time = None

        # Connect to the MQTT broker
        try:
            self.mqtt_client.connect(BROKER_ADDRESS)
            self.mqtt_client.loop_start()
            print(f"Connected to MQTT Broker at {BROKER_ADDRESS}")
        except Exception as e:
            print("Error connecting to MQTT Broker:", e)
        
        # Set up the Sense HAT joystick to act as the panic/cancellation button.
        # The same button is used to start the alert (panic) or cancel a pending alert.
        self.sense.stick.direction_middle = self.panic_button_pressed

    def panic_button_pressed(self, event):
        # Only act on button press events.
        if event.action != ACTION_PRESSED:
            return

        with self.alert_lock:
            if self.state == "IDLE":
                print("Manual panic button pressed. Starting alert sequence.")
                self.start_alert(alert_type="panic")
            elif self.state == "ALERT_PENDING":
                print("Cancellation detected via panic button press.")
                self.cancel_alert()

    def start_alert(self, alert_type):
        """
        Transition the system into ALERT_PENDING state, start blinking the LED matrix,
        and set a 30-second timer to either cancel or send the emergency report.
        """
        self.state = "ALERT_PENDING"
        self.alert_start_time = datetime.datetime.now()
        # Start blinking red on a separate thread so as not to block sensor monitoring.
        threading.Thread(target=self.blink_red, daemon=True).start()
        
        # Start a timer that will trigger sending the emergency report after 30 seconds.
        self.alert_timer = threading.Timer(30, self.send_emergency_report, args=[alert_type])
        self.alert_timer.start()

    def blink_red(self):
        """
        Continuously blink the LED matrix red while in ALERT_PENDING state.
        This simulates the visual feedback (blinking red and noise) to alert the rider.
        """
        red = (255, 0, 0)
        off = (0, 0, 0)
        while self.state == "ALERT_PENDING":
            self.sense.clear(red)
            time.sleep(0.5)
            self.sense.clear(off)
            time.sleep(0.5)

    def cancel_alert(self):
        """
        Cancel the pending alert if the rider confirms it was accidental.
        """
        if self.alert_timer:
            self.alert_timer.cancel()
        self.state = "IDLE"
        self.sense.clear()
        print("Alert cancelled. System returning to IDLE state.")

    def send_emergency_report(self, alert_type):
        """
        Send an emergency report if the alert is not cancelled within the allowed 30 seconds.
        The report includes details such as scooter ID, alert type, timestamp, a simulated location,
        and the current acceleration measurement.
        """
        with self.alert_lock:
            if self.state != "ALERT_PENDING":
                return  # Alert was cancelled
            self.state = "EMERGENCY_SENT"

        report = {
            "scooter_id": SCOOTER_ID,
            "alert_type": alert_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "location": self.get_location(),
            "acceleration": self.get_current_acceleration()
        }
        message = json.dumps(report)
        self.mqtt_client.publish(TOPIC_ALERTS, message)
        print("Emergency report sent:", message)
        # After sending the report, wait a few seconds then reset the system.
        time.sleep(5)
        self.reset_system()

    def get_location(self):
        """
        Placeholder for a GPS integration.
        Returns a fixed location (e.g., Trondheim) for demonstration purposes.
        """
        return {"lat": 63.4305, "lon": 10.3951}

    def get_current_acceleration(self):
        """
        Read raw accelerometer data from the Sense HAT and compute the magnitude.
        """
        accel = self.sense.get_accelerometer_raw()
        x = accel.get("x", 0)
        y = accel.get("y", 0)
        z = accel.get("z", 0)
        magnitude = math.sqrt(x * x + y * y + z * z)
        return magnitude

    def monitor_sensors(self):
        """
        Continuously monitor the accelerometer for sudden changes.
        If the measured acceleration exceeds the CRASH_THRESHOLD, a crash is detected.
        """
        while True:
            if self.state == "IDLE":
                current_accel = self.get_current_acceleration()
                if current_accel > CRASH_THRESHOLD:
                    print(f"Crash detected! Acceleration: {current_accel:.2f}")
                    self.start_alert(alert_type="crash")
            time.sleep(0.1)

    def reset_system(self):
        """
        Resets the system state back to IDLE after an emergency report has been sent.
        """
        with self.alert_lock:
            self.state = "IDLE"
            self.sense.clear()
            print("System reset to IDLE state.")

    def run(self):
        """
        Start the sensor monitoring in a separate thread and keep the main thread alive.
        """
        sensor_thread = threading.Thread(target=self.monitor_sensors, daemon=True)
        sensor_thread.start()
        while True:
            time.sleep(1)

if __name__ == "__main__":
    system = EScooterSystem()
    system.run()