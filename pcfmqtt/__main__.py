""" Main entry point for the pcfmqtt package. """
import argparse
import os
import logging
import pcfmqtt.service

logger_mapping = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL}


def main():
    """ Where the magic happens """
    parser = argparse.ArgumentParser(
        description='Home-Assistant MQTT bridge for Panasonic Comfort Cloud')
    parser.add_argument('-u', '--username', type=str, default=os.environ.get('USERNAME'),
                        help="Panasonic Comfort Cloud username, usually email address. Environment variable `USERNAME`")
    parser.add_argument('-P', '--password', type=str, default=os.environ.get('PASSWORD'),
                        help="Panasonic Comfort Cloud password. Environment variable `PASSWORD`")
    parser.add_argument('-s', '--server', type=str, default=os.environ.get('MQTT') or "localhost",
                        help="MQTT server address, default `localhost`. Environment variable: `MQTT`")
    parser.add_argument('-p', '--port', type=int, default=os.environ.get('MQTT_PORT') or 1883,
                        help="MQTT server port, default 1883. Environment variable `MQTT_PORT`")
    parser.add_argument('-t', '--topic', type=str, default=os.environ.get('TOPIC_PREFIX') or "homeassistant",
                        help="MQTT discovery topic prefix, default `homeassistant`. Environment variable TOPIC_PREFIX.")
    parser.add_argument('-l', '--log', type=str, default=os.environ.get('LOG_LEVEL') or "INFO",
                        choices=logger_mapping.keys(),
                        help="Logging level to use, defaults to INFO")

    args = parser.parse_args()
    logging.root.setLevel(logger_mapping.get(args.log, logging.INFO))
    handler = logging.StreamHandler()
    logger_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(logger_format)
    logging.root.addHandler(handler)

    if not args.username or not args.password or not args.server or not args.port or not args.topic:
        exit(parser.print_usage())

    s = pcfmqtt.service.Service(
        args.username, args.password, args.server, args.port, args.topic)
    s.start()


if __name__ == "__main__":
    main()
