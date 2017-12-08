"""
Data crawler for the diferent types of requests
"""

def create_crawler(user):
    # Creates a crawler that will do the extraction and processing tasks
    from . import Crawler

    return Crawler(user)
