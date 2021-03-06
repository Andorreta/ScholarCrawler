"""
Data crawler for the different types of requests
"""

import os
import datetime
import shutil


# Create a Crawler object to make the data extraction or processing
def create_crawler(user_data, desired_crawler):
    # Creates a crawler that will do the extraction and processing tasks
    crawler = Crawler

    # Select the desired crawler for the extraction
    if desired_crawler == 'googleScholarArticles' or desired_crawler == 'googleScholarArticles-cli':
        from crawler.googleScholarArticles import GoogleScholarArticles
        crawler = GoogleScholarArticles

    return crawler(user_data)


# Create a crawler object and extract the data
def create_crawler_and_extract(user_data, desired_crawler):
    return create_crawler(user_data, desired_crawler).data_extraction()


class Crawler(object):
    crawler_id = 'generalCrawler'

    # Extraction class to get the data user = system user
    def __init__(self, user_data):
        self.userArr = user_data

        # Set the extraction data save directories
        directory = os.path.dirname(__file__)
        self.tempDir = os.path.join(directory, 'storage/extractionTmp/' + self.crawler_id + '-' + user_data['id'] + '/')

        # Clean the Temp directory before starting a new download (Remove it to have a clean download)
        shutil.rmtree(self.tempDir, ignore_errors=True)

        # Create the temp directory
        os.makedirs(os.path.dirname(self.tempDir), exist_ok=True)
        self.extractionZip = os.path.join(directory, 'storage/extraction/' + self.crawler_id + '-' + user_data['id'] +
                                          '-' + str(datetime.datetime.now()))

    # Clean the temp files before quitting
    def __del__(self):
        self.delete_temp_file()

    # Zip the downloaded files and delete de temp files dir
    def delete_temp_file(self):
        shutil.make_archive(self.extractionZip, 'zip', self.tempDir)
        shutil.rmtree(self.tempDir, ignore_errors=True)

    def crawler_extract_process(self):
        pass

    # Override this method to make the data extraction
    def data_extraction(self):
        pass

    # Override this method to make the data processing
    def data_process(self, html_source):
        pass

    # Save the downloaded data into the HDD
    def save_source_to_file(self, source, file_path):
        with open(file_path, 'wb') as file:
            file.write(source.content)

    def extract_page(self, parameters):
        from requests import Request, Session
        from random import randint
        from time import sleep

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

        # Set the request Headers
        headers = parameters['headers'] if 'headers' in parameters else None

        # GET Parameters
        params = parameters['params'] if 'params' in parameters else None

        # Request Body for 'x-url-encoded' parameters
        data = parameters['data'] if 'data' in parameters else None

        # Set the request Cookies
        cookies = parameters['cookies'] if 'cookies' in parameters else None

        # Set the request PoolManager
        proxy = parameters['proxy'] if 'proxy' in parameters else None

        # Set the max retries number
        max_retries = parameters['retries'] if 'retries' in parameters else 1
        retries_wait_range = parameters['retries_wait_range'] if 'retries_wait_range' in parameters else [3, 5]
        current_retry = 1
        html_source = None

        # Prepare the desired Request and make the download
        session = Session()

        # html_source = requests.request('GET', url, headers=headers, proxies=self.proxies, cookies=self.cookieJar)
        desired_request = Request(parameters['requestType'], parameters['url'], headers=headers, params=params,
                                  data=data, cookies=cookies)

        prepared_request = desired_request.prepare()

        error = {
            'error': True,
            'error_message': 'First request',
        }

        while error['error'] and current_retry <= max_retries:
            html_source = session.send(prepared_request, proxies=proxy)

            # Check for error after the data download
            error = self.extraction_error_check(html_source)
            if error['error']:
                if current_retry == max_retries:
                    filename = 'error-' + parameters['filename']
                else:
                    sleep(randint(retries_wait_range[0], retries_wait_range[1]))
                    filename = 'retry-' + str(current_retry) + '-' + parameters['filename']
            else:
                filename = parameters['filename']

            # Save the downloaded data into the HDD
            self.save_source_to_file(html_source, os.path.dirname(self.tempDir) + '/' + filename)

            # Increase the request number and sleep a random time from the range
            current_retry = current_retry + 1

        return html_source

    # Checks for possible errors in the download
    def extraction_error_check(self, html_source):
        if html_source.status_code >= 400:
            return {
                'error': True,
                'error_message': 'Download error',
            }

        return {
            'error': False,
            'error_message': '',
        }

    # Function to iterate through a list of function names to get a String
    def find_version_text(self, version_list, source, params=None):
        for version in version_list:
            function = getattr(self, version)

            text = function(source, params)
            if isinstance(text, str) and text is not '':
                return text

        return None

    # Function to iterate through a list of function names to get a List/dictionary
    def find_version_array(self, version_list, source, params=None):
        for version in version_list:
            function = getattr(self, version)

            array = function(source, params)
            if isinstance(array, (list, dict)) and array:
                return array

        return None
