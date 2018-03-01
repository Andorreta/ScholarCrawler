"""
Routes and views for the flask application.
"""

from datetime import datetime

from flask import render_template, redirect, request, jsonify, session, url_for, flash, current_app, json
from functools import wraps
from bson.json_util import dumps

from . import app
from .models import DataNotFound
from .models.factory import create_database_connection
from .settings import REPOSITORY_NAME, REPOSITORY_SETTINGS, API_NAME, API_VERSION
from .crawler.crawler import create_crawler


# Function to define the DB connection
def connect_db():
    return create_database_connection(REPOSITORY_NAME, REPOSITORY_SETTINGS)

    
# Function to make internal API calls
def make_api_callback(view_name, *args, **kwargs):
    # Calls internal view method, parses json, and returns python dict. #
    view = current_app.view_functions[view_name]
    response = view(*args, **kwargs)
    jsonResponse = json.loads(response.data)
    return jsonResponse


# login required decorator
def login_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if 'logged' in session:
            return function(*args, **kwargs)
        else:
            flash('You need to login first')
            print(request.values)
            return redirect(url_for('home'))
    return decorated_function


# login required decorator For the API
def login_required_api(function):
    @wraps(function)
    def decorated_function_api(*args, **kwargs):
        if 'login' in args:
            return function(*args, **kwargs)
        else:
            if 'logged' in session:
                return function(*args, **kwargs)
            else:
                return jsonify({"name" : API_NAME, "version" : API_VERSION, "message" : "You need to login first"})
    return decorated_function_api


# Main API URL
@app.route('/api')
def api():
    return jsonify({"name" : API_NAME, "version" : API_VERSION})


# Main API function controller
@app.route('/api/<function>', methods=['GET', 'POST'])
@login_required_api
def api_function(function):
    error = "function not found"
    if function == 'login':
        error = login_api(request)
    elif function == 'logout':
        error = logout_api(request)
    elif function == 'extract':
        extractor = create_crawler(session['user'])
        return extractor.extract()
    elif function == 'articles':
        articles = connect_db().get_articles(session['user']['id'])
        if articles:
            error = dumps(articles)
        else:
            error = "No articles found"
    return jsonify({"name" : API_NAME, "version" : API_VERSION, "function" : function, "message" : error})


# Make the login request
def login_api(request):
    # Check the request method and the database for data #
    error = None
    if request.method != 'POST':
        error = 'Bad request type: ' + request.method
    else:
        # Get the user value from the request #
        if 'emailSigninInput' in request.form:
            email = request.form.get('emailSigninInput')
        elif 'email' in request.form:
            email = request.form.get('email')
        else:
            return 'Unable to get user from request'

        # Get the password value from the request #
        if 'passwordSigninInput' in request.form:
            password = request.form.get('passwordSigninInput')
        elif 'password' in request.form:
            password = request.form.get('password')
        else:
            return 'Unable to get password from request'

        doc = connect_db().get_user(email)
        # Check if the user exists #
        if doc == 'userNotFound':
                error = 'User: ' + email + ' doesn\'t exist'
        else:
            # Check the password #
            if doc['password'] == password:
                session['logged'] = True
                session['user'] = {'id': str(doc['_id']), 'name': doc['name'], 'user': doc['mail'], 'scholarUser': doc['scholarUser'], 'scholarAliases': doc['scholarAliases']}
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
        title = 'Google Scholar Crawler',
        year = datetime.now().year,
    )


@app.route('/login', methods=['GET', 'POST'])
def login(defaultUrl='home'):
    apiCall = make_api_callback('api_function', 'login')
    flash(apiCall['message'])
    return redirect(request.referrer) or redirect(url_for(defaultUrl))


@app.route('/logout')
@login_required
def logout():
    # Makes the Logout request
    apiCall = make_api_callback('api_function', 'logout')
    flash(apiCall['message'])
    return redirect(url_for('home'))


@app.route('/signup', methods=['GET', 'POST'])
def signup(defaultUrl='home'):
    # Check the request method and the database for data #
    error = None
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
                session['user'] = {'id': str(doc['_id']), 'name': doc['name'], 'user': doc['mail'], 'scholarUser': doc['scholarUser'], 'scholarAliases': doc['scholarAliases']}
                error = 'Welcome ' + doc['name']
            else:
                error = 'Incorrect password'
    flash(error)
    return redirect(request.referrer) or redirect(url_for(defaultUrl))


@app.route('/settings')
@login_required
def settings():
    # Renders the crawler settings page.
    #settings = connect_db().get_user_config()
    return render_template(
        'settings.html',
        title='Settings',
        year=datetime.now().year,
        #settings=settings
    )


@app.route('/articles')
@login_required
def articles():
    # Renders the articles page, with a list of ALL the articles.
    return render_template(
        'articles.html',
        title = 'Articles for ' + session['user']['name'],
        year = datetime.now().year,
        articles = connect_db().get_articles(session['user']['id']),
    )


@app.route('/articles/<key>', methods=['GET', 'POST'])
@login_required
def details(key):
    # Renders the article details page.
    error_message = ''
    if request.method == 'POST':
        try:
            choice_key = request.form['choice']
            connect_db().increment_vote(key, choice_key)
            return redirect('/results/{0}'.format(key))
        except KeyError:
            error_message = 'Please make a selection.'

    return render_template(
        'details.html',
        title = 'Poll',
        year = datetime.now().year,
        poll = connect_db().get_poll(key),
        error_message = error_message,
    )

@app.route('/extract')
@login_required
def extract(defaultUrl='home'):
    flash("Extraction in progress")
    apiCall = make_api_callback('api_function', 'extract')
    if int(apiCall['Articles']) > 0:
        flash("Extraction Successfull")
    else:
        flash("Extraction Failed")
    return redirect(request.referrer) or redirect(url_for(defaultUrl))


@app.route('/contact')
def contact():
    # Renders the contact page. #
    return render_template(
        'contact.html',
        title='Contact',
        year=datetime.now().year,
    )


@app.route('/about')
def about():
    # Renders the about page. #
    comunication_prot = 'TCP'
    return render_template(
        'about.html',
        title = 'About',
        year = datetime.now().year,
        db_name = connect_db().name,
        comunitacion_protocol = comunication_prot
    )


@app.errorhandler(DataNotFound)
def page_not_found(error):
    # Renders error page.
    return 'Page doesn\'t exist.', 404
