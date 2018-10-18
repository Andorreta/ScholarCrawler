"""
Repository that stores data in a MongoDB database.
"""

import pymongo

from flask import json
from bson.objectid import InvalidId
from bson.json_util import dumps

from .factory import *


# Creates a user object from an user document # TODO quitar?¿ Si....
def _user_from_doc(doc):
    return User(str(doc['_id']))


class Database(Database):
    # MongoDB database.
    def __init__(self, settings):
        """Initializes the repository with the specified settings dict.
        Required settings are:
         - MONGODB_HOST
         - MONGODB_DATABASE
         - MONGODB_COLLECTION
        """
        self.name = 'MongoDB'
        if 'MONGODB_HOST' in settings:
            self.host = settings['MONGODB_HOST']
        else:
            self.host = 'localhost'
        self.client = pymongo.MongoClient(self.host)

        if 'MONGODB_DATABASE' in settings:
            self.database = self.client[settings['MONGODB_DATABASE']]
        else:
            self.database = self.client['ScholarSettings']

        if 'MONGODB_COLLECTION' in settings:
            self.collection = self.database[settings['MONGODB_COLLECTION']]
        else:
            self.collection = self.database['Users']

    # Check the connection to the desired database
    def check_connection(self, max_delay=100):
        try:
            client = pymongo.MongoClient(self.host, serverSelectionTimeoutMS=max_delay)
            client.server_info()  # Make the server info request to make a connection to the server
        except pymongo.errors.ServerSelectionTimeoutError as err:
            print(err)
            return False
        return True

    # Establish the connection to the desired collection/table/database
    def set_connection(self):
        pass

    # Returns all the users from the database
    def get_all_users(self):
        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']
        docs = self.collection.find()
        users = [User(str(doc['_id'])) for doc in docs]
        return users

    # Returns a user from the repository, using the mail
    def get_user_by_mail(self, user):
        try:
            doc = self.collection.find_one({"mail": user})
            if doc is None:
                return 'userNotFound'
            else:
                return doc
        except InvalidId:
            raise DataNotFound()

    # Returns a user from the repository, using a Mongo Id
    def get_user_by_id(self, id):
        try:
            doc = self.collection.find_one({"_id": id})
            if doc is None:
                return 'userNotFound'
            else:
                return doc
        except InvalidId:
            raise DataNotFound()

    # Adds a new user to the system
    def add_new_user(self, user):
        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']

        try:
            self.collection.insert_one(user)
        except(InvalidId, ValueError):
            raise DataNotFound()

    # Adds new articles to the user Collection
    def add_new_articles(self, user_id, articles):
        collection = 'articles_' + user_id
        self.database = self.client['DataStorage']
        self.collection = self.database[collection]

        # Insert the articles to MongoDB
        try:
            for article in articles:
                self.collection.update({'articleId': article['articleId']}, article, upsert=True)
        except(InvalidId, ValueError):
            raise DataNotFound()

    # Adds new articles to the others user Collection
    def add_new_articles_others(self, user_id, articles):
        collection = 'articles_others_' + user_id
        self.database = self.client['DataStorage']
        self.collection = self.database[collection]

        # Insert the articles to MongoDB
        try:
            for article in articles:
                self.collection.update({'articleId': article['articleId']}, article, upsert=True)
        except(InvalidId, ValueError):
            raise DataNotFound()

    # Returns all the articles related to an user from the user collection
    def get_articles(self, user_id):
        docs = []
        collection = 'articles_' + user_id
        self.database = self.client['DataStorage']
        self.collection = self.database[collection]

        # Extract the data and Dump it to remove the BSON specific kirks
        for document in self.collection.find():
            docs.append(json.loads(dumps(document)))

        return docs

    # Returns all the articles related to an user from the others collection
    def get_articles_others(self, user_id):
        docs = []
        collection = 'articles_others_' + user_id
        self.database = self.client['DataStorage']
        self.collection = self.database[collection]

        # Extract the data and Dump it to remove the BSON specific kirks
        for document in self.collection.find():
            docs.append(json.loads(dumps(document)))

        return docs


# Class for the scheduler using MongoDB as Job Store
class Scheduler(Scheduler):
    def __init__(self, settings):
        from apscheduler.jobstores.mongodb import MongoDBJobStore

        """
            Initializes the repository with the specified settings dict.
            Required settings are:
             - SCHEDULER_HOST
             - SCHEDULER_DATABASE
             - SCHEDULER_COLLECTION
        """
        if 'SCHEDULER_HOST' in settings:
            self.host = settings['SCHEDULER_HOST']
        else:
            self.host = 'localhost'

        if 'SCHEDULER_DATABASE' in settings:
            database = settings['SCHEDULER_DATABASE']
        else:
            database = 'apscheduler'

        if 'SCHEDULER_COLLECTION' in settings:
            collection = settings['SCHEDULER_COLLECTION']
        else:
            collection = 'scheduler_jobs'

        client = pymongo.MongoClient(self.host)

        self.name = 'MongoDB'
        self.job_stores = {
            'default': MongoDBJobStore(database=database, collection=collection, client=client),
        }

        # Execute the parent method to obtain the default values
        super(Scheduler, self).__init__(settings)

    # Check the connection to the desired database
    def check_connection(self, max_delay=100):
        try:
            client = pymongo.MongoClient(self.host, serverSelectionTimeoutMS=max_delay)
            client.server_info()  # Make the server info request to make a connection to the server
        except pymongo.errors.ServerSelectionTimeoutError as err:
            print(err)
            return False
        return True
