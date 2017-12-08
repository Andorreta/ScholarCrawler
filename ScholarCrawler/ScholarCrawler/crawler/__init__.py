"""
Package for the crawler.
"""

import json, urllib3, re, time
from random import randint
from os import path
from flask import jsonify
from urllib.parse import urlencode
from bs4 import BeautifulSoup

from ScholarCrawler.models import DataNotFound
from ScholarCrawler.models.factory import create_database_connection
from ScholarCrawler.settings import REPOSITORY_NAME, REPOSITORY_SETTINGS, API_NAME, API_VERSION

class Crawler(object):
    # Disable urllib3 insecure connection warnings
    urllib3.disable_warnings()

    # Extraction class to get the data user = system user
    def __init__(self, user):
        self.mongoId = user['id']
        self.user = user['user']
        self.scholarUser = user['scholarUser']
        self.scholarAliases = user['scholarAliases']
        self.html_source = urllib3.PoolManager()
        self.tempDir = './storage/extractionTmp/' + user['id'] + '/'
        self.extractionDir = './storage/extraction/' + user['id'] + '/'

    # Do the extraction process
    def extract(self):
        pages = 1
        articles = []
        data = []
        query = urlencode({'q' : '"' + self.scholarUser + '"', 'hl': 'en', 'btnG': 'Search Scholar', 'as_sdt': '0,5', 'as_sdtp': '', 'lookup': '0'})
        url = 'https://scholar.google.com/scholar?' + query
        print('\nScholar main page Crawler for: ' + self.scholarUser + '\n')  # Test
        while (url != '' and len(articles) < 10):
            html_source = self.extract_page(url) # Extract a page

            # Save the downloaded data into the HDD
            with open(self.tempDir + 'page-' + str(pages) + '.html', 'w') as file:
                file.write(html_source.data)

            # process the downloaded data
            data = self.process_page(html_source.data)
            articles.extend(data)
            # Check if the articles contain the user as author
            if self.has_author(data):
                url = self.get_next_page_url(html_source.data) # get next page url
                time.sleep(randint(10, 25)) # Sleep some time (between 10 and 25 seconds) to avoid a captcha page
            else:
                url = ''
            pages = pages + 1
            print('    Articles: ' + str(len(articles)))  # Test
        # Add the articles to the DB
        if articles != []:
            db = create_database_connection(REPOSITORY_NAME, REPOSITORY_SETTINGS)
            db.add_new_articles(self.mongoId, articles)

        # Zip the extracted data and move it to the extraction DIR

        # Return the job statistics
        return jsonify({"name" : API_NAME, "version" : API_VERSION, "Function" : "extract", "message" : "Process finished", "Articles" : str(len(articles))})

    # Data extraction
    def extract_page(self, url):
        print('   Url: ' + url)  # Test
        return urllib3.PoolManager().request('GET', url)

    # Data processing
    def process_page(self, html_source):
        output = []
        soup = BeautifulSoup(html_source, 'html.parser')
        articles = soup.select('.gs_r')
        for article in articles:
            #print('   Next article: ' + article.get_text())
            data = self.process_article(str(article))
            if data != None:
                output.append(data)
        return output

    def process_article(self, articleSource):
        soup = BeautifulSoup(articleSource, 'html.parser')
        article = {'articleId':'', 'title':'', 'date':'', 'source':'', 'description':'', 'quotes':0, 'versions':0, 'related':'', 'authors':[]}

        # Get the Article title
        titles = soup.select('.gs_ri > .gs_rt > a')
        for title in titles:
            article['title'] = title.get_text()
        # Check if we got the user profile field or an article
        if article['title'] == '':
            return None

        # Get the authors
        authors = soup.select('.gs_ri > .gs_a > a')
        for author in authors:
            article['authors'].append(author.get_text())

        # Check if we got the user profile field or an article
        if not article['authors'] or not set(article['authors']).isdisjoint(self.scholarAliases):
            return None

        # Get the article Id
        articleId = soup.select('.gs_r')
        if len(articleId) > 0:
            article['articleId'] = articleId[0]['data-cid']

        # Get the Article description
        descriptions = soup.select('.gs_ri > .gs_rs')
        for description in descriptions:
            article['description'] = description.get_text()

        # Get the article date
        dates = soup.select('.gs_ri > .gs_a')
        for date in dates:
            regex = re.compile('\s(\d{4})\s\-')
            article['date'] = str(regex.findall(date.get_text())[0])

        # Get the source URL
        sources = soup.select('.gs_ri > .gs_rt > a')
        for source in sources:
            article['source'] = source['href']

        # Get the article bottom line
        bottomline = soup.select('.gs_ri > .gs_fl > a')
        for part in bottomline:
            # Find how many times has been quoted
            regex = re.compile('Cited by\s(\d+)', re.IGNORECASE)
            if regex.match(part.get_text()):
                article['quotes'] = str(regex.match(part.get_text())[1])
                continue

            # Get the related articles URL
            if part.get_text().find('Related articles') != -1:
                article['related'] = 'https://scholar.google.com' + str(part['href'])
                continue

            # Get the other versions
            regex = re.compile('All\s(\d+)\sversions', re.IGNORECASE)
            if regex.match(part.get_text()):
                article['versions'] = str(regex.match(part.get_text())[1])
                continue

        #print('   Article: ' + str(article)) # Test
        return article

    def get_next_page_url(self, html_source):
        soup = BeautifulSoup(html_source, 'html.parser')
        url = soup.select('#gs_n td[align~=left] > a')
        if url != []:
            url = 'https://scholar.google.com' + url[0]['href']
        print('   Next Url: ' + str(url)) # Test
        return str(url)

    # Check if the article is from the user
    def has_author(self, data):
        for article in data:
            for author in article['authors']:
                for alias in self.scholarAliases:
                    if alias not in author:
                        return True
        return False