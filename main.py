# main.py file
import gc
from main.ota_updater import OTAUpdater
from main.appl import application
from main.utils import wifi_connect
from main.review_config import collect_u_config


def download_and_install_update_if_available():
    o = OTAUpdater('https://github.com/nicolasfala1se/esp_temp_sensor')
    o.download_and_install_update_if_available()

def boot():
    u_config = collect_u_config()
    # if wifi config seems ok
    if u_config['WIFI_CONF']:
        # wifi connection
        wifi_connect(u_config['WIFI_SSID'], u_config['WIFI_PASS'])
        download_and_install_update_if_available()
    
    gc.collect()
    # execute application
    application(u_config)

if __name__ == "__main__":
    boot()
