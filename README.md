# Panasonic Comfort Cloud MQTT Bridge
Home-Assistant MQTT bridge for Panasonic Comfort Cloud. Supports automatic entity registration to Home Assistant and full control over the devices.

_Note: Current version has been tested with model `CS-HZ25UKE`, let me know if noticing any problems with other models_

![Controls](/docs/preview.png "Controls")

Uses `pcomfortcloud` for Panasonic Comfort Cloud and `paho-mqtt` for MQTT.

## Features
- Auto registers entities to Home Assistant
- Fan speed controls
- AC operating modes 
- Target temperature controls
- Non-optimistic behaviour
- Power controls for retaining preset modes
- Inside and outside temperature sensors
- Eco-mode controls
- Swing settings (horizontal and vertical)
- Device bundling
- Respects HA birth and last will events

## Usage 

### Running Locally

    usage: run.py [-h] [-u USERNAME] [-P PASSWORD] [-s SERVER] [-p PORT] [-t TOPIC] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

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
    -i INTERVAL, --interval INTERVAL
                            Device update interval in seconds, default 60. Not recommended to put value below 60
                            as this might cause too many request error from the API. Environment variable `UPDATE_INTERVAL`
    -t TOPIC, --topic TOPIC
                            MQTT discovery topic prefix, default `homeassistant`. Environment variable TOPIC_PREFIX.
    -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                            Logging level to use, defaults to INFO

Example,

    git clone https://github.com/slvwolf/panasonic-comfort-cloud-mqtt.git
    pip3 install .
    python3 run.py -u username@dev.null -P 123password -s 127.0.0.1

### Running with Docker
Currently there are no readily built Docker images but building the image yourself can be done simply by running `make docker`. 

Example of building and running (just change USERNAME, PASSWORD and MQTT variables),

    git clone https://github.com/slvwolf/panasonic-comfort-cloud-mqtt.git
    make docker
    docker run -it -d --name pcc-mqtt -e "USERNAME=username@dev.null" -e "PASSWORD=123password" -e "MQTT=127.0.0.1" pcc-mqtt

Available env. variables,

- USERNAME
- PASSWORD
- MQTT (default: localhost)
- MQTT_PORT (default: 1883)
- INTERVAL (default 60)
- TOPIC_PREFIX (default: homeassistant)
- LOG_LEVEL (default: info)

At minimum `USERNAME`, `PASSWORD` and `MQTT` needs to be defined

To access the logs run,

    docker logs pcc-mqtt

### Plans for version 1.0.0

- [ ] Docker package

### Beyound 1.x

- [X] Fan mode support
- [X] Support for Eco mode
- [X] Support for Nano mode
- [X] Fan speed support
- [ ] Service state events
- [ ] Power usage metrics