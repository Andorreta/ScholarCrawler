"""
Routes and views for the flask application API.
"""

from flask import request, jsonify, session
from functools import wraps

from . import app
from .models.factory import DataNotFound


# Function to define the DB connection
def connect_db():
    from .models.factory import connect_to_database
    return connect_to_database(app.config['REPOSITORY_NAME'], app.config['REPOSITORY_SETTINGS'])


# Create and Start the Scheduler process
def create_scheduler():
    from .models.factory import create_scheduler_process
    return create_scheduler_process(app.config['REPOSITORY_NAME'], app.config['REPOSITORY_SETTINGS'])


# Connect to the local scheduler
def connect_scheduler():
    from . import scheduler
    return scheduler


# login required decorator For the API
def login_required_api(called_function):
    @wraps(called_function)
    def decorated_function_api(*args, **kwargs):
        if 'logged' in session:
            return called_function(*args, **kwargs)
        else:
            return jsonify({"name": app.config['API_NAME'], "version": app.config['API_VERSION'],
                            "message": "You need to login first"})

    return decorated_function_api


# Main API URL
@app.route('/api')
def api():
    return jsonify({"name": app.config['API_NAME'], "version": app.config['API_VERSION']})


@app.route('/api/public', methods=['GET', 'POST'])
@app.route('/api/public/<called_function>', methods=['GET', 'POST'])
def api_public(called_function=None):
    if called_function == 'login':
        message = api_login(request)
    elif called_function == 'signup':
        message = api_signup(request)
    elif called_function == 'server_info':
        message = api_info()
    else:
        message = 'Function doesn\'t exist or not implemented'

    return jsonify({"name": app.config['API_NAME'], "version": app.config['API_VERSION'], "function": called_function,
                    "message": message})


# Main API function controller
@app.route('/api/<called_function>', methods=['GET', 'POST'])
@login_required_api
def api_function(called_function=None):
    if called_function == 'logout':
        message = api_logout()
    elif called_function == 'extract_articles':
        message = api_extract_articles()
    elif called_function == 'get_articles':
        message = api_get_articles()
    elif called_function == 'get_settings':
        message = api_get_user_settings()
    elif called_function == 'get_job_status':
        message = api_get_job_status(request)
    elif called_function == 'store_settings':
        message = api_store_user_settings(request)
    elif called_function == 'store_aliases':
        message = api_store_user_aliases(request)
    elif called_function == 'set_scheduler':
        message = api_set_scheduler_job(request)
    elif called_function == 'remove_scheduler':
        message = api_remove_scheduler(request)
    else:
        message = 'Function doesn\'t exist or not implemented'

    return jsonify({"name": app.config['API_NAME'], "version": app.config['API_VERSION'], "function": called_function,
                    "message": message})


# Make the login request
def api_login(login_request):
    # Check the request method and the database for data
    if login_request.method != 'POST':
        return 'Bad request type: ' + login_request.method

    # Get the user value from the request #
    if 'emailSigninInput' in login_request.form:
        email = login_request.form.get('emailSigninInput')
    elif 'email' in login_request.form:
        email = login_request.form.get('email')
    else:
        return 'Unable to get user from request'

    # Get the password value from the request #
    if 'passwordSigninInput' in login_request.form:
        password = login_request.form.get('passwordSigninInput')
    elif 'password' in login_request.form:
        password = login_request.form.get('password')
    else:
        return 'Unable to get password from request'

    doc = connect_db().get_user_by_mail(email)
    # Check if the user exists #
    if doc == 'userNotFound':
        return 'User: ' + email + ' doesn\'t exist'

    # Check the password #
    if doc['password'] == password:
        session['logged'] = True
        session['user'] = {'id': str(doc['_id']), 'name': doc['name'], 'user': doc['mail'],
                           'scholarUser': doc['scholarUser'], 'scholarAliases': doc['scholarAliases']}
        return 'Welcome ' + doc['name']

    return 'Incorrect password'


