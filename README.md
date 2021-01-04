# bme680-mqtt
Modifies example by [Pimoroni](https://github.com/pimoroni/bme680/blob/master/examples/indoor-air-quality.py) to publish [bme680](https://learn.pimoroni.com/tutorial/sandyj/getting-started-with-bme680-breakout) data via MQTT and shown automatically as an [Home-assistant](https://home-assistant.io/) entity.

Most of the code is based on [Robin Cole own bme680-mqtt](https://github.com/robmarkcole/bme680-mqtt), with the mqtt code altered to comply with [Home Assistant MQTT-Discovery](https://www.home-assistant.io/docs/mqtt/discovery/) schema.
Most of the code is based on both documentation and by checking the message queue from a couple of [TASMOTA](https://tasmota.github.io/docs/) devices using [MQTT Explorer](http://mqtt-explorer.com/)

Everything is auto set in the code, you just have to configure the following parameters:
- sensor name (you can have several such sensors around, so you should set an unique id)
- MQTT Broker (usually the Hassio server with MosQuiTTo integration installed)
- MQTT username and password (default MosQuiTTo integration require a username and password set via Home Assistant users)

Finally you may want to [customise](https://home-assistant.io/docs/configuration/customizing-devices/) the look of the sensors in the Home-assistant front end. 


<img src="https://github.com/murraythegoz/bme680-mqtt/blob/master/bme680-mqtt.PNG">
