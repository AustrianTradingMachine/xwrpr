#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###########################################################################
#
#    xwrpr - A wrapper for the API of XTB (https://www.xtb.com)
#
#    Copyright (C) 2024  Philipp Craighero
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###########################################################################

import socket
import ssl
import time
import select
from pathlib import Path
import logging
import json
from xwrpr.utils import generate_logger

class Client():
    """
    The Client class provides a simple interface for creating and managing

    Attributes:
    _host (str): The host address to connect to.
    _port (int): The port number to connect to.
    _encrypted (bool): Indicates whether the connection should be encrypted.
    _timeout (float): The timeout value for the connection.
    _blocking (bool): Indicates whether the connection is blocking.
    _used_addresses (list): A list of addresses that have been used.
    _family (int): The address family.
    _socktype (int): The socket type.
    _proto (int): The protocol.
    _cname (str): The canonical name.
    _sockaddr (tuple): The socket address.
    _ip_address (str): The IP address.
    _port (int): The port number.
    _socket (socket): The socket connection.
    _interval (float): The interval between requests in seconds.
    _max_fails (int): The maximum number of consecutive failed requests before giving up.
    _bytes_out (int): The maximum number of bytes to send in each request.
    _bytes_in (int): The maximum number of bytes to receive in each response.
    _stream (bool): Indicates whether to use a streaming connection.
    _decoder (json.JSONDecoder): The JSON decoder instance.
    _logger (logging.Logger): The logger instance to use for logging.

    Methods:
        check: Check the socket for readability, writability, or errors.
        create: Creates a socket connection.
        open: Opens a connection to the server.
        send: Sends a message over the socket connection.
        receive: Receives a message from the socket.
        close: Closes the connection and releases the socket.

    """

    def __init__(
        self,
        host: str,
        port: int,
        
        encrypted: bool,
        timeout: float,
        stream: bool,
        
        interval: float=0.5,
        max_fails: int=10,
        bytes_out: int=1024,
        bytes_in: int=1024,
        
        logger=None
    ) -> None:
        """
        Initializes a new instance of the Client class.

        Args:
            host (str): The host address to connect to.
            port (int): The port number to connect to.
            encrypted (bool): Indicates whether the connection should be encrypted.
            timeout (float): The timeout value for the connection.
            stream (bool): Indicates whether to use a streaming connection.
            interval (float, optional): The interval between requests in seconds. Defaults to 0.5.
            max_fails (int, optional): The maximum number of consecutive failed requests before giving up. Defaults to 10.
            bytes_out (int, optional): The maximum number of bytes to send in each request. Defaults to 1024.
            bytes_in (int, optional): The maximum number of bytes to receive in each response. Defaults to 1024.
            logger (logging.Logger, optional): The logger instance to use for logging. Defaults to None.

        Raises:
            ValueError: If the logger argument is provided but is not an instance of logging.Logger.
        """

        

        if logger:
            # Check if the logger is an instance of logging.Logger
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            # Use the provided logger
            self._logger = logger
        else:
            # Generate a new logger
            self._logger = generate_logger(name='Client', path=Path.cwd() / "logs")

        self._logger.info("Initializing the client ...")
        
        self._host = host
        self._port = port
        self._encrypted = encrypted
        self._timeout = timeout
        
        if timeout:
            # If timeout is set, the socket should be non-blocking
            self._blocking = False
        else:
            # If timeout is not set, the socket should be blocking
            self._blocking = True
            
        self._used_addresses = []

        # Create the socket
        self.create()

        self._interval = interval
        self._max_fails = max_fails
        self._bytes_out = bytes_out
        self._bytes_in = bytes_in
        self._stream = stream

        # Initialize the JSON decoder
        self._decoder=json.JSONDecoder()

        self._logger.info("Client initialized")

    def check(self, mode: str) -> None:
        """
        Check the socket for readability, writability, or errors.

        Args:
            mode (str): The mode to check for. Can be one of 'basic', 'readable', or 'writable'.

        Raises:
            ValueError: If the mode argument is not one of 'basic', 'readable', or 'writable'.
            Exception: If there is an error checking the socket.
        """

        try:
            if mode == 'basic':
                # Check if the socket is in an error state
                _, _, errored = select.select(
                    rlist = [],
                    wlist = [],
                    xlist = [self._socket],
                    timeout = 0
                )
                if self._socket in errored:
                    raise Exception("Socket error")
            elif mode == 'readable':
                # Check if the socket is readable
                readable, _, _ = select.select(
                    rlist = [self._socket],
                    wlist = [],
                    xlist = [],
                    timeout = 0
                )
                if self._socket not in readable:
                    raise Exception("Socket not readable")
            elif mode == 'writable':
                # Check if the socket is writable
                _, writable, _ = select.select(
                    rlist = [],
                    wlist = [self._socket],
                    xlist = [],
                    timeout = 0
                )
                if self._socket not in writable:
                    raise Exception("Socket not writable")
            else:
                raise ValueError("Error: unknown mode value")
        except Exception as e:
            self._logger.error("Error in check method: %s" % str(e))
            raise Exception("Error in check method") from e

    def create(self) -> None:
        """
        Creates a socket connection.

        Raises:
            Exception: If there is an error creating the socket.
        """

        self._logger.info("Creating socket ...")

        try:
            # Get address info from the socket
            avl_addresses=socket.getaddrinfo(
                host = self._host,
                port = self._port,
                family = socket.AF_UNSPEC,
                type = socket.SOCK_STREAM,
                proto = socket.IPPROTO_TCP
            )
        except socket.error as e:
            self._logger.error("Failed to query socket info: %s" % str(e))
            raise Exception("Failed to query socket info") from e

        # Log the available addresses
        self._logger.info(f"{len(avl_addresses)} addresses found")

        tried_addresses = []
        connected = False
        while len(tried_addresses) < len(avl_addresses) and not connected:
            # Always tries those adresses first that did not fail
            # if all adresses failed, it tries all adresses again
            if len(self._used_addresses)+len(tried_addresses) < len(avl_addresses):
                for address in avl_addresses:
                    # Check if the address has not been tried before
                    if address[4] not in tried_addresses and address[4] not in self._used_addresses:
                        tried_addresses.append(address)
                        break
            else:
                for address in avl_addresses:
                    # Check if the address has not been tried before
                    if address[4] not in tried_addresses:
                        tried_addresses.append(address)
                        break

            # Extract the address info         
            self._family, self._socktype, self._proto, self._cname, self._sockaddr = tried_addresses[-1]
            if self._family == socket.AF_INET:
                # For IPv4 sockedadress consists of (ip, port)
                self._ip_address, self._port = self._sockaddr
            elif self._family == socket.AF_INET6:
                # For IPv6 sockedadress consists of (ip, port, flowinfo, scopeid)
                self._ip_address, self._port, self._flowinfo, self._scopeid = self._sockaddr 

            # Log the selected socket
            self._logger.info(
                "Selected socket:\nFamily: %s\nSocket Type: %s\nProtocol: %s\nCanonical Name: %s\nIP-address: %s\nPort: %s",
                self._family, self._socktype, self._proto, self._cname, self._ip_address, self._port
            )
            
            # For request limitation
            time.sleep(self._interval)

            try:
                # Create the socket
                self._socket = socket.socket(
                    family = self._family,
                    type = self._socktype,
                    proto = self._proto
                )
            except socket.error as e:
                self._logger.error("Failed to create socket: %s" % str(e))
                # Try the next address
                continue

            self._logger.info("Socket created")

            # If the connection is ssl encrypted
            if self._encrypted:
                try:
                    # Wrap the socket with SSL
                    context = ssl.create_default_context()
                    self._socket=context.wrap_socket(
                        sock = self._socket,
                        server_hostname=self._host)
                except socket.error as e:
                    self._logger.error("Failed to wrap socket: %s" % str(e))
                    # Try the next address
                    continue

                self._logger.info("Socket wrapped")

            # Set the socket to non-blocking mode
            self._socket.setblocking(flag = self._blocking)

            # Add the address to the list of used addresses
            self._used_addresses.append(self._sockaddr)

            # Connection successful
            connected = True

        self._used_addresses=[]
        
        # If all attempts to create the socket failed raise an exception
        self._logger.error("All attempts to create socket failed")
        raise Exception("All attempts to create socket failed")

    def open(self) -> None:
        """
        Opens a connection to the server.

        Raises:
            Exception: If there is an error opening the connection.
        """

        self._logger.info("Opening connection ...")

        try:
            # Check if the socket is in a basic state
            self.check(mode='basic')
        except Exception as e:
            self._logger.error("Socket failed. Try to create again")
            # Create a new socket
            self.create()
    
        # Try to connect to the server
        for fails in range(self._max_fails):
            try:
                if self._timeout:
                    # Set the timeout for the socket
                    self._socket.settimeout(value = self._timeout)
                # Connect to the server
                self._socket.connect((self._sockaddr))
            except Exception as e:
                self._logger.error("Error connecting to socket: %s" % str(e))

                if fails < self._max_fails - 1:
                    # For request limitation
                    time.sleep(self._interval)
                    # Try again
                    continue
                else:
                    # If max fails reached raise an exception
                    self._logger.error("Max fails reached")
                    raise Exception("Max fails reached") from e
            break

        self._logger.info("Connection opened")

    def send(self, msg: str) -> None:
        """
        Sends a message over the socket connection.

        Args:
            msg (str): The message to send.

        Raises:
            Exception: If there is an error sending the message.
        """

        self._logger.info("Sending message ...")

        try:
            # Convert the message to bytes
            msg =  json.dumps(msg)
            msg = msg.encode("utf-8")
        except json.JSONDecodeError as e:
            self._logger.error("Error dumping message: %s" % str(e))
            raise Exception("Error dumping message") from e
        except Exception as e:
            self._logger.error("Error during encoding message: %s" % str(e))
            raise Exception("Error during encoding message") from e
        
        send_msg = 0
        while send_msg < len(msg):
            package_size = min(self._bytes_out, len(msg) - send_msg)
            try:
                # Check if the socket is writable
                self.check(mode='writable')

                # Send the message
                send_msg += self._socket.send(msg[send_msg:send_msg + package_size])
            except Exception as e:
                self._logger.error("Error sending message: %s" % str(e))
                raise Exception("Error sending message") from e
            
            # For request limitation
            time.sleep(self._interval)

        self._logger.info("Message sent")

    def receive(self) -> str:
        """
        Receives a message from the socket.

        Returns:
            str: The received message.

        Raises:
            Exception: If there is an error receiving the message.
        """

        self._logger.info("Receiving message ...")

        # Initialize the full message and buffer
        full_msg = ''
        buffer=''

        while True:
            try:
                # No check for readability because big Messages could fail
                msg = self._socket.recv(self._bytes_in).decode("utf-8")
            except Exception as e:
                self._logger.error("Error receiving message: %s" % str(e))
                raise Exception("Error receiving message") from e

            # Fill buffer with recieved data package
            buffer += msg

            # Thanks to the JSON format we can easily check if the message is complete
            try:
                # Try to decode the buffer
                full_msg, pos = self._decoder.raw_decode(buffer)
                if pos == len(buffer):
                    # Entire buffer has been successfully decoded
                    buffer=''
                    break
                elif pos < len(buffer):
                    # Partially decoded, more data might follow
                    buffer = buffer[pos:].strip()
                    break
            except json.JSONDecodeError:
                # Continue receiving data if JSON is not yet complete
                # No output of error message because error is necessary
                continue
            except Exception as e:
                self._logger.error("Error decoding message: %s" % str(e))
                raise Exception("Error decoding message") from e

        self._logger.info("Message received")

        # Return the full message
        return full_msg

    def __del__(self) -> None:
        """
        Clean up resources and close the connection.

        This method is automatically called when the object is about to be destroyed.
        It ensures that any open connections are closed properly and any resources
        are released.

        """
        self.close()

    def close(self) -> None:
        """
        Closes the connection and releases the socket.

        """
       
        self._logger.info("Closing connection ...")

        # Check if the socket is in a basic state
        if self._socket.fileno() != -1:
            try:
                # Close the connection
                self._socket.shutdown(socket.SHUT_RDWR)
                self._logger.info("Connections closed")
            except Exception as e:
                 # For graceful shutdown no error message is allowed
                self._logger.error("Error shutting down socket: %s" % str(e))
            finally:
                # Close the socket
                self._socket.close()
                # Because the socked showed stable behavior,
                # the address is removed from the list of used addresses
                self._used_addresses.pop() 
                self._logger.info("Socket closed")
        else:
            self._logger.warning("Socket is already closed")
        
    def get_host(self) -> str:
        return self._host
    
    def set_host(self, host) -> None:
        raise AttributeError("Cannot set read-only attribute 'host'")
    
    def get_port(self) -> int:
        return self._port
    
    def set_port(self, port) -> None:
        raise AttributeError("Cannot set read-only attribute 'port'")

    def get_encrypted(self) -> bool:
        return self._encrypted

    def set_encrypted(self, encrypted) -> None:
        raise AttributeError("Cannot set read-only attribute 'encrypted'")
    
    def get_timeout(self) -> float:
        return self._timeout
    
    def set_timeout(self, timeout) -> None:
        self._timeout = timeout
        self._socket.settimeout(timeout)
        
        if timeout:
            self._blocking=False
        else:
            self._blocking=True

    def get_interval(self) -> float:
        return self._interval

    def set_interval(self, interval) -> None:
        self._interval = interval

    def get_max_fails(self) -> int:
        return self._max_fails

    def set_max_fails(self, max_fails) -> None:
        self._max_fails = max_fails

    def get_bytes_out(self) -> int:
        return self._bytes_out

    def set_bytes_out(self, bytes_out) -> None:
        self._bytes_out = bytes_out

    def get_bytes_in(self) -> int:
        return self._bytes_in

    def set_bytes_in(self, bytes_in) -> None:
        self._bytes_in = bytes_in

    
    # Properties
    host = property(get_host, set_host, doc='read only property socket host')
    port = property(get_port, set_port, doc='read only property socket port')
    encrypted = property(get_encrypted, set_encrypted, doc='read only property socket encryption')
    timeout = property(get_timeout, set_timeout, doc='Get/set the socket timeout')
    interval = property(get_interval, set_interval, doc='Get/set the interval value')
    max_fails = property(get_max_fails, set_max_fails, doc='Get/set the max fails value')
    bytes_out = property(get_bytes_out, set_bytes_out, doc='Get/set the bytes out value')
    bytes_in = property(get_bytes_in, set_bytes_in, doc='Get/set the bytes in value')