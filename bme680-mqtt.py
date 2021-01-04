#!/usr/bin/env python
# -*- coding: utf-8 -*-

# see https://github.com/robmarkcole/bme680-mqtt
# requirements: pip install bme680 smbus paho-mqtt
# reworked to allow hass MQTT discovery

import bme680
import time
import json
import socket

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish


print("""Estimate indoor air quality
Runs the sensor for a burn-in period, then uses a 
combination of relative humidity and gas resistance
to estimate indoor air quality as a percentage.
Press Ctrl+C to exit
""")

### MQTT
# set broker to either local or remote broker
# since hassio integrated mosquitto usually require a password, set it as well
broker = '192.0.2.1'
sensor_name="bme680_01"
mqtt_username="hass_mqtt_user"
mqtt_password="hass_mqtt_pass"

config_prefix ="homeassistant/sensor/"+sensor_name

#set MQTT LWT
def on_connect(client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        client.publish(sensor_name+"/tele/LWT","Online",qos=0,retain=True)

#get local_IP
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

client = mqtt.Client(sensor_name)
client.username_pw_set(username=mqtt_username,password=mqtt_password)
client.on_connect = on_connect
client.will_set(sensor_name+"/tele/LWT","Offline",qos=0,retain=True)
client.connect(broker)
client.loop_start()

### bme680

sensor = bme680.BME680()

# These oversampling settings can be tweaked to 
# change the balance between accuracy and noise in
# the data.
# BME680 temperature is often higher than normal. Offset it accordingly

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

sensor.set_temp_offset(-6)


# start_time and curr_time ensure that the 
# burn_in_time (in seconds) is kept track of.

start_time = time.time()
curr_time = time.time()
burn_in_time = 1  # burn_in_time (in seconds) is kept track of.

burn_in_data = []

try:
    # Collect gas resistance burn-in values, then use the average
    # of the last 50 values to set the upper limit for calculating
    # gas_baseline.
##    print("Collecting gas resistance burn-in data for 5 mins\n")
    while curr_time - start_time < burn_in_time:
        curr_time = time.time()
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            gas = sensor.data.gas_resistance
            burn_in_data.append(gas)
            time.sleep(1)

    gas_baseline = sum(burn_in_data[-50:]) / 50.0

    # Set the humidity baseline to 40%, an optimal indoor humidity.
    hum_baseline = 40.0

    # This sets the balance between humidity and gas reading in the 
    # calculation of air_quality_score (25:75, humidity:gas)
    hum_weighting = 0.25

    while True:
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            gas = sensor.data.gas_resistance
            gas_offset = gas_baseline - gas

            hum = sensor.data.humidity
            hum_offset = hum - hum_baseline

            # Calculate hum_score as the distance from the hum_baseline.
            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * (hum_weighting * 100)

            else:
                hum_score = (hum_baseline + hum_offset) / hum_baseline * (hum_weighting * 100)

            # Calculate gas_score as the distance from the gas_baseline.
            if gas_offset > 0:
                gas_score = (gas / gas_baseline) * (100 - (hum_weighting * 100))

            else:
                gas_score = 100 - (hum_weighting * 100)

            # Calculate air_quality_score. 
            air_quality_score = hum_score + gas_score

            humidity = str(round(hum, 2))
            temperature = str(round(sensor.data.temperature, 2))
            pressure = str(round(sensor.data.pressure, 2))
            air_qual = str(round(air_quality_score, 2))

            ##HASS autodiscovery
            device_class= { "name": sensor_name+" status", 
                            "stat_t": sensor_name+"/tele/HASS_STATE", 
                            "json_attr_t": sensor_name+"/tele/HASS_STATE",
                            "avty_t": sensor_name+"/tele/LWT",
                            "pl_avail": "Online",
                            "pl_not_avail": "Offline",
                            "unit_of_meas":"%",
                            "val_tpl": "{{value_json['RSSI']}}", 
                            "uniq_id": sensor_name+"_status", 
                            "dev": {"ids": [sensor_name], 
                                    "name": sensor_name, 
                                    "mdl": "bme680", 
                                    "sw": "bme680", 
                                    "mf": "Pimoroni" 
                            } 
                           }
            client.publish(config_prefix+'_status'+'/config', json.dumps(device_class))

            air_qual_class= { "name": sensor_name+" Air Quality", 
                              "stat_t": sensor_name+"/tele/SENSOR",
                              "uniq_id": sensor_name+"_air_qual",
                              "dev": {"ids": [sensor_name],
                              },
                              "unit_of_meas": "%", 
                              "dev_cla": "pressure",
                              "val_tpl": "{{ value_json.airqual}}" 
            }
            client.publish(config_prefix+'_air_qual'+'/config', json.dumps(air_qual_class))

            humidity_class= { "name": sensor_name+" humidity", 
                              "stat_t": sensor_name+"/tele/SENSOR",
                              "uniq_id": sensor_name+"_humidity",
                              "dev": {"ids": [sensor_name],
                              },
                              "unit_of_meas": "%", 
                              "dev_cla": "humidity",
                              "val_tpl": "{{ value_json.humidity}}" 
            }
            client.publish(config_prefix+'_humidity'+'/config', json.dumps(humidity_class))

            temperature_class= { "name": sensor_name+" temperature", 
                              "stat_t": sensor_name+"/tele/SENSOR",
                              "uniq_id": sensor_name+"_temperature",
                              "dev": {"ids": [sensor_name],
                              },
                              "unit_of_meas": "°C", 
                              "dev_cla": "temperature",
                              "val_tpl": "{{ value_json.temperature}}" 
            }
            client.publish(config_prefix+'_temperature'+'/config', json.dumps(temperature_class))

            pressure_class= { "name": sensor_name+" pressure", 
                              "stat_t": sensor_name+"/tele/SENSOR",
                              "uniq_id": sensor_name+"_pressure",
                              "dev": {"ids": [sensor_name],
                              },
                              "unit_of_meas": "mbar", 
                              "dev_cla": "pressure",
                              "val_tpl": "{{ value_json.pressure}}" 
            }
            client.publish(config_prefix+'_pressure'+'/config', json.dumps(pressure_class))

 
            all_sensor_state= { "airqual": air_qual, "humidity": humidity, "temperature": temperature, "pressure": pressure }
            client.publish(sensor_name+"/tele/SENSOR", json.dumps(all_sensor_state))

            #update mqtt every minute
            time.sleep(60)

except KeyboardInterrupt:
    pass
