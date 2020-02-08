# application

import machine
import ubinascii
import time
import network
import config_file
import user_config

class led:
    ''' This class is used to abstract the led '''
    
    def __init__(self, pin_number):
        if pin_number==0:
            self.pin = None
        else:
            self.pin = machine.Pin(pin_number, machine.Pin.OUT)
        
    def set_on(self):
        if self.pin is not None:
            self.pin.value(1)
        
    def set_off(self):
        if self.pin is not None:
            self.pin.value(0)
 
def application(): 

    print ("application start")   

    l_pin = led(0)

        # execution loop
        while True:
            l_pin.set_on()
            time.sleep_ms(1000)
            l_pin.set_off()
            time.sleep_ms(1000)
            print(".")
 

if __name__ == "__main__":
    try:
        application()
    except:
        pass

