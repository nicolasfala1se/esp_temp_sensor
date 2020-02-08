import network
import time
import machine
import main.config_file
import user_config

DEFAULT_WAKEUP_PERIOD = "30"
DEFAULT_REFRESH_COUNTER = "10"
DEFAULT_DHT_PIN = "0"
DEFAULT_LED_PIN = "0"
DEFAULT_DHT_TYPE = "DHT22"
DEFAULT_DEEPSLEEP_MODE = "DISABLE"

def wifi_connect( wifi_ssid, wifi_password, verbose=False):
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        if verbose:
            print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(wifi_ssid, wifi_password)
        while not sta_if.isconnected():
            time.sleep_ms(200)
        if verbose:
            print('network config:', sta_if.ifconfig())
    else:
        if verbose:
            print("Already connected to network")

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

def review_u_config(u_config):

    try:
        led_pin = int(u_config['LED_PIN'])
    except:
        u_config['LED_PIN'] = DEFAULT_LED_PIN

    try:
        dht_pin = int(u_config['DHT_PIN'])
    except:
        u_config['DHT_PIN'] = DEFAULT_DHT_PIN

    try:
        dht_type = u_config['DHT_TYPE']
    except:
        u_config['DHT_TYPE'] = DEFAULT_DHT_TYPE

    try:
        refresh_counter = int(u_config['REFRESH_COUNTER'])
    except:
        u_config['REFRESH_COUNTER']  = DEFAULT_REFRESH_COUNTER

    try:
        wakeup_period = int(u_config['WAKEUP_PERIOD'])
    except:
        u_config['WAKEUP_PERIOD']  = DEFAULT_WAKEUP_PERIOD
        
    try:
        deepsleep_mode = u_config['DEEPSLEEP_MODE']
    except:
        u_config['DEEPSLEEP_MODE'] = DEFAULT_DEEPSLEEP_MODE

    try:
        node_name = u_config['NODE_NAME']
    except:
        u_config['NODE_NAME'] = DEFAULT_NODE_NAME

    try:
        wifi_ssid = u_config['WIFI_SSID']
        wifi_pass = u_config['WIFI_PASS']        
    except:
        print("No valid WIFI configuration")
        u_config['WIFI_CONF'] = False
    else:
        u_config['WIFI_CONF'] = True 

    try:
        mqtt_server = u_config['MQTT_SERVER']
    except:
        print("No valid MQTT server")
        u_config['MQTT_CONF'] = False
    else:
        u_config['MQTT_CONF'] = True


def collect_u_config():
    config_jsonfile = main.config_file.jsonfile("/h_config.json", user_config.default_hardware_config)
    u_config = config_jsonfile.get_data()

    config_jsonfile = main.config_file.jsonfile("/config.json", user_config.default_user_config)
    u_config.update( config_jsonfile.get_data() )

    review_u_config(u_config)

    return u_config
