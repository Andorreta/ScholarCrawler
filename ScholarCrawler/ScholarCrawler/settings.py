"""
Settings for the Scholar Crawler application.

You can set values of REPOSITORY_NAME and REPOSITORY_SETTINGS in
environment variables, or set the default values in code here.
"""

from os import environ

REPOSITORY_NAME = environ.get('REPOSITORY_NAME', 'mongodb')

if REPOSITORY_NAME == 'mongodb':
    REPOSITORY_SETTINGS = {
        'MONGODB_HOST': environ.get('MONGODB_HOST', None),
        'MONGODB_DATABASE': environ.get('MONGODB_DATABASE', 'ScholarSettings'),
        'MONGODB_COLLECTION': environ.get('MONGODB_COLLECTION', 'Users'),
    }
elif REPOSITORY_NAME == 'memory':
    REPOSITORY_SETTINGS = {}
else:
    raise ValueError('Unknown repository.')

API_NAME = "Scholar Crawler API"
API_VERSION = "0.5"

# Tor Proxy Settings
TOR_IP = '127.0.0.1'
TOR_PORT = 9050
TOR_CONTROL_PORT = 9051
TOR_PASSWORD = 'P4ssW0rd'  # Hash 16:1EECF718CF92C0006045C9C9BC2E1D10E21B9D005C3C86746C7FFD4783


class BaseConfig(object):
    DEBUG = False
    SECRET_KEY = '\x0c\'\xbe\xc5/\x82\'\xca\xde?\xe8\x95Z\xc4`\x7f>ces\xad\x0e\xdc\xf3'


class LocalConfig(BaseConfig):
    DEBUG = False
