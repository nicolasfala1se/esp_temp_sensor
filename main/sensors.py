from machine import I2C
from machine import Pin
from main.bme280 import BME280

class DUMMY_DHT:
    def __init__ (self, pin):
        self.temperature_value = 0
        self.humidity_value = 0
            
    def measure(self):
        pass
        
    def humidity(self):
        return self.humidity_value

    def temperature(self):
        return self.temperature_value
    
class DHT_BME280:
    def __init__ (self, pin):
        i2c = I2C(scl=Pin(pin+1), sda=Pin(pin), freq=500000)
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
            from dht import DHT22
            self.dht_comp = DHT22(Pin(pin))
        elif sensor_type == "DHT11":
            from dht import DHT11
            self.dht_comp = DHT11(Pin(pin))
        elif sensor_type == "BME280":
            from main.bme280 import BME280
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

            
