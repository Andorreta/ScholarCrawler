"""
Factory for the different types of databases.
"""


def connect_to_database(name, settings):
    """
    Creates a databases from its name and settings. The settings
    is a dictionary where the keys are different for every type of databases.
    See each database for details on the required settings. And the method fallback
    to the memory database in case the connection is unable to be set.
    """
    if name == 'mongodb':
        import models.mongodb
        database = models.mongodb.Database(settings)
        if database.check_connection():
            return database
        else:
            name = 'memory'

    if name == 'memory':
        import models.memory
        database = models.memory.Database(settings)
        return database

    raise ValueError('Unknown database.')


def create_scheduler_process(name, settings):
    """
    Creates a scheduler process defining the job store from its repository name and settings. The settings
    is a dictionary where the keys are different for every type of databases.
    See each model for details on the required settings. And the method fallback
    to the memory job store scheduler in case the connection is unable to be set.
    """
    if name == 'mongodb':
        import models.mongodb
        scheduler = models.mongodb.Scheduler(settings)
        if scheduler.check_connection():
            return scheduler
        else:
            name = 'memory'

    if name == 'memory':
        import models.memory
        return models.memory.Scheduler(settings)

    raise ValueError('Unknown Scheduler Type.')


class Database(object):
    # Check the connection to the desired database
    def check_connection(self):
        pass

    # Establish the connection to the desired collection/table/database
    def set_connection(self):
        pass

    # Returns all the users from the database
    def get_all_users(self):
        pass

    # Returns all the articles related to an user from the user collection
    def get_articles(self, user_id):
        pass

    # Returns all the articles related to an user from the others collection
    def get_articles_others(self, user_id):
        pass

    # Returns a user from the repository, using the mail
    def get_user_by_mail(self, user):
        pass

    # Adds a new user to the system
    def add_new_user(self, user):
        pass

    # Adds new articles to the user Collection
    def add_new_articles(self, user_id, articles):
        pass

    # Adds new articles to the others user Collection
    def add_new_articles_others(self, user_id, articles):
        pass


class Scheduler(object):
    job_stores = None
    executors = None
    job_defaults = None
    scheduler = None

    def __init__(self, settings=None):
        import atexit

        from pytz import utc

        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

        # Set the Scheduler config
        self.executors = {
            'default': ThreadPoolExecutor(20),
            'process_pool': ProcessPoolExecutor(5)
        }
        # Set the default job parameters
        self.job_defaults = {
            'coalesce': True,
            'max_instances': 1
        }
        # Register the Scheduler
        self.scheduler = BackgroundScheduler(jobstores=self.job_stores, executors=self.executors,
                                             job_defaults=self.job_defaults, timezone=utc)

        # Start the Scheduler
        self.scheduler.start()

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: self.scheduler.shutdown())

    # Check the connection to the desired scheduler job store
    def check_connection(self):
        pass

    def start_scheduler(self):
        self.scheduler.start()

    def stop_scheduler(self):
        self.scheduler.shutdown()

# TODO se puede cambiar el extract para que en lugar de hacer la extracción directamente,
# TODO cree un job y lo lance al instante y luego añadir un listener para que cuando haya acabado el job
# TODO mande un mensaje por pantalla para indicar que ya ha acabado la descarga (usando un flash)
    def add_scheduled_job(self, function_name, trigger=None, id=None, name=None, replace=True):
        pause = None

        # Check if we got all the desired values

        self.scheduler.add_job(func=function_name, trigger=trigger, id=id, name=name, replace_existing=replace)

    def add_one_time_job(self, function_name, func_args, user_id):
        from apscheduler.triggers.date import DateTrigger

        self.scheduler.add_job(func=function_name, trigger=DateTrigger(), kwargs=func_args,
                               name=user_id + '_onetime_job', replace_existing=True)


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