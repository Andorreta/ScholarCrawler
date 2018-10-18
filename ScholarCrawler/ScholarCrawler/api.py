"""
Routes and views for the flask application API.
"""

from flask import request, jsonify, session
from functools import wraps

from . import app
from .models.factory import DataNotFound
from .settings import API_NAME, API_VERSION


# Function to define the DB connection
def connect_db():
    from .settings import REPOSITORY_NAME, REPOSITORY_SETTINGS
    from .models.factory import connect_to_database

    return connect_to_database(REPOSITORY_NAME, REPOSITORY_SETTINGS)


# Create and Start the Scheduler process
def create_scheduler():
    from .settings import REPOSITORY_NAME, REPOSITORY_SETTINGS
    from .models.factory import create_scheduler_process

    return create_scheduler_process(REPOSITORY_NAME, REPOSITORY_SETTINGS)


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
            return jsonify({"name": API_NAME, "version": API_VERSION, "message": "You need to login first"})

    return decorated_function_api


# Main API URL
@app.route('/api')
def api():
    return jsonify({"name": API_NAME, "version": API_VERSION})


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

    return jsonify({"name": API_NAME, "version": API_VERSION, "function": called_function, "message": message})


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
    else:
        message = 'Function doesn\'t exist or not implemented'

    return jsonify({"name": API_NAME, "version": API_VERSION, "function": called_function, "message": message})


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

    if signup_request.form.get('emailSignUpInput') is None:
        return 'Invalid request: Missing Email'

    if signup_request.form.get('usernameSignUpInput') is None:
        return 'Invalid request: Missing Name'

    if signup_request.form.get('passwordSignUpInput') is None:
        return 'Invalid request: Missing Password'

    if signup_request.form.get('passwordSignUpInput2') is None:
        return 'Invalid request: Missing Password Confirmation'

    # Check ir the user already exists
    db = connect_db()
    doc = db.get_user_by_mail(signup_request.form.get('emailSignUpInput'))

    if doc != 'userNotFound':
        return 'Mail: "' + signup_request.form.get('emailSignUpInput') + '" already in the database'

    if signup_request.form.get('passwordSignUpInput') != signup_request.form.get('passwordSignUpInput2'):
        return 'Passwords don\'t match'

    # Add the new user to the database
    doc = {
        'name': signup_request.form.get('usernameSignUpInput'),
        'mail': signup_request.form.get('emailSignUpInput'),
        'password': signup_request.form.get('passwordSignUpInput'),
        'scholarUser': signup_request.form.get('usernameSignUpInput'),
        'scholarAliases': [],
    }
    db.add_new_user(doc)

    # Sign in the recently created user
    doc = db.get_user_by_mail(signup_request.form.get('emailSignUpInput'))
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

    # TODO ya empieza el Scheduler y hay que ver si crea los jobs o simplemente no lo los crea
    return connect_scheduler().add_one_time_job(function_name=create_crawler_and_extract,
                                                func_args={'user_data': session['user'],
                                                           'desired_crawler': 'googleScholarArticles'},
                                                user_id=session['user']['id'])
    # return create_crawler(session['user'], 'googleScholarArticles').data_extraction()


# Get the User articles from the database
def api_get_articles():
    user_articles = {
        'user': connect_db().get_articles(session['user']['id']),
        'others': connect_db().get_articles_others(session['user']['id']),
    }

    if len(user_articles['user']) + len(user_articles['others']) > 0:
        return user_articles

    return "No articles found"


# Get the User settings from the database
def api_get_user_settings():
    return connect_db().get_user_by_id(session['user']['id'])


# TODO FUNCIONES A IMPLEMENTAR
# def api_set_scheduler():
# TODO establecer un scheduler para el job/user que se quiera usar.

# def api_remove_scheduler():
# TODO quitar un scheduler para el job/user que se quiera

# Renders error page.
@app.errorhandler(DataNotFound)
def page_not_found(error):
    if not error:
        error = 'Page doesn\'t exist.'
    return error, 404
