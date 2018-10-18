"""
Routes and views for the flask application.
"""

from flask import render_template, redirect, request, jsonify, session, url_for, flash, current_app, json
from functools import wraps
from bson.json_util import dumps

from . import app
from .models import DataNotFound
from .models.factory import create_database_connection
from .settings import REPOSITORY_NAME, REPOSITORY_SETTINGS, API_NAME, API_VERSION
from .crawler.crawlerGeneral import *


# Function to define the DB connection
def connect_db(): # TODO Cambiar esto, En lugar de hacer un create, deberiamos de hacer un connect con un metodo de fallback por si falla
    return create_database_connection(REPOSITORY_NAME, REPOSITORY_SETTINGS)


# Function to make internal API calls
def make_api_callback(view_name, *args, **kwargs):
    # Calls internal view method, parses json, and returns python dict. #
    view = current_app.view_functions[view_name]
    response = view(*args, **kwargs)
    json_response = json.loads(response.data)
    return json_response


# login required decorator
def login_required(called_function):
    @wraps(called_function)
    def decorated_function(*args, **kwargs):
        if 'logged' in session:
            return called_function(*args, **kwargs)
        else:
            flash('You need to login first')
            print(request.values)
            return redirect(url_for('home'))

    return decorated_function


# login required decorator For the API
def login_required_api(called_function):
    @wraps(called_function)
    def decorated_function_api(*args, **kwargs):
        if 'login' in args:
            return called_function(*args, **kwargs)
        else:
            if 'logged' in session:
                return called_function(*args, **kwargs)
            else:
                return jsonify({"name": API_NAME, "version": API_VERSION, "message": "You need to login first"})

    return decorated_function_api


# Main API URL
@app.route('/api')
def api():
    return jsonify({"name": API_NAME, "version": API_VERSION})


# Main API function controller
@app.route('/api/<function>', methods=['GET', 'POST'])
@login_required_api
def api_function(called_function):
    error = "function not found"
    if called_function == 'login':
        error = login_api(request)
    elif called_function == 'logout':
        error = logout_api()
    elif called_function == 'extract':
        extractor = create_crawler(session['user'], 'googleScholarArticles')
        return extractor.data_extraction()
    elif called_function == 'get_articles':
        user_articles = {
            'user': connect_db().get_articles(session['user']['id']),
            'others': connect_db().get_articles_others(session['user']['id']),
        }
        if len(user_articles['user']) + len(user_articles['others']) > 0:
            error = dumps(user_articles)
        else:
            error = "No articles found"
    return jsonify({"name": API_NAME, "version": API_VERSION, "function": called_function, "message": error})


# Make the login request
def login_api(login_request):
    # Check the request method and the database for data #
    if login_request.method != 'POST':
        error = 'Bad request type: ' + login_request.method
    else:
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
            error = 'User: ' + email + ' doesn\'t exist'
        else:
            # Check the password #
            if doc['password'] == password:
                session['logged'] = True
                session['user'] = {'id': str(doc['_id']), 'name': doc['name'], 'user': doc['mail'],
                                   'scholarUser': doc['scholarUser'], 'scholarAliases': doc['scholarAliases']}
                error = 'Welcome ' + doc['name']
            else:
                error = 'Incorrect password'
    return error


# Makes the Logout request
def logout_api():
    # Erase the user session and data
    session.pop('logged', None)
    session.pop('user', None)
    return 'Logout successful'


@app.route('/')
@app.route('/home')
def home():
    # Renders the home page
    return render_template(
        'index.html',
        title='Google Scholar Crawler',
        year=datetime.datetime.now().year,
    )


@app.route('/login', methods=['GET', 'POST'])
def login(default_url='home'):
    api_call = make_api_callback('api_function', 'login')
    flash(api_call['message'])
    return redirect(request.referrer) or redirect(url_for(default_url))


@app.route('/logout')
@login_required
def logout():
    # Makes the Logout request
    api_call = make_api_callback('api_function', 'logout')
    flash(api_call['message'])
    return redirect(url_for('home'))


@app.route('/signup', methods=['GET', 'POST'])
def signup(default_url='home'):
    # Check the request method and the database for data #
    if request.method != 'POST':
        error = 'Bad request type: ' + request.method
    else:
        doc = connect_db().get_user(request.form.get('emailSigninInput'))
        # Check if the user exists #
        if doc != 'userNotFound':
            error = 'User: ' + request.form.get('emailSigninInput') + ' already exist'
        else:
            # Check the password #
            if doc['password'] == request.form.get('passwordSigninInput'):
                session['logged'] = True
                session['user'] = {'id': str(doc['_id']), 'name': doc['name'], 'user': doc['mail'],
                                   'scholarUser': doc['scholarUser'], 'scholarAliases': doc['scholarAliases']}
                error = 'Welcome ' + doc['name']
            else:
                error = 'Incorrect password'
    flash(error)
    return redirect(request.referrer) or redirect(url_for(default_url))


@app.route('/settings')
@login_required
def settings():
    # Renders the crawler user settings page
    return render_template(
        'settings.html',
        title='Settings',
        year=datetime.datetime.now().year,
        # settings=connect_db().get_user_config() # TODO añadir esto y una funcion para autorefrescar la pagina de settings al cambiar algo.
    )


@app.route('/articles')
@login_required
def articles():
    # Renders the articles page, with a list of ALL the articles.
    api_call = make_api_callback('api_function', 'get_articles')

    user_articles = json.loads(api_call['message'])
    if 'user' not in user_articles:
        user_articles = {
            'user': [],
            'others': [],
        }

    return render_template(
        'articles.html',
        title='Articles for ' + session['user']['name'],
        year=datetime.datetime.now().year,
        articles=user_articles
    )


@app.route('/extract')
@login_required
def extract(default_url='home'):
    # Makes the Google Scholar Articles extraction
    flash("Extraction in progress")
    api_call = make_api_callback('api_function', 'extract')

    if int(api_call['Articles']) > 0:
        flash("Extraction Successful")
    else:
        flash("Extraction Failed")

    return redirect(request.referrer) or redirect(url_for(default_url))


@app.route('/contact')
def contact():
    # Renders the contact page. #
    return render_template(
        'contact.html',
        title='Contact',
        year=datetime.datetime.now().year,
    )


@app.route('/about')
def about():
    # Renders the about page. #
    communication_protocol = 'TCP'
    return render_template(
        'about.html',
        title='About',
        year=datetime.datetime.now().year,
        db_name=connect_db().name,
        comunitacion_protocol=communication_protocol
    )


@app.errorhandler(DataNotFound)
def page_not_found(error):
    # Renders error page.
    if not error:
        error = 'Page doesn\'t exist.'
    return error, 404
