from sense_hat import SenseHat


sense = SenseHat()

while True:
    events = sense.stick.get_events()
    if events:
        print("Button pressed")
        sense.showmessage("Button pressed", text_colour=[255, 0, 0])




