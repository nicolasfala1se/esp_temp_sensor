# MQTT temperature monitor.
from main.umqtt.robust import MQTTClient
from main.ota_updater import OTAUpdater
from main.utils import wifi_connect, wifi_disconnect, led, GITHUB_HTTPS_ADDRESS
from main.bme280 import BME280
from main.sensors import temp_sensor

import machine
import gc
from ubinascii import hexlify
import time
import ujson as json

debug_mode_verwrite = const(1)

# Default MQTT server to connect to
CLIENT_ID = b"ESP_"+hexlify(machine.unique_id())
TOPIC_TEMPERATURE = "/temperature"
TOPIC_HUMIDITY = "/humidity"

MAINSTATE_INIT = {"ST_CNT":"1"}

OTA_CHECK_PERIOD = const(300*1000)  # check every 5 minutes

def no_debug():
    import esp
    # this can be run from the REPL as well
    esp.osdebug(None)

def ota_check_for_new_version ( reboot_flag=False ):
    o=OTAUpdater(GITHUB_HTTPS_ADDRESS)
    new_version = o.check_for_update_to_install_during_next_reboot()
    if new_version and reboot_flag:
        print('rebooting...')
        machine.reset() 

def application(u_config): 
    no_debug()

    gc.collect()

    # convert counters
    wakeup_period = int(u_config['WAKEUP_PERIOD'])*1000
    refresh_counter = int(u_config['REFRESH_COUNTER'])
     # next period to check for new software
    ota_next_check = 0
   
    # BME280
    dht_comp = temp_sensor(u_config['DHT_TYPE'], int(u_config['DHT_PIN']), int(u_config['BME_PIN']))   

    if debug_mode_verwrite != 0:
        debug_p = True
    else:
        debug_p = False if u_config['DEBUG_MODE']=="0" else True 

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
    if debug_p: print("Node: ",u_config['NODE_NAME'])
    
    # configure led pin
    l_pin = led(int(u_config['LED_PIN']))

    if u_config['WIFI_CONF']:
        # wifi connection
        wifi_connect(u_config['WIFI_SSID'], u_config['WIFI_PASS'])

    if u_config['MQTT_CONF']:
        try:
            # create MQTT connection
            c = MQTTClient( CLIENT_ID, u_config['MQTT_SERVER'] )
            # mqtt connection
            c.connect()
        except:
            print ("unable to connect to server")

    # wait 2 second before reading sensor 
    wait_time = 2000
    current_time = time.ticks_ms()
    if wait_time>current_time:
        # compute time difference
        delta = time.ticks_diff(wait_time, current_time)
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

            try:
                dht_comp.measure()
            except Exception as other:
                dht_measured=0
                print ("Dht exception:", other)
            else:
                dht_measured=1

            if(dht_measured):
                temperature_str = "{:.02f}".format(dht_comp.temperature()*9.0/5.0+32)
                humidity_str = "{:.02f}".format(dht_comp.humidity())

                if u_config['MQTT_CONF']:
                    try:
                        # valid measure
                        c.publish( u_config['NODE_NAME']+TOPIC_TEMPERATURE, temperature_str)
                        c.publish( u_config['NODE_NAME']+TOPIC_HUMIDITY, humidity_str)
                    except:
                        print("Cannot publish measurements")

                    if u_config['DEEPSLEEP_MODE'] == 'ENABLE':
                        c.disconnect()
                
                if u_config['WIFI_CONF'] and (u_config['DEEPSLEEP_MODE'] == 'ENABLE'):
                    wifi_disconnect()
                    
                if debug_p: print("Temperature:", temperature_str)
                if debug_p: print("Humidity:", humidity_str)

                #reset state
                main_state['ST_CNT']="1"
                
            l_pin.set_off()

        else:
            # increment counter
            main_state['ST_CNT']=str(int(main_state['ST_CNT'])+1)

        if u_config['DEEPSLEEP_MODE'] == 'ENABLE':
            
            # save main_state in rtc memory
            rtc.memory(json.dumps(main_state))
            
            if debug_p: print("Entering sleep mode...")
            
            # configure RTC.ALARM0 to be able to wake the device
            rtc = machine.RTC()
            rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)

            # set RTC.ALARM0 to fire after wakeup_period seconds (waking the device)
            current_time = time.ticks_ms()-1850
            rtc.alarm(rtc.ALARM0, wakeup_period-current_time)

            # put the device to sleep
            machine.deepsleep()
        else:
            if debug_p: print("Entering sleep time ...")

            # check new version every few minutes
            if time.ticks_ms() > ota_next_check:
                gc.collect()
                ota_next_check = time.ticks_add(time.ticks_ms(), OTA_CHECK_PERIOD)
                # check new version
                ota_check_for_new_version (True)

            # compute next time to run
            time_to_reach = time.ticks_add(wakeup_period, start_loop)

            gc.collect()

            # while we don't reach that time
            time_left = time.ticks_diff(time_to_reach,time.ticks_ms())
            time.sleep_ms(time_left)

