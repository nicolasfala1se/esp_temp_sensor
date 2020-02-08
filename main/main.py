# MQTT temperature monitor.

import machine
import ubinascii
import time
import dht
from umqtt.robust import MQTTClient
import network
import config_file
import user_config
import ujson as json
from bme280 import BME280

sw_version = "1"

debug_mode_verwrite = "0"

# Default MQTT server to connect to
CLIENT_ID = b"ESP_"+ubinascii.hexlify(machine.unique_id())
TOPIC_TEMPERATURE = "/temperature"
TOPIC_HUMIDITY = "/humidity"

MAINSTATE_INIT = {"ST_CNT":"1"}

DEFAULT_WAKEUP_PERIOD = 30
DEFAULT_REFRESH_COUNTER = 10
DEFAULT_DHT_PIN = 0
DEFAULT_LED_PIN = 0
DEFAULT_DHT_TYPE = "DHT22"
DEFAULT_DEEPSLEEP_MODE = "DISABLE"

debug_mode = "0" 

def no_debug():
    import esp
    # this can be run from the REPL as well
    esp.osdebug(None)

def wifi_connect( wifi_ssid, wifi_password):
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        if debug_mode != "0":
            print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(wifi_ssid, wifi_password)
        while not sta_if.isconnected():
            time.sleep_ms(200)
        if debug_mode != "0":
            print('network config:', sta_if.ifconfig())
        
def wifi_disconnect ():
    sta_if = network.WLAN(network.STA_IF)
    if sta_if.isconnected():
        sta_if.disconnect()
    sta_if.active(False)
    
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
       
class DUMMY_DHT:
    def __init__ (self, pin):
        self.temperature_value = 70
        self.humidity_value = 30
        self.rand_num = self.get_rand(0)

    def get_rand ( self, x ):
        incr = 1
        while True:
            if(x>=10):
                incr = -1
            elif (x<=0):
                incr = 1
            x += incr
            yield x
            
    def measure(self):
        v = next(self.rand_num)
        self.temperature_value = 20 + v
        self.humidity_value = 30 + v
        time.sleep_ms(120)
        
    def humidity(self):
        return self.humidity_value

    def temperature(self):
        return self.temperature_value
    
class DHT_BME280:
    def __init__ (self, pin):
        self.pin = pin
        i2c = machine.I2C(scl=machine.Pin(self.pin+1), sda=machine.Pin(self.pin), freq=500000)
        self.bme280 = BME280.BME280(i2c=i2c)
  
    def measure(self):
        self.temperature_value, self.pressure_value, self.humidity_value = self.bme280.read_compensated_data()
        
    def humidity(self):
        return self.humidity_value/1024

    def temperature(self):
        return self.temperature_value/100
 
    def pressure(self):
        return self.pressure_value/256/100
 
