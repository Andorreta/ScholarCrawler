"""
Package to extract the Google Scholar data using cli tools (like curl, requests,...)
"""

import re
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

from .crawlerGeneral import *


class GoogleScholarArticles(Crawler):
    crawler_id = 'googleScholarArticles'

    def __init__(self, user_data):
        from requests import cookies

        super().__init__(user_data)

        self.domain = 'scholar.google.es'
        self.scholarUser = user_data['scholarUser']
        self.scholarAliases = user_data['scholarAliases']
        self.unusedScholarAliases = []
        self.lastRequestUrl = ''
        self.repoUserId = user_data['id']
        self.user = user_data['user']
        self.cookieJar = cookies.RequestsCookieJar()
        self.pages = 1

    # Make the articles extraction
    def data_extraction(self):
        # Start the data extraction
        articles_count = 0
        url = None
        continue_extraction = True

        # TODO Test message for debugging
        print('\nScholar Crawler for: ' + self.scholarUser + '\n')

        # Extract the main portal page
        query_parameters = self.generate_main_page_query()
        html_source = self.extract_page(query_parameters)
        self.lastRequestUrl = query_parameters['url']

        # Extract the NID generation page
        query_parameters = self.generate_nid_query()
        html_source = self.extract_page(query_parameters)
        self.lastRequestUrl = query_parameters['url']

        while continue_extraction:
            # Generate the query Parameters
            query_parameters = self.generate_query(url)

            # Check possible errors withe the proxy
            if 'proxy' in query_parameters and query_parameters['proxy'] is None:
                return 'Process aborted. Proxy connection failure'

            # Download the page and save it in the tempDir
            html_source = self.extract_page(query_parameters)
            self.lastRequestUrl = query_parameters['url']

            # process the downloaded data
            data = self.data_process(html_source)

            # Check if the articles contain the user as author
            if data is not None and 'articles' in data and data['articles'] is not None:
                # get next page url
                url = self.get_next_page_url(html_source.content)

                self.pages = self.pages + 1
                articles_count += len(list(data['articles']))

                # print('   Next Url: ' + str(url))  # TODO Test
                # print('    Articles processed: ' + str(len(list(data['articles']))))  # TODO Tests

            else:
                url = ''

            # TODO Tests (Limit the max number of extractions to avoid a Google Ban/Captcha)
            if articles_count >= 200 or self.pages >= 20:
                continue_extraction = False
            else:
                # Check if the URL is valid
                continue_extraction = self.validate_url(url)

        # TODO Test message for debugging
        print('\nExtraction for ' + self.scholarUser + ' finished with ' + str(articles_count) + ' articles\n')

        # Return the job statistics
        return 'Process finished. Articles: ' + str(articles_count)

    # Function to check if the URL is valid, to continue the extraction
    def validate_url(self, url=None):
        if url is None:
            return False

        regex = re.compile('/scholar\?', re.IGNORECASE)

        return True if regex.match(url) else False

    # Function to generate the Data extraction query parameters
    def generate_query(self, url=None):
        return {
            'url': self.generate_articles_url(),
            'params': self.generate_articles_get_parameters(url),
            'headers': self.generate_articles_headers(),
            # 'proxy': self.generate_articles_proxy(),  # Uncomment to use Tor
            'filename': self.generate_articles_filename(),
            'retries': 3,
            'retries_wait_range': [6, 10],
        }

    # Function to generate the main page query parameters
    def generate_main_page_query(self):
        return {
            'url': self.generate_main_page_url(),
            'headers': self.generate_articles_headers(),
            # 'proxy': self.generate_articles_proxy(),  # Uncomment to use Tor
            'filename': self.generate_main_page_filename(),
            'retries': 2,
            'retries_wait_range': [6, 10],
        }

    # Function to generate the NID query parameters
    def generate_nid_query(self):
        return {
            'url': self.generate_nid_url(),
            'headers': self.generate_articles_headers(),
            # 'proxy': self.generate_articles_proxy(),  # Uncomment to use Tor
            'filename': self.generate_nid_filename(),
            'retries': 2,
            'retries_wait_range': [6, 10],
        }

    # Function to generate the articles extraction Url
    def generate_articles_url(self):
        return 'https://' + self.domain + '/scholar'

    # Function to generate the articles extraction Url
    def generate_main_page_url(self):
        return 'https://' + self.domain

    # Function to generate the articles extraction Url
    def generate_nid_url(self):
        return 'https://' + self.domain + '/gen_nid'

    # Function to generate the articles extraction GET Parameters
    def generate_articles_get_parameters(self, url=None):
        if url is None or url is 'initial':
            return {
                'q': self.scholarUser,
                'hl': 'all',
                'btnG': '',
                'as_sdt': '0,5',
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
            'Host': self.domain,
            'Referer': self.lastRequestUrl,
            'Upgrade-Insecure-Requests': '1'
        }

    # Function to generate the Proxy Settings (Proxy settings)
    def generate_articles_proxy(self):
        from .httpProviders.proxyTor import ProxyTor
        return ProxyTor().set_connection()

    # Function to generate the articles extraction query filename
    def generate_articles_filename(self, extension='.html'):
        return 'articles-' + self.repoUserId + '-page-' + str(self.pages) + '-' + \
               str(datetime.datetime.now().timestamp()) + extension

    # Function to generate the main page query  filename
    def generate_main_page_filename(self, extension='.html'):
        return 'mainPage-' + self.repoUserId + '-' + str(datetime.datetime.now().timestamp()) + extension

    # Function to generate the main page query  filename
    def generate_nid_filename(self, extension='.html'):
        return 'nidQuery-' + self.repoUserId + '-' + str(datetime.datetime.now().timestamp()) + extension

    """
    Data Processing Part
    """

    # Data processing
    def data_process(self, html_source):
        # Import the factory
        from models.factory import connect_to_database
        from ScholarCrawler import app

        # Check if we got an error during the extraction
        if 'error' in html_source:
            data = {
                'articles': None,
                'unknown_aliases': None,
            }
        else:
            # Process the page to get the articles
            data = self.process_page(html_source.content)

            # Add the user articles to the DB and the unknown/new aliases
            if data is not None:
                db = connect_to_database(app.config['REPOSITORY_NAME'], app.config['REPOSITORY_SETTINGS'])

                if 'articles' in data and data['articles'] is not None:
                    db.add_new_articles(self.repoUserId, data['articles'])

                if 'unknown_aliases' in data and data['unknown_aliases'] is not None:
                    db.add_new_unused_aliases(self.repoUserId, data['unknown_aliases'])

        return data

    # Process the Google Scholar articles page
    def process_page(self, html_source):
        output = {
            'articles': [],
            'unknown_aliases': [],
        }

        # Load the DOM Crawler and filter the articles from the HTML
        soup = BeautifulSoup(html_source, 'html5lib')
        articles = self.get_articles_list(soup)

        if articles is None:
            return None

        for article in articles:
            # print('   Next article: ' + article.get_text()) # TODO Test
            data = self.process_article(str(article))

            # Add the data to it's corresponding group
            if data is not None and 'authors' in data:
                output['articles'].append(data)

                # Add the missing unused authors to the list
                for author in data['authors']:
                    if author not in self.scholarAliases:
                        output['unknown_aliases'].append(author)

        return output

    # Process an article
    def process_article(self, article_source):
        soup = BeautifulSoup(article_source, 'html5lib')

        # Get the Article title
        title = self.get_article_title(soup)

        # Get the authors
        authors = self.get_article_authors(soup)

        # Check to know if we got the user profile field or an article
        if title is None or authors is None:
            return None

        article = {
            'articleId': self.get_article_id(soup),             # Get the article Id
            'title': title,
            'date': self.get_article_date(soup),                # Get the article date
            'source': self.get_article_source_url(soup),        # Get the source URL
            'description': self.get_article_description(soup),  # Get the Article description
            'quotes': self.get_article_quotes(soup),            # Find how many times has been quoted
            'versions': self.get_article_versions(soup),
            'related': self.get_article_related_urls(soup),     # Get the related articles URL
            'authors': authors
        }

        # print('   Article: ' + str(article))  # TODO Test output to debug the code
        return article

    # Get the articles list
    def get_articles_list(self, source, params=None):
        versions = [
            'get_articles_list_20181018',
        ]

        return self.find_version_array(versions, source, params)

    # Get the articles list (version: 2018-10-18)
    def get_articles_list_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        return source.select('.gs_r')

    # Get the article title
    def get_article_title(self, source, params=None):
        versions = [
            'get_article_title_20181018',
        ]

        return self.find_version_text(versions, source, params)

    # Get the article title (version: 2018-10-18)
    def get_article_title_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        titles = source.select('.gs_ri > .gs_rt > a')
        for title in titles:
            return title.get_text()
        return None

    # Get the article Authors
    def get_article_authors(self, source, params=None):
        versions = [
            'get_article_authors_20181018',
        ]

        return self.find_version_array(versions, source, params)

    # Get the article Authors (version: 2018-10-18)
    def get_article_authors_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        authors_list = []
        authors = source.select('.gs_ri > .gs_a > a')
        for author in authors:
            authors_list.append(author.get_text())

        return authors_list

    # Get the article id
    def get_article_id(self, source, params=None):
        versions = [
            'get_article_id_20181018',
        ]

        return self.find_version_text(versions, source, params)

    # Get the article id (version: 2018-10-18)
    def get_article_id_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        article_id = source.select('.gs_r')

        return article_id[0]['data-cid'] if len(article_id) > 0 and 'data-cid' in article_id[0].attrs else None

    # Get the article description
    def get_article_description(self, source, params=None):
        versions = [
            'get_article_description_20181018',
        ]

        return self.find_version_text(versions, source, params)

    # Get the article description (version: 2018-10-18)
    def get_article_description_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        descriptions = source.select('.gs_ri > .gs_rs')
        for description in descriptions:
            return description.get_text()
        return None

    # Get the article date
    def get_article_date(self, source, params=None):
        versions = [
            'get_article_date_20181018',
        ]

        return self.find_version_text(versions, source, params)

    # Get the article date (version: 2018-10-18)
    def get_article_date_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        dates = source.select('.gs_ri > .gs_a')
        for date in dates:
            regex = re.compile('\s(\d{4})\s-')
            return str(regex.findall(date.get_text())[0])
        return None

    # Get the article source url
    def get_article_source_url(self, source, params=None):
        versions = [
            'get_article_source_url_20181018',
        ]

        return self.find_version_text(versions, source, params)

    # Get the article source url (version: 2018-10-18)
    def get_article_source_url_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        sources_urls = source.select('.gs_ri > .gs_rt > a')
        for url in sources_urls:
            return url['href']
        return None

    # Get the article bottom line
    def get_article_bottom_line(self, source, params=None):
        versions = [
            'get_article_bottom_line_20181018',
        ]

        return self.find_version_array(versions, source, params)

    # Get the article bottom line (version: 2018-10-18)
    def get_article_bottom_line_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        return source.select('.gs_ri > .gs_fl > a')

    # Get the article quotes
    def get_article_quotes(self, source, params=None):
        versions = [
            'get_article_quotes_20190413',
            'get_article_quotes_20181018',
        ]

        text = self.find_version_text(versions, source, params)

        return int(text) if text is not None else 0

    # Get the article quotes (version: 2019-04-13)
    def get_article_quotes_20190413(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        bottom_line = self.get_article_bottom_line(source, params)

        if bottom_line is None or not bottom_line:
            return None

        regex = re.compile('Citado por\s*(\d+)', re.IGNORECASE)
        for part in bottom_line:
            if regex.match(part.get_text()):
                return str(regex.match(part.get_text())[1])

        return None

    # Get the article quotes (version: 2018-10-18)
    def get_article_quotes_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        bottom_line = self.get_article_bottom_line(source, params)

        if bottom_line is None or not bottom_line:
            return None

        regex = re.compile('Cited by\s(\d+)', re.IGNORECASE)
        for part in bottom_line:
            if regex.match(part.get_text()):
                return str(regex.match(part.get_text())[1])

        return None

    # Get the article related articles urls
    def get_article_related_urls(self, source, params=None):
        versions = [
            'get_article_related_urls_20190413',
            'get_article_related_urls_20181018',
        ]

        return self.find_version_text(versions, source, params)

    # Get the article related articles urls (version: 2019-04-13)
    def get_article_related_urls_20190413(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        bottom_line = self.get_article_bottom_line(source, params)

        if bottom_line is None or not bottom_line:
            return None

        for part in bottom_line:
            if part.get_text().find('Artículos relacionados') != -1:
                return 'https://' + self.domain + str(part['href'])

        return None

    # Get the article related articles urls (version: 2018-10-18)
    def get_article_related_urls_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        bottom_line = self.get_article_bottom_line(source, params)

        if bottom_line is None or not bottom_line:
            return None

        for part in bottom_line:
            if part.get_text().find('Related articles') != -1:
                return 'https://' + self.domain + str(part['href'])

        return None

    # Get the article versions
    def get_article_versions(self, source, params=None):
        versions = [
            'get_article_versions_20190413',
            'get_article_versions_20181018',
        ]

        text = self.find_version_text(versions, source, params)

        return int(text) if text is not None else 0

    # Get the article version (version: 2019-04-13)
    def get_article_versions_20190413(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        bottom_line = self.get_article_bottom_line(source, params)

        if bottom_line is None or not bottom_line:
            return None

        regex = re.compile('Las\s*(\d+)\s*versi', re.IGNORECASE)
        for part in bottom_line:
            if regex.match(part.get_text()):
                return str(regex.match(part.get_text())[1])

        return None

    # Get the article version (version: 2018-10-18)
    def get_article_versions_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            return None

        bottom_line = self.get_article_bottom_line(source, params)

        if bottom_line is None or not bottom_line:
            return None

        regex = re.compile('All\s*(\d+)\s*version', re.IGNORECASE)
        for part in bottom_line:
            if regex.match(part.get_text()):
                return str(regex.match(part.get_text())[1])

        return None

    # Get the next Page URL
    def get_next_page_url(self, source, params=None):
        versions = [
            'get_next_page_url_20181018',
        ]

        return self.find_version_text(versions, source, params)

    # Get the next Page URL (version: 2018-10-18)
    def get_next_page_url_20181018(self, source, params=None):
        if not isinstance(source, BeautifulSoup):
            source = BeautifulSoup(source, 'html5lib')

        url = source.select('#gs_n td[align~=left] > a')

        return url[0]['href'] if len(url) > 0 and 'href' in url[0].attrs and url[0]['href'] is not None else None

    # Checks for possible errors in the download
    def extraction_error_check(self, html_source):
        error = super().extraction_error_check(html_source)

        # Check if there're captcha in the HTML to Rotate the IP (Connect to a new Tor circuit)
        if "captcha" in html_source.text:
            from .httpProviders.proxyTor import ProxyTor
            ProxyTor().rotate_ip()
            error = {
                'error': True,
                'error_message': 'Captchas Detected',
            }

        return error
