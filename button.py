from gpiozero import Button
from signal import pause

button = Button(2)  # GPIO pin 2

def on_press():
    print("Button pressed!") #need to add the blinking and noise functionality

button.when_pressed = on_press 


pause()