def main(): 
    no_debug()

    config_jsonfile = config_file.jsonfile("/config.json", user_config.default_user_config)
    u_config = config_jsonfile.get_data()

    # blue LED pin
    try:
        led_pin = int(u_config['LED_PIN'])
    except:
        led_pin = DEFAULT_LED_PIN

    try:
        dht_pin = int(u_config['DHT_PIN'])
    except:
        dht_pin = DEFAULT_DHT_PIN

    try:
        dht_type = u_config['DHT_TYPE']
    except:
        dht_type = DEFAULT_DHT_TYPE

    if dht_pin == int(DEFAULT_DHT_PIN):
        dht_comp = DUMMY_DHT(0)
    elif dht_type == "DHT22":
        dht_comp = dht.DHT22(machine.Pin(dht_pin))
    elif dht_type == "DHT11":
        dht_comp = dht.DHT11(machine.Pin(dht_pin))
    elif dht_type == "BME280":
        dht_comp = DHT_BME280(dht_pin)
    
    try:
        refresh_counter = int(u_config['REFRESH_COUNTER'])
    except:
        refresh_counter  = DEFAULT_REFRESH_COUNTER

    try:
        wakeup_period = int(u_config['WAKEUP_PERIOD'])
    except:
        wakeup_period  = DEFAULT_WAKEUP_PERIOD
        
    try:
        deepsleep_mode = u_config['DEEPSLEEP_MODE']
    except:
        deepsleep_mode = DEFAULT_DEEPSLEEP_MODE
    
    if debug_mode_verwrite != "0":
        debug_mode = debug_mode_verwrite
    else:
        try:
            debug_mode = u_config['DEBUG_MODE']
        except:
            debug_mode = "0"
        
    debug_p = False if debug_mode == "0" else True

    try:
        wifi_ssid = u_config['WIFI_SSID']
        wifi_pass = u_config['WIFI_PASSWORD']
        mqtt_server = u_config['MQTT_SERVER']
        node_name = u_config['NODE_NAME']
    except:
        print("No valid WIFI configuration")
    else:
    
        main_state = {}
        rtc = machine.RTC()
        
        # check if the device woke from a deep sleep
        if machine.reset_cause() == machine.DEEPSLEEP_RESET:
            if debug_p: print('woke from a deep sleep')
            #retrieve main_state from rtc memory
            try:
                main_state = json.loads(rtc.memory())
            except:
                main_state = MAINSTATE_INIT
        else:
            main_state = MAINSTATE_INIT

        # program execution
        if debug_p: print("Node: ",node_name)
        
        l_pin = led(led_pin)

        if deepsleep_mode == 'DISABLE':
            # wifi connection
            wifi_connect(wifi_ssid, wifi_pass)
            # create MQTT connection
            c = MQTTClient( CLIENT_ID, mqtt_server )
            # mqtt connection
            c.connect()

        # wait 2 second before reading sensor 
        wait_time = 2000
        current_time = time.ticks_ms()
        if wait_time>current_time:
            delta = time.ticks_diff(wait_time, current_time) # compute time difference
            # wait before reading sensor
            time.sleep_ms(delta)
        
        # execution loop
        while True:
            # get millisecond counter
            start_loop = time.ticks_ms()
            # if debug_p: print("Start_loop (ms): ",start_loop)

            if debug_p: print("main state :", main_state['ST_CNT'])

            if int(main_state['ST_CNT']) == refresh_counter:
                l_pin.set_on()
    
                dht_measured=1
                try:
                    dht_comp.measure()
                except Exception as other:
                    dht_measured=0
                    print ("Dht exception:", other)
                
                if(dht_measured):
                    temperature_str = "{:.02f}".format(dht_comp.temperature()*9.0/5.0+32)
                    humidity_str = "{:.02f}".format(dht_comp.humidity())

                    try:
                        if deepsleep_mode == 'ENABLE':
                            # wifi reconnection
                            wifi_connect(wifi_ssid, wifi_pass)
                            # create MQTT connection
                            c = MQTTClient( CLIENT_ID, mqtt_server )
                            # mqtt reconnection
                            c.connect()

                        # valid measure
                        c.publish( node_name+TOPIC_TEMPERATURE, temperature_str)
                        c.publish( node_name+TOPIC_HUMIDITY, humidity_str)

                        if deepsleep_mode == 'ENABLE':
                            c.disconnect()
                            wifi_disconnect()
                    except:
                        print ("Connection error")
                        
                    if debug_p: print("Temperature:", temperature_str)
                    if debug_p: print("Humidity:", humidity_str)

                    #reset state
                    main_state['ST_CNT']="1"
                    
                l_pin.set_off()

            else:
                # increment counter
                main_state['ST_CNT']=str(int(main_state['ST_CNT'])+1)
 
            if deepsleep_mode == 'ENABLE':
                
                # save main_state in rtc memory
                rtc.memory(json.dumps(main_state))
               
                if debug_p: print("Entering sleep mode...")
                
                # configure RTC.ALARM0 to be able to wake the device
                rtc = machine.RTC()
                rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)

                # set RTC.ALARM0 to fire after wakeup_period seconds (waking the device)
                current_time = time.ticks_ms()-1850
                rtc.alarm(rtc.ALARM0, wakeup_period*1000-current_time)

                # put the device to sleep
                machine.deepsleep()
            else:
                if debug_p: print("Entering sleep time ...")

                # compute next time to run
                time_to_reach = time.ticks_add(wakeup_period*1000, start_loop)
                # while we don't reach that time
                current_time = time.ticks_ms()
                while current_time < time_to_reach:
                    current_time = time.ticks_ms()


if __name__ == "__main__":
    try:
        main()
    except:
        pass

