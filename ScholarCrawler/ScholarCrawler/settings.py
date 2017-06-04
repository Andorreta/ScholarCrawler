"""
Settings for the polls application.

You can set values of REPOSITORY_NAME and REPOSITORY_SETTINGS in
environment variables, or set the default values in code here.
"""

from os import environ

REPOSITORY_NAME = environ.get('REPOSITORY_NAME', 'mongodb')

if REPOSITORY_NAME == 'mongodb':
    REPOSITORY_SETTINGS = {
        'MONGODB_HOST': environ.get('MONGODB_HOST', None),
        'MONGODB_DATABASE': environ.get('MONGODB_DATABASE', 'polls'),
        'MONGODB_COLLECTION': environ.get('MONGODB_COLLECTION', 'polls'),
    }
elif REPOSITORY_NAME == 'memory':
    REPOSITORY_SETTINGS = {}
else:
    raise ValueError('Unknown repository.')
