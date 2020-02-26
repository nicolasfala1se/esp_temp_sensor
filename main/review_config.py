from main.config_file import jsonfile
import user_config

DEFAULT_WAKEUP_PERIOD = "30"
DEFAULT_REFRESH_COUNTER = "10"
DEFAULT_DHT_PIN = "0"
DEFAULT_LED_PIN = "0"
DEFAULT_DHT_TYPE = "BME280"
DEFAULT_DEEPSLEEP_MODE = "DISABLE"
DEFAULT_LCD1602 = "0"
DEFAULT_NODE_NAME = "None"
DEFAULT_UTC_OFS = "0"
DEFAULT_UNIT = "C"  # unit = "C" or "F"

def review_u_config(u_config):
    ''' This function is called to review and fix the configuration '''

    try:
        _wakeup_period = int(u_config['WAKEUP_PERIOD'])
    except:
        u_config['WAKEUP_PERIOD']  = DEFAULT_WAKEUP_PERIOD

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

    try:
        _debug_mode = u_config['UTC_OFS']
    except:
        u_config['UTC_OFS'] = DEFAULT_UTC_OFS

    try:
        _debug_mode = u_config['UNIT']
    except:
        u_config['UNIT'] = DEFAULT_UNIT


def collect_u_config():
    config_jsonfile = jsonfile("/config.json", user_config.default_user_config)
    u_config = config_jsonfile.get_data()

    review_u_config(u_config)

    return u_config
