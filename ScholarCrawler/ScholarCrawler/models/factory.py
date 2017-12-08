"""
Factory for the different types of databases.
"""

def create_database_connection(name, settings):
    """Creates a databases from its name and settings. The settings
    is a dictionary where the keys are different for every type of databases.
    See each database for details on the required settings."""
    if name == 'mongodb':
        from .mongodb import Database
    elif name == 'memory':
        from .memory import Database
    else:
        raise ValueError('Unknown database.')

    return Database(settings)
