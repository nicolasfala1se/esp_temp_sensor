import dht
from main.bme280 import BME280
import machine

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

class temp_sensor:
    def __init__ (self, sensor_type, pin):
        self.sensor_type = sensor_type
        if sensor_type == "DHT22":
            self.dht_comp = dht.DHT22(machine.Pin(pin))
        elif sensor_type == "DHT11":
            self.dht_comp = dht.DHT11(machine.Pin(pin))
        elif sensor_type == "BME280":
            self.dht_comp = DHT_BME280(pin)
        else:
            self.dht_comp = DUMMY_DHT(0)

    def measure(self):
        self.dht_comp.measure()
        
    def humidity(self):
        return self.dht_comp.humidity()

    def temperature(self):
        return self.dht_comp.temperature()
 
    def pressure(self):
        if self.sensor_type == "BME280":
            return self.dht_comp.pressure()
        else:
            return 1001

            
