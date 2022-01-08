# Panasonic Comfort Cloud MQTT Bridge
Home-Assistant MQTT bridge for Panasonic Comfort Cloud. 

_Note: Currently this brige is a one evening prototype project. Main features should work but corner cases will definitely cause problems. Current version has only been tested with model `CS-HZ25UKE`. Let me know if you hit any issues._

![HA](/ha-dashboard.png "HA")

Uses `pcomfortcloud` for Panasonic Comfort Cloud and `paho-mqtt` for MQTT.

## Features
- Auto registers entities to Home Assistant
- AC operating mode controls (Non-optimistic)
- Target temperature controls (Non-optimistic)
- Inside and outside temperature sensors

## Usage

### Installing

    git clone https://github.com/slvwolf/panasonic-comfort-cloud-mqtt.git
    pip3 install .

### Running

    usage: run.py [-h] [-u USERNAME] [-P PASSWORD] [-s SERVER] [-p PORT] [-t TOPIC]

    Home-Assistant MQTT bridge for Panasonic Comfort Cloud

    optional arguments:
    -h, --help            show this help message and exit
    -u USERNAME, --username USERNAME
                            Panasonic Comfort Cloud username, usually email address. Environment variable `USERNAME`
    -P PASSWORD, --password PASSWORD
                            Panasonic Comfort Cloud password. Environment variable `PASSWORD`
    -s SERVER, --server SERVER
                            MQTT server address, default `localhost`. Environment variable: `MQTT`
    -p PORT, --port PORT  MQTT server port, default 1883. Environment variable `MQTT_PORT`
    -t TOPIC, --topic TOPIC
                            MQTT discovery topic prefix, default `homeassistant`. Environment variable TOPIC_PREFIX.

Example,

    python3 run.py -u username@dev.null -P 123password -s 127.0.0.1

## Features Plans

### High Priority

- [X] Additonal sensors for inside and outside temperature
- [X] Proper entity id generation (currenlty will fail with really wild names)
- [ ] Error handling in general
- [ ] Proper documentation
- [ ] Docker package
- [ ] Proper shutdown

## Maybe

- [ ] Fan mode support
- [ ] Support for Eco mode
- [ ] Support for Nano mode
- [ ] Fan speed support
- [ ] Service state events
- [ ] Stop listening to all events in HA topic
- [ ] Power usage metrics