"""
Package for the models.
"""


class User(object):
    # An user object for use in the Database
    def __init__(self, user=u''):
        # Initializes an user
        self.user = user


class Article(object):
    # An article object for use in the Database
    def __init__(self, article):
        # Initializes an article
        self.article = article


class DataNotFound(Exception):
    # Exception raised when the data object couldn't be retrieved from the database.
    pass
