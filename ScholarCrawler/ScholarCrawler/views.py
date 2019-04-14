"""
Routes and views for the flask application Views.
"""

import datetime

from flask import render_template, redirect, request, session, url_for, flash, current_app, json
from functools import wraps

from . import app


# Function to make internal API calls
def make_api_callback(view_name, *args, **kwargs):
    # Calls internal view method, parses json, and returns python dict. #
    view = current_app.view_functions[view_name]
    response = view(*args, **kwargs)

    return json.loads(response.data)  # Return the JSON Response


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
    api_call = make_api_callback('api_public', 'login')

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
        api_call = make_api_callback('api_public', 'signup')
        error = api_call['message']

    flash(error)
    return redirect(request.referrer) or redirect(url_for(default_url))


@app.route('/settings')
@login_required
def settings(default_url='home'):
    # Renders the crawler user settings page
    api_call = make_api_callback('api_function', 'get_settings')

    if 'error' in api_call['message']:
        flash(api_call['message']['error'])
        return redirect(request.referrer) or redirect(url_for(default_url))

    return render_template(
        'settings.html',
        title='Settings',
        year=datetime.datetime.now().year,
        settings=api_call['message']
    )


@app.route('/store_settings', methods=['GET', 'POST'])
@login_required
def store_settings(default_url='settings'):
    # Check the request method and the database for data #
    if request.method != 'POST':
        error = 'Bad request type: ' + request.method
    else:
        api_call = make_api_callback('api_function', 'store_settings')
        error = api_call['message']

    flash(error)
    return redirect(request.referrer) or redirect(url_for(default_url))


@app.route('/store_aliases', methods=['GET', 'POST'])
@login_required
def store_aliases(default_url='settings'):
    # Check the request method and the database for data #
    if request.method != 'POST':
        error = 'Bad request type: ' + request.method
    else:
        api_call = make_api_callback('api_function', 'store_aliases')
        error = api_call['message']

    flash(error)
    return redirect(request.referrer) or redirect(url_for(default_url))


@app.route('/articles')
@login_required
def articles():
    # Renders the articles page, with a list of ALL the articles.
    api_call = make_api_callback('api_function', 'get_articles')

    if 'user' not in api_call['message']:
        api_call['message'] = {
            'user': [],
            'others': [],
        }

    return render_template(
        'articles.html',
        title='Articles for ' + session['user']['name'],
        year=datetime.datetime.now().year,
        articles=api_call['message']
    )


@app.route('/extract')
@login_required
def extract(default_url='home'):
    # Makes the Google Scholar Articles extraction
    flash("Extraction in progress")
    api_call = make_api_callback('api_function', 'extract_articles')

    # TODO Hacer algo, como un evento/callback para que espere antes de devolver el mensaje de error o finalización
    if api_call['message'] is None:
        flash("Extraction schedule Failed")
    else:
        flash("Extraction Started")

        # TODO create an event listener to show when the job is done
        # TODO you can use the jobID received in api_call['message'] to make the API send an event when the job is done

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
    api_call = make_api_callback('api_public', 'server_info')

    return render_template(
        'about.html',
        title='About',
        year=datetime.datetime.now().year,
        db_name=api_call['message']['database'],
        comunitacion_protocol=api_call['message']['communication_protocol'],
        scheduler_store=api_call['message']['scheduler_store'],
        scheduler_status=api_call['message']['scheduler_status']
    )