# Makes the registration request
def api_signup(signup_request):
    # Check the request method and make a data validation
    if signup_request.method != 'POST':
        return 'Bad request type: ' + signup_request.method

    if 'emailSignUpInput' in signup_request.form:
        email = signup_request.form.get('emailSignUpInput')
    elif 'email' in signup_request.form:
        email = signup_request.form.get('email')
    else:
        return 'Invalid request: Missing Email'

    if 'usernameSignUpInput' in signup_request.form:
        username = signup_request.form.get('usernameSignUpInput')
    elif 'username' in signup_request.form:
        username = signup_request.form.get('username')
    else:
        return 'Invalid request: Missing User Name'

    if 'passwordSignUpInput' in signup_request.form:
        password = signup_request.form.get('passwordSignUpInput')
    elif 'password' in signup_request.form:
        password = signup_request.form.get('password')
    else:
        return 'Invalid request: Missing Password'

    if 'passwordSignUpInput2' in signup_request.form:
        password_confirmation = signup_request.form.get('passwordSignUpInput2')
    elif 'password_confirmation' in signup_request.form:
        password_confirmation = signup_request.form.get('password_confirmation')
    else:
        return 'Invalid request: Missing Password Confirmation'

    # Check ir the user already exists
    db = connect_db()
    doc = db.get_user_by_mail(email)

    if doc != 'userNotFound':
        return 'Mail: "' + email + '" already in the database'

    if password != password_confirmation:
        return 'Passwords don\'t match'

    # Add the new user to the database
    doc = {
        'name': username,
        'mail': email,
        'password': password_confirmation,
        'scholarUser': username,
        'scholarAliases': [],
        'unusedScholarAliases': [],
    }
    db.add_new_user(doc)

    # Sign in the recently created user
    doc = db.get_user_by_mail(email)
    session['logged'] = True
    session['user'] = {'id': str(doc['_id']), 'name': doc['name'], 'user': doc['mail'],
                       'scholarUser': doc['scholarUser'], 'scholarAliases': doc['scholarAliases']}

    return 'User creation Successful. Welcome ' + str(doc['name'])


# Returns the API server status
def api_info():
    return {
        'database': connect_db().name,
        'communication_protocol': 'HTTP',  # Later we can add Websockets or another protocol
        'scheduler_store': connect_scheduler().name,
        'scheduler_status': connect_scheduler().get_status(),
    }


# Makes the Logout request
def api_logout():
    # Erase the user session and data
    session.pop('logged', None)
    session.pop('user', None)

    return 'Logout successful'


# Makes the Google Scholar Articles extraction
def api_extract_articles():
    from .crawler.crawlerGeneral import create_crawler_and_extract

    # Start a 1 time Scheduler job to extract the data
    return connect_scheduler().add_one_time_job(function_name=create_crawler_and_extract,
                                                func_args={'user_data': session['user'],
                                                           'desired_crawler': 'googleScholarArticles'},
                                                user_id=session['user']['id'])


# Get the User articles from the database
def api_get_articles():
    user_articles = connect_db().get_articles(session['user']['id'])

    if len(user_articles['user']) + len(user_articles['others']) > 0:
        return user_articles

    return "No articles found"


# Get the User settings from the database
def api_get_user_settings():
    settings = connect_db().get_user_by_id(session['user']['id'])

    if settings is 'userNotFound':
        return {
            'error': 'Unable to retrieve ' + session['user']['name'] + ' settings'
        }

    # Remove some key user settings to avoid data compromising
    del settings['_id']
    del settings['password']

    return settings


# Get the User settings from the database
def api_get_job_status(status_request):
    # Check the request method and make a data validation
    if status_request.method != 'POST':
        return 'Bad request type: ' + status_request.method

    # Check the job ID
    if status_request.form.get('job_id') is None or status_request.form.get('job_id') is '':
        return 'Empty Job ID'

    # Get the Job Status from the Scheduler
    message = connect_scheduler().check_job_status(status_request.form.get('job_id'))

    if 'error' in message:
        return message['message']

    return message


# Store the User settings
def api_store_user_settings(update_request):
    # Check the request method and make a data validation
    if update_request.method != 'POST':
        return 'Bad request type: ' + update_request.method

    # Get the current User Data from the DB
    user_data = connect_db().get_user_by_id(session['user']['id'])
    updated_components = []

    if update_request.form.get('email') is not None and update_request.form.get('email') is not '':
        user_data['mail'] = update_request.form.get('email')
        updated_components.append('Email')

    if update_request.form.get('password') is not None and update_request.form.get('password') is not '':
        user_data['password'] = update_request.form.get('password')
        updated_components.append('Password')

    if update_request.form.get('scholarUser') is not None and update_request.form.get('scholarUser') is not '':
        user_data['scholarUser'] = update_request.form.get('scholarUser')
        updated_components.append('Scholar_User')

    if len(updated_components) == 0:
        return 'Nothing changed'

    # Upload the changes into the Repository
    connect_db().update_user_by_id(session['user']['id'], user_data)

    # Store the new user settings for the current session
    session['user'] = {'id': str(user_data['_id']), 'name': user_data['name'], 'user': user_data['mail'],
                       'scholarUser': user_data['scholarUser'], 'scholarAliases': user_data['scholarAliases']}

    if len(updated_components) == 1:
        message = 'Updated the ' + updated_components[0]
    else:
        message = 'Updated the following components:'

        for component in updated_components:
            message = message + ' ' + component

    return message


