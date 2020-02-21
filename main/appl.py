# MQTT temperature monitor.
from main.umqtt.robust import MQTTClient
from main.ota_updater import OTAUpdater
from main.utils import wifi_connect, wifi_disconnect, led, GITHUB_HTTPS_ADDRESS
from main.bme280 import BME280
from main.sensors import temp_sensor
from main.rtos import rtos, rtos_task
from main.schedule_file import schedule_table
from main.i2c_lcd.esp8266_i2c_lcd import I2cLcd

import machine
from ubinascii import hexlify
import time
import ujson as json
import micropython
micropython.alloc_emergency_exception_buf(100)

debug_mode_verwrite = const(1)

# Default MQTT server to connect to
CLIENT_ID = b"ESP_"+hexlify(machine.unique_id())
TOPIC_TEMPERATURE = "/temperature"
TOPIC_HUMIDITY = "/humidity"

# The PCF8574 has a jumper selectable address: 0x20 - 0x27
DEFAULT_I2C_ADDR = 0x3F

def no_debug():
    import esp
    # this can be run from the REPL as well
    esp.osdebug(None)
        
class task1 (rtos_task):

    PRESENCE_TIMEOUT = 130000
    def task_init(self, param1):
        print("Init application task")
        self.pin = machine.Pin(16, machine.Pin.OUT)
        self.pin.value(0)
        if param1['LCD1602'] == "1":
            i2c = machine.I2C(scl=machine.Pin(18), sda=machine.Pin(5), freq=400000)
            self.lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)
            self.lcd.putstr("Starting...\nTakes a minute")
            self.lcd.display_on()
            self.backlight_on=1
            self.lcd.backlight_on()        

            self.presence_pin = machine.Pin(39, machine.Pin.IN, pull=machine.Pin.PULL_UP)
            self.presence_timer = machine.Timer(-1)
            self.presence_timer.init(mode=machine.Timer.ONE_SHOT, period=self.PRESENCE_TIMEOUT, callback=lambda t:micropython.schedule(self.backlight_timeout, t))
            # self.presence_pin.irq(self.presence_irq, trigger=machine.Pin.IRQ_RISING)
            # self.presence_pin.irq(lambda p:micropython.schedule(self.backlight_restart, p), trigger=machine.Pin.IRQ_RISING)

        # BME280
        try:
            self.dht_comp = temp_sensor(param1['DHT_TYPE'], int(param1['DHT_PIN']), int(param1['BME_PIN']))
        except:
            self.dht_comp=None
            print("Error: No sensor")


        if debug_mode_verwrite != 0:
            self.debug_p = True
        else:
            self.debug_p = False if param1['DEBUG_MODE']=="0" else True 

        # program execution
        if self.debug_p: print("Node: ",param1['NODE_NAME'])
        
        # configure led pin
        self.l_pin = led(int(param1['LED_PIN']))

        if param1['WIFI_CONF']:
            # wifi connection
            wifi_connect(param1['WIFI_SSID'], param1['WIFI_PASS'],verbose=True)

        if param1['MQTT_CONF']:
            try:
                # create MQTT connection
                self.c = MQTTClient( CLIENT_ID, param1['MQTT_SERVER'] )
                # mqtt connection
                self.c.connect()
            except:
                print ("unable to connect to server")
                if param1['LCD1602'] == "1":
                    self.lcd.clear()
                    self.lcd.move_to(0, 0)
                    self.lcd.putstr("No connection w/ MQTT server")

    def task_body(self, param1):
        while True:
            self.pin.value(1)
            if self.debug_p: print("New measure...")

            self.l_pin.set_on()

            if self.dht_comp == None:
                try:
                    self.dht_comp = temp_sensor(param1['DHT_TYPE'], int(param1['DHT_PIN']), int(param1['BME_PIN']))
                except:
                    self.dht_comp=None
                    print("Error: No sensor")

            dht_measured=0 
            if not self.dht_comp == None:        
                try:
                    self.dht_comp.measure()
                except Exception as other:
                    dht_measured=0
                    print ("Dht exception:", other)
                else:
                    dht_measured=1

            if(dht_measured):
                temperature_str = "{:.02f}".format(self.dht_comp.temperature()*9.0/5.0+32)
                humidity_str = "{:.02f}".format(self.dht_comp.humidity())

                if param1['LCD1602'] == "1":
                    self.lcd.clear()
                    self.lcd.move_to(0, 0)
                    temperature_lcd = "{:.0f}".format(self.dht_comp.temperature()*9.0/5.0+32)
                    humidity_lcd = "{:.0f}".format(self.dht_comp.humidity())
                    self.lcd.putstr("Temperature: %sFHumidity   : %s%%" % (temperature_lcd,humidity_lcd))

                if param1['MQTT_CONF']:
                    try:
                        # valid measure
                        self.c.publish( param1['NODE_NAME']+TOPIC_TEMPERATURE, temperature_str)
                        self.c.publish( param1['NODE_NAME']+TOPIC_HUMIDITY, humidity_str)
                    except:
                        print("Cannot publish measurements")
                    
                if self.debug_p: print("Temperature:", temperature_str)
                if self.debug_p: print("Humidity:", humidity_str)
                
            self.l_pin.set_off()
            self.pin.value(0)

            yield None

    def presence_irq(self,pin):
        #print (self.presence_pin.value())
        micropython.schedule(self.backlight_restart, pin)

    def backlight_restart(self, unused):
        print (self.presence_pin.value())
        if self.backlight_on == 0:
            self.backlight_on = 1
            self.lcd.backlight_on() 
        else:
            # delete before restarting the timer
            self.presence_timer.deinit()
        # start the timer
        self.presence_timer.init(mode=machine.Timer.ONE_SHOT, period=self.PRESENCE_TIMEOUT, callback=lambda t:micropython.schedule(self.backlight_timeout, t))

    def backlight_timeout(self, unused):
        self.backlight_on = 0
        self.lcd.backlight_off()
       

class updater_task(rtos_task):
    """ implementation of the updater task """

    def task_init(self,param1):
        print("Init updater task")

    def task_body(self,param1):
        while True:
            print('Checking for update...')
            yield None

def application(u_config): 
    no_debug()

    # convert counters
    wakeup_period = int(u_config['WAKEUP_PERIOD'])*1000

    t1=task1(priority=2, param1=u_config)
    t2=updater_task(priority=1)

    task_list = [t1,t2]
    r = rtos(s_table=schedule_table, t_list=task_list )   # configure OS wih static configuration
    # timer 0 used for rtos schedule
    tim = machine.Timer(0)
    tim.init(period=wakeup_period, mode=machine.Timer.PERIODIC, callback=lambda t:r.scheduler_tick_call())

    #print(r.task_list)
    try:
        r.start()       # start OS
    finally:
        tim.deinit()    # stop the timer
        r.stop()        # stop OS
    print("Close all")
