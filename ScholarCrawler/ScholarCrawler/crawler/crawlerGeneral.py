"""
Data crawler for the different types of requests
"""

import urllib3
import certifi
import re
import os
import datetime
import shutil
import requests

from flask import jsonify
from urllib.parse import urlencode
from urllib3.contrib.socks import SOCKSProxyManager
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

from models.factory import create_database_connection
from settings import REPOSITORY_NAME, REPOSITORY_SETTINGS, API_NAME, API_VERSION, TOR_PORT, TOR_IP


def create_crawler(user):
    # Creates a crawler that will do the extraction and processing tasks
    from . import Crawler

    return Crawler(user)


class Crawler(object):
    # Disable urllib3 insecure connection warnings
    urllib3.disable_warnings()

    # Extraction class to get the data user = system user
    def __init__(self, user):
        self.userArr = user
        self.mongoId = user['id']
        self.user = user['user']
        self.scholarUser = user['scholarUser']
        self.scholarAliases = user['scholarAliases']
        self.lastRequestUrl = ''
        self.cookieJar = requests.cookies.RequestsCookieJar()
        self.proxies = {
            'http': 'socks5h://' + TOR_IP + ':' + str(TOR_PORT),
            'https': 'socks5h://' + TOR_IP + ':' + str(TOR_PORT),
        }

        # Set the extraction data save directories
        directory = os.path.dirname(__file__)
        self.tempDir = os.path.join(directory, 'storage/extractionTmp/' + user['id'] + '/')
        os.makedirs(os.path.dirname(self.tempDir), exist_ok=True)
        self.extractionZip = os.path.join(directory,
                                          'storage/extraction/' + user['id'] + '-' + datetime.datetime.now().strftime(
                                              '%Y%m%d'))

        # Set the default proxy settings for the requests poll manager
        certs_settings = {
            'cert_reqs': 'CERT_REQUIRED',
            'ca_certs': certifi.where()
        }
        self.html_source = SOCKSProxyManager('socks5://' + TOR_IP + ':' + str(TOR_PORT) + '/', **certs_settings)

    # Do the extraction process
    def extractyy(self):
        extracted_articles = Crawler(self.userArr)
        extracted_articles.extract()

    # Make the articles extraction
    def extract(self):
        # Start the data extraction
        pages = 1
        articles = []
        query = urlencode({'q': '"' + self.scholarUser + '"', 'hl': 'en', 'btnG': 'Search Scholar', 'as_sdt': '0,5',
                           'as_sdtp': '', 'lookup': '0'})
        url = 'https://scholar.google.com/scholar?' + query
        print('\nScholar main page Crawler for: ' + self.scholarUser + '\n')  # Test
        while url != '' and len(articles) < 5:  # Limit the number of articles to make some tests
            html_source = self.extract_page(url, pages)  # Download the page and save it in the tempDir

            # process the downloaded data
            data = self.process_page(html_source.content)
            articles.extend(data)
            # Check if the articles contain the user as author
            if self.has_author(data):
                url = self.get_next_page_url(html_source.content)  # get next page url
                #time.sleep(randint(10, 25))  # Sleep some time (between 10 and 25 seconds) to avoid a captcha page
            else:
                url = ''
            pages = pages + 1
            print('    Articles: ' + str(len(articles)))  # Test
        # Add the articles to the DB
        if articles is not []:
            db = create_database_connection(REPOSITORY_NAME, REPOSITORY_SETTINGS)
            db.add_new_articles(self.mongoId, articles)

        # Zip the extracted data and move it to the extraction DIR
        shutil.make_archive(self.extractionZip, 'zip', self.tempDir)

        # Remove the temporary folder
        shutil.rmtree(self.tempDir, ignore_errors=True)

        # Return the job statistics
        return jsonify({"name": API_NAME, "version": API_VERSION, "Function": "extract", "message": "Process finished",
                        "Articles": str(len(articles))})

    # Data extraction
    def extract_page(self, url, pages):
        print('   Url: ' + url)  # Test output to debug the code
        error = False
        error_message = ''
        headers = self.generate_headers()
        html_source = requests.get(url, headers=headers, proxies=self.proxies, cookies=self.cookieJar)

        # TODO Añadir error check
        if html_source.status_code >= 400:
            error = True
            error_message = 'Download error'

        if error:
            file_name = 'retry-1-'
        else:
            file_name = 'page-'

        # Save the downloaded data into the HDD
        self.save_source_to_file(html_source, os.path.dirname(self.tempDir) + '/' + file_name + str(pages))

        return html_source

    # Function to generate some random headers
    def generate_headers(self):
        return {
            'User-agent': UserAgent().random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Host': 'scholar.google.com',
            'Referer': self.lastRequestUrl,
            'Upgrade-Insecure-Requests': '1'
        }

    # Data processing
    def process_page(self, html_source):
        output = []
        soup = BeautifulSoup(html_source, 'html5lib')
        articles = soup.select('.gs_r')
        for article in articles:
            # print('   Next article: ' + article.get_text())
            data = self.process_article(str(article))
            if data is not None:
                output.append(data)
        return output

    def process_article(self, article_source):
        soup = BeautifulSoup(article_source, 'html.parser')
        article = {'articleId': '', 'title': '', 'date': '', 'source': '', 'description': '', 'quotes': 0,
                   'versions': 0, 'related': '', 'authors': []}

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
        article_id = soup.select('.gs_r')
        if len(article_id) > 0:
            article['articleId'] = article_id[0]['data-cid']

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
        bottom_line = soup.select('.gs_ri > .gs_fl > a')
        for part in bottom_line:
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

        # print('   Article: ' + str(article))  # Test output to debug the code
        return article

    def get_next_page_url(self, html_source):
        soup = BeautifulSoup(html_source, 'html.parser')
        url = soup.select('#gs_n td[align~=left] > a')
        if url is not []:
            url = 'https://scholar.google.com' + url[0]['href']
        print('   Next Url: ' + str(url))  # Test
        return str(url)

    def save_source_to_file(self, source, file_path, extension='.html'):
        # Save the downloaded data into the HDD
        with open(file_path + extension, 'wb') as file:
            file.write(source.content)

    # Check if the article is from the user
    def has_author(self, data):
        for article in data:
            for author in article['authors']:
                for alias in self.scholarAliases:
                    if alias not in author:
                        return True
        return False
