"""
Routes and views for the flask application.
"""

from datetime import datetime

from flask import render_template, redirect, request, jsonify, session, url_for, flash
from functools import wraps

from . import app
from .models import DataNotFound
from .models.factory import create_database_connection
from .settings import REPOSITORY_NAME, REPOSITORY_SETTINGS, API_NAME, API_VERSION
from .crawler.crawler import create_crawler


# Function to define the DB connection
def connect_db():
    return create_database_connection(REPOSITORY_NAME, REPOSITORY_SETTINGS)


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


def login_required_api(function):
    @wraps(function)
    def decorated_function_api(*args, **kwargs):
        if 'logged' in session:
            return function(*args, **kwargs)
        else:
            return jsonify({"name" : API_NAME, "version" : API_VERSION, "message" : "You need to login first"})
    return decorated_function_api


@app.route('/')
@app.route('/home')
def home():
    # Renders the home page
    return render_template(
        'index.html',
        title = 'Google Scholar Crawler',
        year = datetime.now().year,
    )


@app.route('/api')
def api():
    return jsonify({"name" : API_NAME, "version" : API_VERSION})


@app.route('/api/<function>', methods=['GET', 'POST'])
@login_required_api
def api_function(function):
    if function == 'extract':
        extractor = create_crawler(session['user'])
        return extractor.extract()
    else:
        return jsonify({"name" : API_NAME, "version" : API_VERSION, "function" : function, "message" : "function not found"})


@app.route('/extract')
@login_required
def extract():
    extractor = create_crawler(session['user'])
    return extractor.extract()


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


@app.route('/results')
@login_required
def resultspolls():
    # Renders the polls page, with a list of all polls. #
    return render_template(
        'pollsresult.html',
        title='Polls list',
        year=datetime.now().year,
        polls=connect_db().get_polls(),
    )


@app.route('/login', methods=['GET', 'POST'])
def login(defaultUrl='home'):
    # Check the request method and the database for data #
    error = None
    if request.method != 'POST':
        error = 'Bad request type: ' + request.method
    else:
        doc = connect_db().get_user(request.form.get('emailSigninInput'))
        # Check if the user exists #
        if doc == 'userNotFound':
             error = 'User: ' + request.form.get('emailSigninInput') + ' doesn\'t exist'
        else:
            # Check the password #
            if doc['password'] == request.form.get('passwordSigninInput'):
                session['logged'] = True
                session['user'] = {'id': str(doc['_id']), 'name': doc['name'], 'user': doc['mail'], 'scholarUser': doc['scholarUser'], 'scholarAliases': doc['scholarAliases']}
                error = 'Welcome ' + doc['name']
            else:
                error = 'Incorrect password'
    #return jsonify({"login" : login, "request" : request.values, "error": error})
    flash(error)
    return redirect(request.referrer) or redirect(url_for(defaultUrl))


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    # Seeds the database with sample articles.
    session.pop('logged', None)
    flash('Logout successful')
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
    #return jsonify({"login" : login, "request" : request.values, "error": error})
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


@app.errorhandler(DataNotFound)
def page_not_found(error):
    # Renders error page.
    return 'Page doesn\'t exist.', 404
