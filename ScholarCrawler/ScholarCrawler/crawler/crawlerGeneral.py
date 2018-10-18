"""
Data crawler for the different types of requests
"""

import urllib3
import os
import datetime


# Create a Crawler object to make the data extraction or processing
def create_crawler(user_data, desired_crawler):
    # Creates a crawler that will do the extraction and processing tasks
    crawler = Crawler

    # TODO Poner un switch que cargue el crawler necesario según lo que se le mande como segundo parametro.
    # TODO Un IF-ELSE es muy chapucero... Si se hace, se hace bien
    if desired_crawler == 'googleScholarArticles':
        from crawler.googleScholarArticles import GoogleScholarArticles
        crawler = GoogleScholarArticles

    return crawler(user_data)


# Create a crawler object and extract the data
def create_crawler_and_extract(user_data, desired_crawler):
    return create_crawler(user_data, desired_crawler).data_extraction()


class Crawler(object):
    # Disable urllib3 insecure connection warnings
    urllib3.disable_warnings()
    crawler_id = 'generalCrawler'

    # Extraction class to get the data user = system user
    def __init__(self, user_data):
        self.userArr = user_data

        # Set the extraction data save directories
        directory = os.path.dirname(__file__)
        self.tempDir = os.path.join(directory, 'storage/extractionTmp/' + self.crawler_id + '-' + user_data['id'] + '/')
        os.makedirs(os.path.dirname(self.tempDir), exist_ok=True)
        self.extractionZip = os.path.join(directory,
                                          'storage/extraction/' + self.crawler_id + '-' + user_data['id'] + '-' +
                                          datetime.datetime.now().strftime('%Y%m%d'))

    # Override this method to make the data extraction
    def data_extraction(self):
        pass

    # Override this method to make the data extraction
    def data_process(self, html_source):
        pass

    # Save the downloaded data into the HDD
    def save_source_to_file(self, source, file_path):
        with open(file_path, 'wb') as file:
            file.write(source.content)

    def extract_page(self, parameters):
        from requests import Request, Session

        error = {
            'error': False,
            'error_message': '',
        }

        # Check if we have an url and filename
        if 'url' not in parameters:
            return {
                'error': True,
                'error_message': 'No URL in the parameters',
            }

        if 'filename' not in parameters:
            return {
                'error': True,
                'error_message': 'No FILENAME in the parameters',
            }

        # print('   Url: ' + parameters['url'])  # TODO Test output to debug the code

        if 'requestType' not in parameters:
            parameters['requestType'] = 'GET'

        if 'headers' not in parameters:
            headers = parameters['headers']
        else:
            headers = None

        # GET Parameters
        if 'params' in parameters:
            params = parameters['params']
        else:
            params = None

        # Request Body for 'x-url-encoded' parameters
        if 'data' in parameters:
            data = parameters['data']
        else:
            data = None

        if 'cookies' in parameters:
            cookies = parameters['cookies']
        else:
            cookies = None

        if 'proxy' in parameters:
            proxy = parameters['proxy']
        else:
            proxy = urllib3.PoolManager()

        if 'retries' in parameters:
            retry_number = parameters['retries']
        else:
            retry_number = 1

        # Prepare the desired Request and make the download
        session = Session()

        # html_source = requests.request('GET', url, headers=headers, proxies=self.proxies, cookies=self.cookieJar)
        desired_request = Request(parameters['requestType'], parameters['url'], headers=headers, params=params,
                                  data=data, cookies=cookies)
        prepared_request = desired_request.prepare()

        html_source = session.send(
            prepared_request,
            proxies=proxy
        )

        # TODO Añadir error check
        if html_source.status_code >= 400:
            error['error'] = True
            error['error_message'] = 'Download error'

        if error['error']:
            parameters['filename'] = parameters['filename'] + 'retry-' + str(retry_number) + '-'

        # Save the downloaded data into the HDD
        self.save_source_to_file(html_source, os.path.dirname(self.tempDir) + '/' + parameters['filename'])

        return html_source
