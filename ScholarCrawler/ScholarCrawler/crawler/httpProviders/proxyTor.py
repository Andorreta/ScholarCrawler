"""
HTTP Provider for the Tor Proxy
"""


class ProxyTor(object):
    controller = None

    def __init__(self, params=None):
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
        from settings import TOR_PASSWORD, TOR_IP, TOR_CONTROL_PORT

        # Define the variables that will be used
        address = params['address'] if params is not None and 'address' in params else TOR_IP
        port = params['port'] if params is not None and 'port' in params else TOR_CONTROL_PORT
        password = params['password'] if params is not None and 'password' in params else TOR_PASSWORD

        try:
            controller = control.Controller.from_port(address=address,port=port)
        except stem.SocketError as error:
            print('Unable to connect to tor on %s:%s %s' % (address, port, error))
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
            print('Unable to connect to Control Port: %s:%s %s' % (address, port, error))
            return None

        return controller

    # Sets the data to establish a TOR proxy connection
    def set_connection(self, params=None):
        from settings import TOR_PORT, TOR_IP

        if self.controller is None:
            return None

        status = self.check_tor_status()
        return None if status is None else {
            'http': 'socks5h://' + TOR_IP + ':' + str(TOR_PORT) + '/',
            'https': 'socks5h://' + TOR_IP + ':' + str(TOR_PORT) + '/',
        }

    # Standard function to change the Proxy Exit IP
    def rotate_ip(self, params=None):
        return self.change_tor_identity()

    # Send a Signal to Tor to create new circuits
    def change_tor_identity(self):
        from stem import Signal

        if self.controller is None:
            return None

        self.controller.signal(Signal.NEWNYM)
        return True

    # Function to check the connection status
    def check_tor_status(self):
        if self.controller is None:
            return None

        # Get the bootStrap phase
        response = self.controller.get_info("status/bootstrap-phase")

        return True if response.find('SUMMARY="Done"') > 0 else False
