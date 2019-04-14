"""
Repository of polls that uses in-memory objects, no serialization.
Used for testing only.
"""

from .factory import *


class Database(Database):
    """In-Memory database."""
    def __init__(self, settings):
        """Initializes the repository. Note that settings are not used."""
        self.name = 'In-Memory (DISABLED)'


class Scheduler(Scheduler):
    # In-Memory Scheduler
    def __init__(self, settings):
        self.name = 'In-Memory'

        # Execute the parent method to obtain the default values
        super(Scheduler, self).__init__(settings)
