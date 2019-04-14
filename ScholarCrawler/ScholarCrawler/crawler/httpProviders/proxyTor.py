"""
HTTP Provider for the Tor Proxy
"""


class ProxyTor(object):
    controller = None
    defaults = {}

    def __init__(self, params=None):
        from ScholarCrawler import app

        # Get the default control values
        self.defaults = app.config['TOR_SETTINGS']

        # Override default values with the ones specified in the params
        self.defaults['protocol'] = params['protocol'] if params is not None and 'protocol' in params else \
            self.defaults['protocol']
        self.defaults['ip'] = params['address'] if params is not None and 'address' in params else self.defaults['ip']
        self.defaults['port'] = params['port'] if params is not None and 'port' in params else self.defaults['port']
        self.defaults['control_port'] = params['control_port'] if params is not None and 'control_port' in params else \
            self.defaults['control_port']
        self.defaults['control_pass'] = params['password'] if params is not None and 'password' in params else \
            self.defaults['control_pass']

        self.controller = self.connect_tor_control_port(params)
        if not self.controller:
            self.__del__()

    def __del__(self):
        if self.controller:
            self.controller.close()

    # Connect to the Tor control Port
    def connect_tor_control_port(self, params=None):
        import stem
        from stem import control

        # Define the variables that will be used
        address = params['address'] if params is not None and 'address' in params else self.defaults['ip']
        control_port = params['control_port'] if params is not None and 'control_port' in params else self.defaults[
            'control_port']
        password = params['password'] if params is not None and 'password' in params else self.defaults['control_pass']

        try:
            controller = control.Controller.from_port(address=address, port=control_port)
        except stem.SocketError as error:
            print('Unable to connect to tor on %s:%s %s' % (address, control_port, error))
            return None

        try:
            controller.authenticate()
        except stem.connection.MissingPassword:
            try:
                controller.authenticate(password=password)
            except stem.connection.PasswordAuthFailed:
                print('Unable to authenticate to Control Port, password is incorrect\n')
                return None
        except stem.connection.AuthenticationFailure as error:
            print('Unable to connect to Control Port: %s:%s %s' % (address, control_port, error))
            return None

        return controller

    # Sets the data to establish a TOR proxy connection
    def set_connection(self, params=None):
        if self.controller is None:
            return None

        status = self.check_tor_status()
        return None if status is None else {
            'http': self.defaults['protocol'] + '://' + self.defaults['ip'] + ':' + str(self.defaults['port']) + '/',
            'https': self.defaults['protocol'] + '://' + self.defaults['ip'] + ':' + str(self.defaults['port']) + '/',
        }

    # Standard function to change the Proxy Exit IP
    def rotate_ip(self, params=None):
        return self.change_tor_identity()

    # Send a Signal to Tor to create new circuits
    def change_tor_identity(self):
        from stem import Signal
        from time import sleep

        if self.controller is None:
            return None

        # print('Old Ip: ' + self.get_current_ip())  # TODO Test to view Output IP

        self.controller.signal(Signal.NEWNYM)

        # Sleep a little to give time to create a new circuit
        sleep(5)

        # print('New Ip: ' + self.get_current_ip())  # TODO Test to view Output IP

        return self.check_tor_status()

    # Function to check the connection status
    def check_tor_status(self):
        if self.controller is None:
            return None

        # Get the bootStrap phase
        response = self.controller.get_info("status/bootstrap-phase")

        return True if response.find('SUMMARY="Done"') > 0 else False

    def get_current_ip(self):
        import requests

        session = requests.session()

        # TO Request URL with SOCKS over TOR
        session.proxies = {
            'http': 'socks5h://' + self.defaults['ip'] + ':' + str(self.defaults['port']),
            'https': 'socks5h://' + self.defaults['ip'] + ':' + str(self.defaults['port']),
        }

        try:
            response = session.get('http://httpbin.org/ip')
        except Exception as e:
            print(str(e))
        else:
            return response.text
