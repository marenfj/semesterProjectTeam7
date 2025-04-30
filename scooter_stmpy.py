from stmpy import Machine, Driver
import math
import time
import datetime
from threading import Thread
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
CANCELLED_MP3_PATH = "cancelled.mp3" # Path to the cancelled sound


class Scooter:
    def __init__(self):
        self.emergency = False
        # Initialize Sense HAT and clear LEDs at startup
        self.sense = SenseHat()
        self.sense.clear()
        print("Initial state!")
        self.id="scooter123"
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message

        # Connect to MQTT broker
        try:
            self.mqtt_client.connect(BROKER_ADDRESS)
            self.mqtt_client.subscribe(TOPIC_ALERTS) 
            
            try:
                thread = Thread(target=self.mqtt_client.loop_forever)
                thread.start()
            except KeyboardInterrupt:
                self.mqtt_client.disconnect()
            
            print(f"Connected to MQTT Broker at {BROKER_ADDRESS}")
        except Exception as e:
            print("Error connecting to MQTT Broker:", e)
            
        
        # Set up the joystick (middle button)
        # In IDLE, a press triggers alert mode.
        # In ALERT_PENDING, a press cancels the alert.
        self.sense.stick.direction_middle = self.panic_button_pressed
        
    def on_message(self, client, userdata, msg):
        message = msg.payload.decode('utf-8')
        print(message)
        if 'server123' in message:
            print("server123 received")
            self.stm.send("timeout_from_server")
            
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
    
    def start_alert(self):
        #while waiting for message from server or not receiving cancellation button:
        self.emergency = True
        print("start_alert")
        print("Playing alarm sound (panic) and blinking red")
        red = (255, 0, 0)
        self.sense.clear(red)
        os.system(f"play {PANIC_MP3_PATH}")
    
    def send_to_server(self):
        try:
            print("Sending to server.")
            
            report = {
            "scooter_id": SCOOTER_ID,
            "alert_type": "Emergency",
            "timestamp": datetime.datetime.now().isoformat(),
            "location": self.get_location(),
            "acceleration": self.get_current_acceleration()
            }
            message = json.dumps(report)
            #message = SCOOTER_ID
            self.mqtt_client.publish(TOPIC_ALERTS, message)
            
        except Exception as e:
            print("Error sending emergency alert to server: ", e)
    
    #e-scooteren er ledig, og lyser grønt
    def idle(self):
        green = (0, 255, 0)
        self.sense.clear(green)
        input("Press any button to connect : ")
        self.stm.send('user_connected')
        
    #stopper bare blinkingen
    def stop_alert(self):
        self.emergency = False
        off = (0, 0, 0)
        self.sense.clear(off)
        print("stop_alert")
        
    def emergency_contacted(self):
        print("Playing notified sound")
        os.system(f"play {NOTIFIED_MP3_PATH}")

    #nullstiller både lys og lyd
    def reset(self):
        off = (0, 0, 0)
        self.sense.clear(off)
        try:
            os.system("killall play")
        except Exception as e:
            print("Error stopping sound:", e)
        print("Reset")

    def sensor_listening(self):
        print("sensor_listening")
        def monitoring():
            while True:
                current_accel = self.get_current_acceleration()
                if current_accel > CRASH_THRESHOLD:
                    print(f"Crash detected! Acceleration: {current_accel:.2f}")
                    self.stm.send('sensor_spike')
                    break
                time.sleep(0.1)
        threading.Thread(target=monitoring).start()
        
    def panic_button_pressed(self, event):
        if event.action != ACTION_PRESSED:
            return
        if event.action == ACTION_PRESSED and self.emergency == False:
            print("Panic button pressed: starting alert mode.")
            self.emergency = True
            self.stm.send('button_pressed')
            return
        if event.action == ACTION_PRESSED and self.emergency == True:
            print("Panic button pressed during alert: cancelling alert and sending cancellation message.")
            message = json.dumps({"cancel_emergency": "cancel_emergency"})
            self.mqtt_client.publish(TOPIC_ALERTS,message)
            self.emergency = False
            self.stm.send('button_pressed')
            return
            
        
        
#test
scooter = Scooter()


#transition init --> sleep
init = {
    "source": "initial",
    "target": "sleep",
    "effect": "idle",
}

#transition sleep --> listening
startListening = {
    "trigger": "user_connected",
    "source": "sleep",
    "target": "listening",
    "effect": "reset; sensor_listening"
}

#transition listening --> emergencyTriggered 
emergencySensor = {
    "trigger": "sensor_spike",
    "source": "listening",
    "target": "emergencyTriggered",
    "effect": "send_to_server; start_alert",
}

#transition listening --> emergencyTriggered 
emergencyButton = {
    "trigger": "button_pressed",
    "source": "listening",
    "target": "emergencyTriggered",
    "effect": "send_to_server; start_alert",
}

#transition listening --> sleep
backToSleep = {
    "trigger": "user_disconnected",
    "source": "listening",
    "target": "sleep",
    "effect": "idle",
}

#transition emergencyTriggered --> listening 
listeningTimeout = {
    "trigger": "timeout_from_server",
    "source": "emergencyTriggered",
    "target": "listening",
    "effect": "stop_alert; emergency_contacted; sensor_listening; reset",
}

#transition emergencyTriggered --> listening 
listeningButton = {
    "trigger": "button_pressed",
    "source": "emergencyTriggered",
    "target": "listening",
    "effect": "stop_alert; send_to_server; sensor_listening; reset",
}


#(test) STMpy
machine = Machine(transitions=[init, startListening, emergencySensor, emergencyButton, backToSleep, listeningTimeout, listeningButton], obj=scooter, name='scooter')
scooter.stm = machine
driver = Driver()
driver.add_machine(machine)
driver.start()