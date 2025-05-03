import json
from stmpy import Machine, Driver
import paho.mqtt.client as mqtt

BROKER_ADDRESS = "mqtt20.iik.ntnu.no"
SERVER_ID = {"server_id": "server123"}
TOPIC_ALERTS = f"scooter/+/alerts"
SCOOTER_ALERT = f"scooter/scooter123/alerts"

class Server:
    
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        try:
            self.client.connect(BROKER_ADDRESS)
            self.client.subscribe(TOPIC_ALERTS)
            self.client.loop_start()
            print(f"Connected to MQTT Broker at {BROKER_ADDRESS}")
        except Exception as e:
            print("Error connecting to MQTT Broker:", e)
        
    def on_connect(self, client, userdata, flags, rc):
       print("on_connect(): {}".format(mqtt.connack_string(rc)))
    
    def on_message(self, client, userdata, msg):
        message = msg.payload.decode('utf-8')
        message = json.loads(message)
        if message.get("alert_type") == "Emergency":
            print("on_message(): topic: {}".format(msg.topic))
            self.stm.send('receive_emergency_message_from_scooter')
        elif 'cancel_emergency' in message:
            print("Emergency cancellation received.")
            self.stm.send('receive_cancellation_of_emergency')
    
    def wait_for_scooter_message(self):
        print("Waiting for message")
        
    def start_server_timer(self):
        print("Starting timer")
        self.stm.start_timer('timer', 30000)
        
    def stop_server_timer(self):
        print("Stopping timer")
        self.stm.stop_timer('timer')
        
    def send_confirmation_to_scooter(self):
        print("Sending confirmation to scooter")
        msg = json.dumps(SERVER_ID)
        self.client.publish(SCOOTER_ALERT, msg)
        
    def notify_emergency_services(self):
        print("Notifying emergency services")
        
    def log_crash(self):
        print("Logging crash")
        self.stm.send('emergency_handled')
        
server = Server()

#transition from init to listening
init = {
    'source': 'initial', 
    'target': 'listening', 
    'effect': 'wait_for_scooter_message'
}

#transition from listening to pending
scooter_message = {
    'trigger': 'receive_emergency_message_from_scooter',
    'source': 'listening',
    'target': 'pending',
    'effect': 'start_server_timer'
}

#transition from pending to listening
fake_emergency = {
    'trigger': 'receive_cancellation_of_emergency',
    'source': 'pending',
    'target': 'listening',
    'effect': 'stop_server_timer ; wait_for_scooter_message'
}

#transition from pending to real_emergency
real_event = {
    'trigger': 'timer',
    'source': 'pending',
    'target': 'real_emergency',
    'effect': 'send_confirmation_to_scooter ; notify_emergency_services ; log_crash'
}

#transition from real_emergency to listening
back_to_listening = {
    'trigger': 'emergency_handled',
    'source': 'real_emergency',
    'target': 'listening',
    'effect': 'wait_for_scooter_message'
}

stm = Machine(name='server', transitions=[init, scooter_message, fake_emergency, real_event, back_to_listening], obj=server)
server.stm = stm

driver = Driver()
driver.add_machine(stm)
driver.start()
