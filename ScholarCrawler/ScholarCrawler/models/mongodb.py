"""
Repository that stores data in a MongoDB database.
"""

import pymongo

from flask import json
from bson.objectid import InvalidId
from bson.json_util import dumps

from .factory import *


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
        self.info = []

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
            self.info = client.server_info()
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
    def get_user_by_mail(self, user_mail):
        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']

        try:
            doc = self.collection.find_one({"mail": user_mail})
            if doc is None:
                return 'userNotFound'
            else:
                return doc
        except InvalidId:
            raise DataNotFound()

    # Returns a user from the repository, using a Mongo Id
    def get_user_by_id(self, user_id):
        from bson.objectid import ObjectId

        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']

        try:
            doc = self.collection.find_one({"_id": ObjectId(user_id)})
            if doc is None:
                return 'userNotFound'
            else:
                doc['_id'] = user_id
                return doc
        except InvalidId:
            raise DataNotFound()

    # Adds a new user to the system
    def add_new_user(self, user):
        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']

        try:
            self.collection.insert_one(self.add_data_time(user))
        except(InvalidId, ValueError):
            raise DataNotFound()

    # Updates an already existing user
    def update_user_by_id(self, user_id, user_data):
        from bson.objectid import ObjectId

        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']
        del user_data['_id']

        try:
            self.collection.update({"_id": ObjectId(user_id)}, self.add_data_time(user_data))
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
                self.collection.update({'articleId': article['articleId']}, self.add_data_time(article), upsert=True)
        except(InvalidId, ValueError):
            raise DataNotFound()

    # Updates the currently used user aliases
    def update_user_aliases(self, user_id, aliases):
        if aliases is None:
            return None

        user_data = self.get_user_by_id(user_id)

        if user_data == 'userNotFound':
            raise DataNotFound()

        # Update the currently used Aliases of the User
        user_data['scholarAliases'] = aliases
        self.update_user_by_id(user_id, user_data)

    # Updates the currently unused user aliases
    def update_unused_user_aliases(self, user_id, aliases):
        if aliases is None:
            return None

        user_data = self.get_user_by_id(user_id)

        if user_data == 'userNotFound':
            raise DataNotFound()

        # Update the currently used Aliases of the User
        user_data['unusedScholarAliases'] = aliases
        self.update_user_by_id(user_id, user_data)

    # Adds a new unused user alias
    def add_new_unused_aliases(self, user_id, aliases):
        if aliases is None:
            return None

        user_data = self.get_user_by_id(user_id)

        if user_data == 'userNotFound':
            raise DataNotFound()

        # Update the Unused Aliases of the User
        for alias in aliases:
            if alias not in user_data['unusedScholarAliases']:
                user_data['unusedScholarAliases'].append(alias)

        # Update the user in the repository
        self.update_user_by_id(user_id, user_data)

    # Get the user aliases
    def get_user_aliases(self, user_id):
        user_data = self.get_user_by_id(user_id)

        if user_data == 'userNotFound':
            raise DataNotFound()

        return user_data['scholarAliases']

    # Get the user unused aliases
    def get_user_unused_aliases(self, user_id):
        user_data = self.get_user_by_id(user_id)

        if user_data == 'userNotFound':
            raise DataNotFound()

        return user_data['scholarAliases']

    # Get the user assigned Scheduler Job IDs
    def get_user_job_ids(self, user_id):
        from bson.objectid import ObjectId

        self.database = self.client['ScholarSettings']
        self.collection = self.database['Users']

        try:
            doc = self.collection.find_one({"_id": ObjectId(user_id)})
            if doc is None:
                return 'userNotFound'
            else:
                return doc['schedulerJobs']
        except InvalidId:
            raise DataNotFound()

    # Adds a new Scheduler Job ID to the user
    def add_new_scheduler_job_id(self, user_id, scheduler_job_id):
        if scheduler_job_id is None:
            return None

        user_data = self.get_user_by_id(user_id)

        if user_data == 'userNotFound':
            raise DataNotFound()

        # Update the Scheduler Job Ids of the User
        if scheduler_job_id not in user_data['schedulerJobs']:
            user_data['schedulerJobs'].append(scheduler_job_id)

        # Update the user in the repository
        self.update_user_by_id(user_id, user_data)

    # Remove a Scheduler Job ID from the user
    def remove_scheduler_job_id(self, user_id, scheduler_job_id):
        if scheduler_job_id is None:
            return None

        user_data = self.get_user_by_id(user_id)

        if user_data == 'userNotFound':
            raise DataNotFound()

        # Update the Scheduler Job Ids of the User
        if scheduler_job_id in user_data['schedulerJobs']:
            user_data['schedulerJobs'].remove(scheduler_job_id)

        # Update the user in the repository
        self.update_user_by_id(user_id, user_data)

    # Returns all the articles related to an user from the user collection
    def get_articles(self, user_id):
        docs = {'user': [], 'others': []}
        collection = 'articles_' + user_id
        aliases = self.get_user_aliases(user_id)

        self.database = self.client['DataStorage']
        self.collection = self.database[collection]

        # Extract the data and Dump it to remove the BSON specific kirks
        for document in self.collection.find():
            doc = json.loads(dumps(document))
            doc['_id'] = doc['_id']['$oid']

            location = 'others'
            for alias in aliases:
                if doc['authors'] is not None and alias in doc['authors']:
                    location = 'user'
                    break

            # Divide the articles into 2 groups (the user ones an the others)
            docs[location].append(doc)

        return docs

    # Add a time to the documents to know the update and creation date
    def add_data_time(self, data):
        import datetime

        date = datetime.datetime.utcnow()

        # Add the creation date if it hasn't
        if 'creation_date' not in data:
            data['creation_date'] = date.strftime('%Y-%m-%d %H:%M:%S')

        # Update the data update Date
        data['update_date'] = date.strftime('%Y-%m-%d %H:%M:%S')

        return data


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