# Store the User aliases
def api_store_user_aliases(update_request):
    import re

    # Check the request method and make a data validation
    if update_request.method != 'POST':
        return 'Bad request type: ' + update_request.method

    # Get the current User Data from the DB
    user_data = connect_db().get_user_by_id(session['user']['id'])

    request_aliases = update_request.form.to_dict()
    user_data['scholarAliases'] = []
    user_data['unusedScholarAliases'] = []

    regex = re.compile('unusedAliases', re.IGNORECASE)
    for alias in request_aliases:
        if regex.match(alias):
            user_data['unusedScholarAliases'].append(request_aliases[alias])
        else:
            user_data['scholarAliases'].append(request_aliases[alias])

    if not user_data['scholarAliases'] and not user_data['unusedScholarAliases']:
        return 'Nothing changed'

    # Upload the changes into the Repository
    connect_db().update_user_by_id(session['user']['id'], user_data)

    # Store the new user settings for the current session
    session['user'] = {'id': str(user_data['_id']), 'name': user_data['name'], 'user': user_data['mail'],
                       'scholarUser': user_data['scholarUser'], 'scholarAliases': user_data['scholarAliases']}

    return 'Updated the Scholar Aliases'


# Create a Job in the Scheduler with the provided parameters
def api_set_scheduler_job(job_request):
    from .crawler.crawlerGeneral import create_crawler_and_extract

    # TODO Validate received args and create Cron table (forced value for every 3 days at 3:30 am)
    cron = {
        'day': '*/3',
        'hour': 3,
        'minute': 30,
        'second': 0,
    }

    job_id = connect_scheduler().add_scheduled_job(function_name=create_crawler_and_extract,
                                       func_args={'user_data': session['user'],
                                                  'desired_crawler': 'googleScholarArticles'},
                                       user_id=session['user']['id'],
                                       cron=cron,
                                       )

    return api_store_user_job_id(job_id)


# Store the Job Id in the user settings page TODO move to factory
def api_store_user_job_id(job_id):
    if not isinstance(job_id, str) or job_id is '':
        return 'Invalid Job Id'

    # Get the current User Data from the DB
    user_data = connect_db().get_user_by_id(session['user']['id'])

    user_data['schedulerJobIds'].append(job_id)

    # Upload the changes into the Repository
    connect_db().update_user_by_id(session['user']['id'], user_data)

    # Store the new user settings for the current session
    session['user'] = {'id': str(user_data['_id']), 'name': user_data['name'], 'user': user_data['mail'],
                       'scholarUser': user_data['scholarUser'], 'scholarAliases': user_data['scholarAliases']}

    return job_id


# Remove a Scheduled job
def api_remove_scheduler(remove_request):
    # Check the request method and make a data validation
    if remove_request.method != 'POST':
        return 'Bad request type: ' + remove_request.method

    # Check the job ID
    if remove_request.form.get('job_id') is None or remove_request.form.get('job_id') is '':
        return 'Empty Job ID'

    # Remove the job from the Scheduler
    message = connect_scheduler().remove_scheduled_job(remove_request.form.get('job_id'))

    # Remove the Job Id from the user settings
    if not message['error']:
        api_remove_user_job_id(remove_request.form.get('job_id'))

    return message['message']


# Remove the Job Id in the user settings page TODO move to factory
def api_remove_user_job_id(job_id):
    if not isinstance(job_id, str) or job_id is '':
        return 'Invalid Job Id'

    # Get the current User Data from the DB
    user_data = connect_db().get_user_by_id(session['user']['id'])

    user_data['schedulerJobIds'].remove(job_id)

    # Upload the changes into the Repository
    connect_db().update_user_by_id(session['user']['id'], user_data)

    # Store the new user settings for the current session
    session['user'] = {'id': str(user_data['_id']), 'name': user_data['name'], 'user': user_data['mail'],
                       'scholarUser': user_data['scholarUser'], 'scholarAliases': user_data['scholarAliases']}

    return job_id


# Renders error page.
@app.errorhandler(DataNotFound)
def page_not_found(error):
    if not error:
        error = 'Page doesn\'t exist.'
    return error, 404
