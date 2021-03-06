"""
The flask application package.
"""

from flask import Flask
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Set the config for the APP (TODO Update to load the config based on the environment)
app.config.from_object('ScholarCrawler.settings.LocalConfig')

from . import api
from . import views

# Start the Scheduler
scheduler = api.create_scheduler()