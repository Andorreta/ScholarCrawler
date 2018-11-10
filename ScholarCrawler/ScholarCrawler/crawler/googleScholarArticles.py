"""
Package for the crawler.
"""

from .crawlerGeneral import *

import re
from requests import cookies

from fake_useragent import UserAgent
from bs4 import BeautifulSoup

from settings import REPOSITORY_NAME, REPOSITORY_SETTINGS


class GoogleScholarArticles(Crawler):
    crawler_id = 'googleScholarArticles'

    def __init__(self, user_data):
        super().__init__(user_data)

        self.domain = 'scholar.google.com'
        self.scholarUser = user_data['scholarUser']
        self.scholarAliases = user_data['scholarAliases']
        self.lastRequestUrl = ''
        self.mongoId = user_data['id']
        self.user = user_data['user']
        self.cookieJar = cookies.RequestsCookieJar()
        self.pages = 1

    # Make the articles extraction
    # TODO dividir para que separe los articulos en 2 colecciones. La temporal se va a borrar antes de la extraccion.
    def data_extraction(self):
        # Start the data extraction
        articles_count = 0
        url = 'initial'

        print('\nScholar main page Crawler for: ' + self.scholarUser + '\n')  # TODO Test

        while url is not None:
            # Generate the query Parameters
            query_parameters = self.generate_query(url)

            # Check possible errors withe the proxy
            if 'proxy' in query_parameters and query_parameters['proxy'] is None:
                return 'Process aborted. Proxy connection failure'

            # Download the data
            html_source = self.extract_page(query_parameters)  # Download the page and save it in the tempDir

            # process the downloaded data
            data = self.data_process(html_source)

            # Check if the articles contain the user as author
            if data['user'] is not None:
                url = self.get_next_page_url(html_source.content)  # get next page url
                # time.sleep(randint(10, 25))  # Sleep some time (between 10 and 25 seconds) to avoid a captcha page
            else:
                url = None

            self.pages = self.pages + 1
            articles_count += len(list(data['user'])) + len(list(data['others']))

            # TODO Tests
            print('    Articles processed: ' + str(len(list(data['user']))))
            if articles_count >= 200 or self.pages >= 20:
                url = ''

        # Zip the extracted data and move it to the extraction DIR
        shutil.make_archive(self.extractionZip, 'zip', self.tempDir)

        # Remove the temporary folder
        shutil.rmtree(self.tempDir, ignore_errors=True)

        # Return the job statistics
        return 'Process finished. Articles: ' + str(articles_count)

    # Function to generate the query parameters
    def generate_query(self, url=None):
        return {
            'url': self.generate_articles_url(),
            'params': self.generate_articles_get_parameters(url),
            'headers': self.generate_articles_headers(),
            'proxy': self.generate_articles_proxy(),
            'filename': self.generate_articles_filename(),
            'retries': 3,
            'retries_wait_range': [6, 10],
        }

    # Function to generate the articles extraction Url
    def generate_articles_url(self):
        return 'https://' + self.domain + '/scholar'

    # Function to generate the articles extraction GET Parameters
    def generate_articles_get_parameters(self, url=None):
        if url is None or url is 'initial':
            return {
                'q': '"' + self.scholarUser + '"',
                'hl': 'en',
                'btnG': 'Search Scholar',
                'as_sdt': '0,5',
                'as_sdtp': '',
                'lookup': '0'
            }
        else:
            # Parse the parameters of the url and return them
            from urllib.parse import urlparse, parse_qs
            return parse_qs(urlparse(url).query)

    # Function to generate some random headers
    def generate_articles_headers(self):
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

    # Function to generate the Proxy Settings (Proxy settings)
    def generate_articles_proxy(self):
        from .httpProviders.proxyTor import ProxyTor
        return ProxyTor().set_connection()

    # Function to generate the filename
    def generate_articles_filename(self, extension='.html'):
        return 'articles-' + self.mongoId + '-page-' + str(self.pages) + '-' +\
               str(datetime.datetime.now().timestamp()) + extension

    """
    Data Processing Part
    """

    # Data processing
    def data_process(self, html_source):
        # Import the factory
        from models.factory import connect_to_database

        # Check if we got an error during the extraction
        if 'error' in html_source:
            data = {
                'user': None,
                'others': None,
            }
        else:
            # Process the page to get the articles
            data = self.process_page(html_source.content)

            # Add the user articles to the DB
            if data['user'] is not None:
                db = connect_to_database(REPOSITORY_NAME, REPOSITORY_SETTINGS)
                db.add_new_articles(self.mongoId, data['user'])

            # Add the user articles to the DB
            if data['user'] is not None:
                db = connect_to_database(REPOSITORY_NAME, REPOSITORY_SETTINGS)
                db.add_new_articles_others(self.mongoId, data['others'])

        return data

    # Process the Google Scholar articles page
    def process_page(self, html_source):
        output = {
            'user': [],
            'others': [],
        }

        # Load the DOM Crawler and filter the articles from the HTML
        soup = BeautifulSoup(html_source, 'html5lib')
        articles = soup.select('.gs_r')

        for article in articles:
            # print('   Next article: ' + article.get_text()) # TODO Test
            data = self.process_article(str(article))

            # Add the data to it's corresponding group
            if data is not None and 'authors' in data:
                output['user'].append(data) if self.has_author(data) else output['others'].append(data)

        return output

    # Process an article
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
        if not article['authors']:
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
            regex = re.compile('\s(\d{4})\s-')
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

        # print('   Article: ' + str(article))  # TODO Test output to debug the code
        return article

    # TODO cambiar esto para que no añada el domain. De ese modo se puede reusar el crawler para otros dominios distintos
    def get_next_page_url(self, html_source):
        soup = BeautifulSoup(html_source, 'html5lib')
        url = soup.select('#gs_n td[align~=left] > a')

        if 0 in url and 'href' in url[0] and url[0]['href'] is not None:
            url = 'https://' + self.domain + url[0]['href']

        print('   Next Url: ' + str(url))  # TODO Test

        return str(url)

    # Check if the article is from the user
    def has_author(self, data):
        for author in data['authors']:
            for alias in self.scholarAliases:
                if alias in author:
                    return True

        return False

        # Checks for possible errors in the download

    def extraction_error_check(self, html_source):
        error = super().extraction_error_check(html_source)

        if not error['error']:
            # Check if there're captchas in the HTML
            captchas = re.compile('gs_captcha_f', re.IGNORECASE)
            if captchas.match(html_source.text):
                # Rotate the IP
                from.httpProviders.proxyTor import ProxyTor
                ProxyTor().rotate_ip()
                error = {
                    'error': True,
                    'error_message': 'Captchas Detected',
                }

        return error
