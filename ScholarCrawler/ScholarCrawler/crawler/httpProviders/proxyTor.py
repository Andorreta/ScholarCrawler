"""
HTTP Provider for the Tor Proxy
"""


class ProxyTor(object):
    from stem.control import Controller

    # Sets the data to establish a TOR proxy connection
    def set_connection(self, params=None):
        from settings import TOR_PORT, TOR_IP

        status = self.tor_check_status()
        if status == True:
            return {
                'http': 'socks5h://' + TOR_IP + ':' + str(TOR_PORT) + '/',
                'https': 'socks5h://' + TOR_IP + ':' + str(TOR_PORT) + '/',
            }
        else:
            return status

    # Standard function to check the connection status
    def check_connection_status(self, params=None):
        return self.check_connection_status()

    # Standard function to change the Proxy Exit IP
    def rotate_ip(self, params=None):
        self.tor_check_status()

    # Send a Signal to Tor to create new circuits
    def change_tor_identity(self):
        import stem

        try:
            with self.Controller.from_port() as controller:
                controller.authenticate()
                controller.signal(stem.Signal.NEWNYM)
        except (stem.SocketError, stem.connection.AuthenticationFailure) as error:
            print('Unable to connect to Control Port: ' + str(error) + "\n")

    # Check the status of the Tor connection
    def tor_check_status(self):
        import stem

        try:
            with self.Controller.from_port() as controller:
                controller.authenticate() # TODO aqui peta
                # TODO hay que hacer algo para que coja la cookie (mi sistema está bien configurado
                # TODO con los permisos y la ubicación del fichero, así que tiene que ser cosa del STEM)
                # TODO Tambien se podría cambiar al sistema de autenticación por clave (Password)
                response = controller.get_info("status/bootstrap-phase")
                controller.close()

                if response.find('SUMMARY="Done"') > 0:
                    return True
        except (stem.SocketError, stem.connection.AuthenticationFailure) as error:
            print('Unable to connect to Control Port: ' + str(error) + "\n")

        return False
