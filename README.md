# Panasonic Comfort Cloud MQTT Bridge
Home-Assistant MQTT bridge for Panasonic Comfort Cloud. 

_Note: Current version has only been tested with model `CS-HZ25UKE` so there might be some problems with other models. If._

![HA](/ha-dashboard.png "HA")

Uses `pcomfortcloud` for Panasonic Comfort Cloud and `paho-mqtt` for MQTT.

## Features
- Auto registers entities to Home Assistant
- Non-optimistic behaviour
- AC operating mode controls 
- Target temperature controls
- Power controls for retaining preset modes
- Inside and outside temperature sensors
- Respects HA birth and last will events

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

### Running with Docker

    docker build  . --tag pcc-mqtt
    docker run -it -d --name pcc-mqtt -e "USERNAME=username@dev.null" -e "PASSWORD=123password" -e "MQTT=127.0.0.1" pcc-mqtt

Available env. variables,

- USERNAME
- PASSWORD
- MQTT (default: localhost)
- MQTT_PORT (default: 1883)
- TOPIC_PREFIX (default: homeassistant)

At minimum `USERNAME`, `PASSWORD` and `MQTT` needs to be defined

## Development

Project has two branches,
- `main` containing more or less stable version of the project
- `dev` development branch with most likely breaking changes

### Plans for version 1.0.0

- [X] Additonal sensors for inside and outside temperature
- [X] Proper entity id generation (currenlty will fail with really wild names)
- [X] Proper shutdown
- [ ] Logging cleanup
- [ ] Error handling in general
- [ ] Proper documentation
- [ ] Docker package

### Beyound 1.x

- [ ] Fan mode support
- [ ] Support for Eco mode
- [ ] Support for Nano mode
- [ ] Fan speed support
- [ ] Service state events
- [ ] Stop listening to all events in HA topic
- [ ] Power usage metrics