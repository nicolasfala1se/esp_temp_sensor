# MQTT temperature monitor.
from umqtt.robust import MQTTClient
#from main.ota_updater import OTAUpdater
from main.utils import wifi_connect, wifi_disconnect, led, GITHUB_HTTPS_ADDRESS
from main.bme280 import BME280
from main.rtos import rtos, rtos_task
from main.schedule_file import schedule_table
from main.oled_screen import oled_screen
from main.ntptime import settime

import machine, time, micropython, framebuf, utime, network
from ubinascii import hexlify
import ujson as json

micropython.alloc_emergency_exception_buf(100)

debug_mode_verwrite = 1

# Default MQTT server to connect to
CLIENT_ID = b"ESP_"+hexlify(machine.unique_id())
TOPIC_TEMPERATURE = "/temperature"
TOPIC_HUMIDITY = "/humidity"

I2C_SCL_PIN_NUMBER = 18
I2C_SDA_PIN_NUMBER = 5

DEFAULT_OLED_I2C_ADDR = 60  #0x3c
DEFAULT_BME280_I2C_ADDR  = 118 #0x76

def no_debug():
    import esp
    # this can be run from the REPL as well
    esp.osdebug(None)
        
class task1 (rtos_task):

    PRESENCE_TIMEOUT = 130000

    def task_init(self, param1):
        self.pin = machine.Pin(16, machine.Pin.OUT)
        self.pin.value(0)
        print("Init application task")

        self.wifi_valid, self.mqtt_valid = [False, False]

        # configure led pin
        self.l_pin = led(2)

        self.oledIsConnected, self.bmeIsConnected = [False, False]
        # init ic2 object
        i2c = machine.I2C(scl=machine.Pin(I2C_SCL_PIN_NUMBER), sda=machine.Pin(I2C_SDA_PIN_NUMBER),freq=400000)
        # Scan i2c bus and check if BME2 and OLDE display are connected
        #print('Scan i2c bus...')
        devices = i2c.scan()
        if len(devices) == 0:
            print("No i2c device !")
        else:
            #print('i2c devices found:',len(devices))
            for device in devices: 
                if device == DEFAULT_OLED_I2C_ADDR:
                    self.oledIsConnected = True
                if device == DEFAULT_BME280_I2C_ADDR:
                    self.bmeIsConnected = True  
                #print ('Adr: ',device)
        # BME280
        if self.bmeIsConnected:
            try:
                self.bme280 = BME280.BME280(i2c=i2c, mode=BME280.BME280_OSAMPLE_1, address=DEFAULT_BME280_I2C_ADDR)
            except:
                self.bmeIsConnected = False
                print("Error: No sensor")
            else:
                # discard first measure to switch sensor in FORCED MODE
                self.bme280.read_compensated_data()

        if debug_mode_verwrite != 0:
            self.debug_p = True
        else:
            self.debug_p = False if param1['DEBUG_MODE']=="0" else True 

        # program execution
        if self.debug_p: print("Node: ",param1['NODE_NAME'])
        
        if param1['WIFI_CONF']:
            # wifi connection
            wifi_connect(param1['WIFI_SSID'], param1['WIFI_PASS'],verbose=True)
            self.wifi_valid=True

            if param1['MQTT_CONF']:
                try:
                    # create MQTT connection
                    self.c = MQTTClient( CLIENT_ID, param1['MQTT_SERVER'] )
                    # mqtt connection
                    self.c.connect()
                except:
                    print ("unable to connect to server")
                    self.mqtt_valid = False
                else:
                    self.mqtt_valid = True
            
        # OLED screen
        if self.oledIsConnected:
            self.oled = oled_screen(i2c, DEFAULT_OLED_I2C_ADDR, unit=param1['UNIT'])
            self.oled.update_screen(self.wifi_valid,self.mqtt_valid, utime.localtime(), None, None )
        else:
            print('! No i2c display')

# Task body
#
    def task_body(self, param1):

        while True:
            self.pin.value(1)
            self.l_pin.set_on()
            if self.debug_p: print("New measure...")

            dht_measured=0 
            if self.bmeIsConnected: 
                try:
                    t, p, h = self.bme280.read_compensated_data()
                except Exception as other:
                    dht_measured=0
                    print ("Bme exception:", other)
                else:
                    dht_measured=1

            if dht_measured == 1:
                if param1['UNIT'] == 'F':
                    t = t/100*9.0/5.0+32
                else:
                    t = t/100

                temperature_str = "{:.02f}".format(t)
                humidity_str = "{:.02f}".format(h/1024)

                # verify wifi connection
                sta_if = network.WLAN(network.STA_IF)
                self.wifi_valid = sta_if.isconnected()

                if self.wifi_valid:
                    l_mqtt_valid = self.mqtt_valid
                    if l_mqtt_valid:
                        try:
                            # valid measure
                            self.c.publish( param1['NODE_NAME']+TOPIC_TEMPERATURE, temperature_str)
                            self.c.publish( param1['NODE_NAME']+TOPIC_HUMIDITY, humidity_str)
                        except:
                            print("Cannot publish measurements")
                            l_mqtt_valid = False
                else:
                    l_mqtt_valid = False        
            
                if self.debug_p: print("Temperature:", temperature_str)
                if self.debug_p: print("Humidity:", humidity_str)

                if self.oledIsConnected:
                    self.oled.update_screen(self.wifi_valid, l_mqtt_valid, utime.localtime(), t, h/1024, "Call Daddy...")
                
            self.l_pin.set_off()
            self.pin.value(0)

            yield None

class updater_task(rtos_task):
    """ implementation of the updater task """

    def task_init(self,param1):
        print("Init updater task")

    def task_body(self,param1):
        while True:
            print('Checking for update...')
            yield None

def load_application_screen():
    # load screen logo
    i2c = machine.I2C(scl=machine.Pin(I2C_SCL_PIN_NUMBER), sda=machine.Pin(I2C_SDA_PIN_NUMBER),freq=400000)
    devices = i2c.scan()
    if len(devices) != 0:
        if DEFAULT_OLED_I2C_ADDR in devices: 
            oled = oled_screen(i2c, DEFAULT_OLED_I2C_ADDR)
            oled.load_logo()

def application(u_config): 
    no_debug()

    # configure rtc with ntp time
    settime(int(u_config['UTC_OFS'])*60*60)

    # convert counters
    wakeup_period = int(u_config['WAKEUP_PERIOD'])*1000
    t1=task1(priority=2, param1=u_config)
    t2=updater_task(priority=1)
    task_list = [t1,t2]
    r = rtos(s_table=schedule_table, t_list=task_list )   # configure OS wih static configuration
    # timer 1 used to scheduled the first execution
    tim = machine.Timer(1)
    tim.init(period=2000, mode=machine.Timer.ONE_SHOT, callback=lambda t:r.scheduler_tick_call())
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
