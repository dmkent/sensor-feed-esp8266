"""Sensor running app."""

from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='sensor_app',
    description='A simple sensor event loop',
    long_description=long_description,
    long_description_content_type='text/x=rst',
    url='https://github.com/dmkent/sensor-feed-esp8266',
    author='David Kent',
    author_email='davidkent@fastmail.com.au',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    entry_points={
        'console_scripts': [
            'sensor_app_rpi=sensor_app.main_rpi:main',
        ],
    },
)