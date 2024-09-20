""" Setup script for the package. """
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='panasonic-comfort-cloud-mqtt',
      version='0.6.0',
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
      install_requires=['pcomfortcloud>=0.1.0', 'paho-mqtt==1.6.1'],
      )
