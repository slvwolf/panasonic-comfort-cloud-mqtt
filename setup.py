#!/usr/bin/env python

from distutils.core import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='panasonic-comfort-cloud-mqtt',
    version='0.3.0',
    description='Home-Assistant MQTT bridge for Panasonic Comfort Cloud ',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Santtu Järvi',
    author_email='slvwolf@finfur.net',
    keywords='home automation panasonic climate mqtt hass',
    url='https://github.com/slvwolf/panasonic-comfort-cloud-mqtt',
    classifiers=[
       'Topic :: Home Automation',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    packages=['pcfmqtt'],
    license='MIT',
    install_requires=['pcomfortcloud>=0.0.22', 'paho-mqtt>=1.6.1'],
)