import socket
import ssl
import time
import select
import os
import logging
from XTB.utils import generate_logger

class Client():
    """
    Represents a client that can create and manage a socket connection.

    Attributes:
        host (str): The host to connect to.
        port (int): The port to connect to.
        encrypted (bool): Indicates whether the socket connection should be encrypted.
        blocking (bool): Indicates whether the socket connection should be blocking.
        timeout (float): The timeout value for socket operations.
        interval (float): The interval between socket operations.
        max_fails (int): The maximum number of connection attempts.
        bytes_out (int): The maximum number of bytes to send in each message.
        bytes_in (int): The maximum number of bytes to receive in each message.
        stream (bool): Indicates whether the socket connection is a stream connection.
        logger: The logger object for logging messages.
    """
    def __init__(self, host: str=None, port: int=None,  encrypted: bool=False, blocking: bool=True, timeout: float=None, interval: float=None, max_fails: int=10, bytes_out: int=1024, bytes_in: int=1024, stream: bool=False, logger=None):
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='Client', path=os.path.join(os.getcwd(), "logs"))
        
        self._host=host
        self._port=port
        self._encrypted=encrypted
        self._blocking=blocking
        self._timeout=timeout
        self._used_addresses=[]

        self.create()

        self._interval=interval
        self._max_fails=max_fails
        self._bytes_out=bytes_out
        self._bytes_in=bytes_in
        self._stream=stream

    def check(self, mode: str=None):
        """
        Check the socket for readability, writability, or errors.

        Args:
            mode (str): The mode to check for. Can be one of 'basic', 'readable', or 'writable'.

        Returns:
            bool: True if the socket is in the desired mode, False otherwise.

        Raises:
            ValueError: If an unknown mode value is provided.

        """
        try:
            # Use select to check for readability, writability, and errors
            if mode == 'basic':
                _, _, errored = select.select([], [], [self._socket], 0)
                if self._socket in errored:
                    return False
                return True
            elif mode == 'readable':
                readable, _, _ = select.select([self._socket], [], [], 0)
                if self._socket in readable:
                    return True
                return False
            elif mode == 'writable':
                _, writable, _ = select.select([], [self._socket], [], 0)
                if self._socket in writable:
                    return True
                return False
            else:
                raise ValueError("Error: unknown mode value")
        except Exception as e:
            self._logger.error("In check method: %s" % str(e))
            return False

    def create(self):
        """
        Creates a socket connection to the specified host and port.

        Returns:
            bool: True if the socket connection is successfully created, False otherwise.
        """
        self._logger.info("Creating socket ...")

        try:
            avl_addresses=socket.getaddrinfo(self._host, self._port, socket.AF_UNSPEC, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        except socket.error as e:
            self._logger.error("Failed to query socket info")
            return False
        self._logger.info(str(len(avl_addresses))+" addresses found")
        
        while len(self._used_addresses) =< len(avl_addresses):
            # Always trie adresses first that did not fail
            for i in range(len(avl_addresses)):
                address=avl_addresses[i]
                if address[4] not in self._used_addresses:
                    address=avl_addresses[i]
                    break

            # Extract the tuple
            self._family, self._socktype, self._proto, self._cname, self._sockaddr = address
            if self._family == socket.AF_INET: # For IPv4
                self._ip_address, self._port = self._sockaddr
            elif self._family == socket.AF_INET6: # For IPv6
                self._ip_address, self._port, self._flowinfo, self._scopeid = self._sockaddr 

            self._logger.info(
                "Selected socket:\nFamily: %s\nSocket Type: %s\nProtocol: %s\nCanonical Name: %s\nIP-address: %s\nPort: %s",
                self._family, self._socktype, self._proto, self._cname, self._ip_address, self._port
            )
            
            try:
                self._socket = socket.socket(self._family, self._socktype, self._proto)
            except socket.error as e:
                self._logger.error("Failed to create socket: %s", e)
                continue
            self._logger.info("Socket created")

            # in case socket is SSL wrapped
            if self._encrypted:
                try:
                    context = ssl.create_default_context()
                    self._socket=context.wrap_socket(self._socket, server_hostname=self._host)
                except socket.error as e:
                    self._logger.error("Failed to wrap socket: %s", e)
                    continue
                self._logger.info("Socket wrapped")

            # stops the socket from blocking when receive or send is called
            self._socket.setblocking(self._blocking)

            # safe used address
            self._used_addresses.append(self._sockaddr)

            return True

        self._used_addresses=[]
        
        self._logger.error("All attempts to create socket failed")
        return False
    
    def open(self):
        """
        Opens a socket connection.

        Returns:
            bool: True if the socket connection is successfully opened, False otherwise.
        """
        self._logger.info("Opening connection ...")

        if not self.check('basic'):
            self._logger.error("Socket failed. Try to create again")
            if not self.create():
                return False
                
        for _ in range(self._max_fails):
            try:
                self._socket.settimeout(None)
                self._socket.connect((self._sockaddr))
            except socket.error as error_msg:
                self._logger.error("Socket error: %s" % error_msg)
                time.sleep(self._interval)
                continue
            self._logger.info("Socket connected")
            return True
        return False

    def send(self, msg):
        """
        Sends a message over the socket connection.

        Args:
            msg (str): The message to be sent.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        self._logger.info("Sending message ...")

        msg = msg.encode("utf-8")
        send_msg = 0
        while send_msg < len(msg):
            package_size = min(self._bytes_out, len(msg) - send_msg)
            try:
                # Check socket for writability
                if self.check('writable'):
                    send_msg += self._socket.send(msg[send_msg:send_msg + package_size])
                else:
                    self._logger.error("Connection to socket broken")
                    return False
            except Exception as e:
                self._logger.error("Error sending message: %s" % str(e))
                return False
            
            self._logger.info("sending ...")
            time.sleep(self._interval)

        self._logger.info("Message sent")
        return True

    def receive(self):
        """
        Receive messages from the socket.

        This method continuously receives messages from the socket until there are no more messages to receive.
        It returns the concatenated message received.

        Returns:
            str: The concatenated message received from the socket.

        Raises:
            Exception: If there is an error receiving the message.
        """
        self._logger.info("Receiving message ...")

        full_msg = ''
        while True:
            msg=''
            try:
                # Check socket for readability
                if self.check('readable'):
                    msg = self._socket.recv(self._bytes_in)
            except Exception as e:
                self._logger.error("Error receiving message: %s" % str(e))
                return False
            
            if len(msg) > 0:
                full_msg += msg.decode("utf-8")
            time.sleep(self._interval)

            if self._stream and len(msg) > 0:
                break
            elif not self._stream and len(msg) <= 0:
                break
    
        self._logger.info("Message received")
        return full_msg
    
    def __del__(self):
        self.close()

    def close(self):
        """
        Closes the socket connection.

        Returns:
            bool: True if the socket is successfully closed, False otherwise.
        """
        self._logger.info("Closing connection ...")

        if self._socket.fileno() != -1:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._logger.info("Connections closed")
            except Exception as e:
                self._logger.error("Error shutting down socket: %s" % str(e))
                # no false return function must run through
            finally:
                self._socket.close()
                self._logger.info("Socket closed")
                return True
        else:
            self._logger.error("Socket is already closed")
            return True
        
    def get_blocking(self):
        return self._blocking
    
    def set_blocking(self, blocking):
        self._blocking = blocking
        self._socket.setblocking(blocking)

    def get_timeout(self):
        return self._timeout
    
    def set_timeout(self, timeout):
        self._timeout = timeout
        self._socket.settimeout(timeout)
        
    def get_host(self):
        return self._host
    
    def set_host(self, host):
        raise AttributeError("Cannot set read-only attribute 'address'")
    
    def get_port(self):
        return self._port
    
    def set_port(self, port):
        raise AttributeError("Cannot set read-only attribute 'port'")

    def get_encrypted(self):
        return self._encrypted

    def set_encrypted(self, encrypted):
        raise AttributeError("Cannot set read-only attribute 'encrypted'")

    def get_interval(self):
        return self._interval

    def set_interval(self, interval):
        self._interval = interval

    def get_max_fails(self):
        return self._max_fails

    def set_max_fails(self, max_fails):
        self._max_fails = max_fails

    def get_bytes_out(self):
        return self._bytes_out

    def set_bytes_out(self, bytes_out):
        self._bytes_out = bytes_out

    def get_bytes_in(self):
        return self._bytes_in

    def set_bytes_in(self, bytes_in):
        self._bytes_in = bytes_in

    blocking = property(get_blocking, set_blocking, doc='Get/set the blocking value')
    timeout = property(get_timeout, set_timeout, doc='Get/set the socket timeout')
    host = property(get_host, set_host, doc='read only property socket host')
    port = property(get_port, set_port, doc='read only property socket port')
    encrypted = property(get_encrypted, set_encrypted, doc='read only property socket encryption')
    interval = property(get_interval, set_interval, doc='Get/set the interval value')
    max_fails = property(get_max_fails, set_max_fails, doc='Get/set the max fails value')
    bytes_out = property(get_bytes_out, set_bytes_out, doc='Get/set the bytes out value')
    bytes_in = property(get_bytes_in, set_bytes_in, doc='Get/set the bytes in value')
