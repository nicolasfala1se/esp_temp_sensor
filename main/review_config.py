from main.config_file import jsonfile
import user_config

DEFAULT_WAKEUP_PERIOD = "30"
DEFAULT_REFRESH_COUNTER = "10"
DEFAULT_DHT_PIN = "0"
DEFAULT_LED_PIN = "0"
DEFAULT_DHT_TYPE = "DHT22"
DEFAULT_DEEPSLEEP_MODE = "DISABLE"

def review_u_config(u_config):
    ''' This function is called to review and fix the configuration '''

    try:
        _led_pin = int(u_config['LED_PIN'])
    except:
        u_config['LED_PIN'] = DEFAULT_LED_PIN

    try:
        _dht_pin = int(u_config['DHT_PIN'])
    except:
        u_config['DHT_PIN'] = DEFAULT_DHT_PIN

    try:
        _bme_pin = int(u_config['BME_PIN'])
    except:
        u_config['BME_PIN'] = DEFAULT_DHT_PIN

    try:
        _dht_type = u_config['DHT_TYPE']
    except:
        u_config['DHT_TYPE'] = DEFAULT_DHT_TYPE

    if u_config['DHT_PIN'] == DEFAULT_DHT_PIN:
        u_config['DHT_TYPE'] = "DUMMY_DHT"
   
    try:
        _refresh_counter = int(u_config['REFRESH_COUNTER'])
    except:
        u_config['REFRESH_COUNTER']  = DEFAULT_REFRESH_COUNTER

    try:
        _wakeup_period = int(u_config['WAKEUP_PERIOD'])
    except:
        u_config['WAKEUP_PERIOD']  = DEFAULT_WAKEUP_PERIOD
        
    try:
        _deepsleep_mode = u_config['DEEPSLEEP_MODE']
    except:
        u_config['DEEPSLEEP_MODE'] = DEFAULT_DEEPSLEEP_MODE

    try:
        _node_name = u_config['NODE_NAME']
    except:
        u_config['NODE_NAME'] = DEFAULT_NODE_NAME

    try:
        _wifi_ssid = u_config['WIFI_SSID']
        _wifi_pass = u_config['WIFI_PASS']        
    except:
        print("No valid WIFI configuration")
        u_config['WIFI_CONF'] = False
    else:
        u_config['WIFI_CONF'] = True 

    try:
        _mqtt_server = u_config['MQTT_SERVER']
    except:
        print("No valid MQTT server")
        u_config['MQTT_CONF'] = False
    else:
        u_config['MQTT_CONF'] = True

    try:
        _debug_mode = u_config['DEBUG_MODE']
    except:
        u_config['DEBUG_MODE'] = False

def collect_u_config():
    config_jsonfile = jsonfile("/h_config.json", user_config.default_hardware_config)
    u_config = config_jsonfile.get_data()

    config_jsonfile = jsonfile("/config.json", user_config.default_user_config)
    u_config.update( config_jsonfile.get_data() )

    review_u_config(u_config)

    return u_config
