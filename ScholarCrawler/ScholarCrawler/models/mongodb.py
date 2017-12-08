"""
Repository that stores data in a MongoDB database.
"""

from bson.objectid import InvalidId
from pymongo import MongoClient
from . import User, DataNotFound


def _user_from_doc(doc):
    # Creates a user object from the MongoDB user document.
    return User(str(doc['_id']))


class Database(object):
    # MongoDB database.
    def __init__(self, settings):
        """Initializes the repository with the specified settings dict.
        Required settings are:
         - MONGODB_HOST
         - MONGODB_DATABASE
         - MONGODB_COLLECTION
        """
        self.name = 'MongoDB'
        self.host = settings['MONGODB_HOST']
        self.client = MongoClient(self.host)
        self.database = self.client[settings['MONGODB_DATABASE']]
        self.collection = self.database[settings['MONGODB_COLLECTION']]

    def get_users(self):
        # Returns all the users from the database.
        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']
        docs = self.collection.find()
        users = [_user_from_doc(doc) for doc in docs]
        return users

    def get_articles(self, user_id):
        # Returns all the articles related to an user from the database.
        collection = 'Articles_' + user_id
        self.database = self.client['DataStorage']
        self.collection = self.database[collection]
        docs = self.collection.find()
        return docs

    def get_user(self, user):
        # Returns a user from the repository.
        try:
            doc = self.collection.find_one({"mail": user})
            if doc is None:
                return 'userNotFound'
            else:
                return doc
        except InvalidId:
            raise DataNotFound()

    def add_new_articles(self, user_id, articles):
        # Adds new articles to the user Collection
        collection = 'Articles_' + user_id
        self.database = self.client['DataStorage']
        self.collection = self.database[collection]

        # Insert the articles to Mongo
        try:
            for article in articles:
                self.collection.update({'articleId': article['articleId']}, article, upsert = True)
        except(InvalidId, ValueError):
            raise DataNotFound()
