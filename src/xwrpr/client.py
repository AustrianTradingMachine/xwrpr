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
from typing import List
from xwrpr.utils import generate_logger

class Client():
    """
    The Client class provides a simple interface for creating and managing

    Attributes:
    _logger (logging.Logger): The logger instance to use for logging.
    _host (str): The host address to connect to.
    _port (int): The port number to connect to.
    _encrypted (bool): Indicates whether the connection should be encrypted.
    _timeout (float): The timeout value for the connection.
    _blocking (bool): Indicates whether the connection is blocking.
    _interval (float): The interval between requests in seconds.
    _max_fails (int): The maximum number of consecutive failed requests before giving up.
    _bytes_out (int): The maximum number of bytes to send in each request.
    _bytes_in (int): The maximum number of bytes to receive in each response.
    _decoder (json.JSONDecoder): The JSON decoder instance.
    _addresses (dict): A dictionary of addresses that have been used.
    _address_key (str): The key of the current address.
    _socket (socket): The socket connection.

    Methods:
        check: Check the socket for readability, writability, or errors.
        create: Creates a socket connection.
        open: Opens a connection to the server.
        send: Sends a message over the socket connection.
        receive: Receives a message from the socket.
        close: Closes the connection and releases the socket.
        get_host: Returns the host address.
        set_host: Sets the host address.
        get_port: Returns the port number.
        set_port: Sets the port number.
        get_encrypted: Returns the encrypted flag.
        set_encrypted: Sets the encrypted flag.

        get_timeout: Returns the timeout value.
        set_timeout: Sets the timeout value.
        get_interval: Returns the interval value.
        set_interval: Sets the interval value.
        get_max_fails: Returns the max fails value.
        set_max_fails: Sets the max fails value.
        get_bytes_out: Returns the bytes out value.
        set_bytes_out: Sets the bytes out value.
        get_bytes_in: Returns the bytes in value.
        set_bytes_in: Sets the bytes

    """

    def __init__(
        self,
        host: str,
        port: int,
        
        encrypted: bool,
        timeout: float,
        
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
        
        # If timeout is set, the socket should be non-blocking
        # Sockets in blocking mode has to wait indefinitely for an event
        if self._timeout:
            self._blocking = False
        else:
            self._blocking = True
            
        # List of used addresses
        self._addresses = {}

        # Create the socket
        self._get_adresses()
        self.create()

        self._interval = interval
        self._max_fails = max_fails
        self._bytes_out = bytes_out
        self._bytes_in = bytes_in

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
            # Checkking check the status of the socket
            # The check is intern, no request to the server is made

            # Initialize the lists
            rlist, wlist, xlist = [], [], []
            if mode == 'basic':
                xlist = [self._socket]
            elif mode == 'readable':
                rlist = [self._socket]
            elif mode == 'writable':
                wlist = [self._socket]
            else:
                raise ValueError("Unknown mode value")
            
            # Check the socket
            readable, writable, errored  = select.select(rlist, wlist, xlist, 0)

            # Check the results
            if mode == 'basic' and self._socket in errored:
                self._logger.error("Socket error")
                # Log the failure cause
                self._addresses[self.adress_key]['last_error'] = 'check'
                raise Exception("Socket error")
            if mode == 'readable' and self._socket not in readable:
                self._logger.debug("Socket not readable")
                raise Exception("Socket not readable")
            if mode == 'writable' and self._socket not in writable:
                self._logger.debug("Socket not writable")
                raise Exception("Socket not writable")
        except Exception as e:
            self._logger.error("Error in check method: %s" % str(e))
            raise Exception("Error in check method") from e
        
    def _get_adresses(self):
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
        self._logger.debug(f"{len(avl_addresses)} addresses found")

        # Check if there are any available addresses
        number_of_avl_addresses = len(avl_addresses)
        if number_of_avl_addresses == 0:
            self._logger.error("No available addresses found")
            raise Exception("No available addresses found")
        
        for address in avl_addresses:
            # Extract the address info         
            family, socktype, proto, cname, sockaddr = address
            flowinfo, scopeid = None, None
            if family == socket.AF_INET:
                # For IPv4 sockedadress consists of (ip, port)
                ip_address, port = sockaddr
            elif family == socket.AF_INET6:
                # For IPv6 sockedadress consists of (ip, port, flowinfo, scopeid)
                ip_address, port, flowinfo, scopeid = sockaddr 

            # Log adress
            self._logger.debug("Available address:")
            self._logger.debug(
                "\nFamily: %s\nSocket Type: %s\nProtocol: %s\nCanonical Name: %s\nIP-address: %s\nPort: %s",
                family, socktype, proto, cname, ip_address, port
            )
            if family == socket.AF_INET6:
                self._logger.debug("Flow Info: %s\nScope ID: %s", flowinfo, scopeid)

            # Create a key for the address
            address_key = f"{family}__{socktype}__{proto}"
            self._addresses[address_key] = {
                'retries': 0,
                'last_atempt': time.time(),
                'last_error': None,
                'family': family,
                'socktype': socktype,
                'proto': proto,
            }
                
    def create(self, excluded_errors: List[str] = []) -> None:
        """
        Creates a socket connection.

        Args:
            excluded_errorors (List[str], optional): A list of error values to exclude from retrying. Defaults to [].

        Raises:
            ValueError: If the excluded_errorors list contains an unknown error value.
            Exception: If there is an error creating the socket.
        """

        self._logger.info("Creating socket ...")

        # Check for existing socket
        if hasattr(self, '_socket'):
            self._logger.warning("Socket already exists")
            # Close the existing socket
            self.close()

        # List of possible error values
        # Ordered by level of lifecicle of the socket
        possible_errors = ['check', 'connect', 'wrap', 'create']

        # Fill the list of errors
        errors = []
        if 'all' not in excluded_errors:
            for error in possible_errors:
                if error not in excluded_errors:
                    errors.append(error)

        # Fill the list of available addresses
        avl_addresses = []
        for error in None, errors:
            avl_addresses.append([key for key, value in self._addresses.items() if value['last_error'] is error])

        try:
            # Try to create the socket
            created = False
            while len(avl_addresses) > 0 and not created:
                # Get the next address
                self.address_key = avl_addresses.pop(0)

                # For request limitation
                time.sleep(self._interval)

                # If the address has been tried before
                self._addresses[self.address_key]['retries'] += 1
                self._addresses[self.address_key]['last_atempt'] = time.time()

                try:
                    # Create the socket
                    self._socket = socket.socket(
                        family = self._family,
                        type = self._socktype,
                        proto = self._proto
                    )
                except socket.error as e:
                    self._logger.error("Failed to create socket: %s" % str(e))
                    # Log the failure cause
                    self._addresses[self.address_key]['last_error'] = 'create'
                    # Close the socket if it is not stable
                    self.close()
                    # Try the next address
                    continue

                self._logger.info("Socket created")

                # If the connection is ssl encrypted
                if self._encrypted:
                    self._logger.info("Wrapping socket ...")
                    
                    try:
                        # Wrap the socket with SSL
                        context = ssl.create_default_context()
                        self._socket=context.wrap_socket(
                            sock = self._socket,
                            server_hostname=self._host)
                    except socket.error as e:
                        self._logger.error("Failed to wrap socket: %s" % str(e))
                        # Log the failure cause
                        self._addresses[self.address_key]['last_error'] = 'wrap'
                        # Close the socket if it is not stable
                        self.close()
                        # Try the next address
                        continue

                    self._logger.info("Socket wrapped")

                # Set the socket blocking mode
                self._socket.setblocking(flag = self._blocking)
                if self._timeout:
                    # The socket is in non-blocking mode
                    # The timeout avoids that the socket is raising
                    # a timout exeption immediately
                    self._socket.settimeout(value = self._timeout)

                # Socket successfully created
                created = True

            # If all attempts to create the socket failed raise an exception
            if not created:
                self._logger.error("All attempts to create socket failed")
                raise Exception("All attempts to create socket failed")
        except Exception as e:
            self._logger.error("Error creating socket: %s" % str(e))
            raise Exception("Error creating socket") from e

    def open(self, recreate: bool = True) -> None:
        """
        Opens a connection to the server.

        Raises:
            Exception: If there is an error opening the connection.
        """

        self._logger.info("Opening connection ...")

        try:
            # Ceck if socket is already connected
            if self._socket.getpeername():
                self._logger.warning("Socket already connected")
                # Return if the socket is already connected
                return
        except socket.error:
            # Pass if the socket is not connected
            pass

        # Loop until the connection is established
        # or an error occurs
        connected = False
        while not connected:
            try:
                # Try to connect to the server
                for attempt in range(1, self._max_fails + 1):
                    try:
                        # Connect to the server
                        self._socket.connect(self._sockaddr)
                        # Exit loop if connection is successful
                        break  
                    except (socket.error, InterruptedError) as e:
                        self._logger.error("Error connecting to socket (%d/%d): %s" % (attempt, self._max_fails, str(e)))
                        
                        if attempt < self._max_fails:
                            # For request limitation
                            time.sleep(self._interval)
                        else:
                            # If max fails reached raise an exception
                            self._logger.error("Max fails reached. Unable to open connection.")
                            raise Exception("Max fails reached. Unable to connect to server.") from e
            except Exception as e:
                self._logger.error("Error connecting to socket: %s" % str(e))
                # Log the failure cause
                self._addresses[self.address_key]['last_error'] = 'connect'
                # Close the connection if it is not stable
                self.close(stable = False)
                if recreate:
                    # Try to create a new socket
                    self._logger.error("Try to create a new socket")
                    self.create(excluded_errors=['all'])

            # Connection successful
            connected = True

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
        except UnicodeEncodeError as e:
            self._logger.error("Error encoding message: %s" % str(e))
            raise Exception("Error encoding message") from e
        except Exception as e:
            self._logger.error("Error during converting message: %s" % str(e))
            raise Exception("Error during converting message") from e
        
        # Check if the socket is in blocking mode
        blocking = self._socket.getblocking()
        
        # Loop until the entire message is sent
        # Or an error occurs
        send_msg_length = 0
        msg_length = len(msg)
        while send_msg_length < msg_length:
            package_size = min(self._bytes_out, msg_length - send_msg_length)
            try:
                # Attempt to send the message chunk
                send_msg_length += self._socket.send(msg[send_msg_length:send_msg_length + package_size])

                # For request limitation
                time.sleep(self._interval)

            # Handle if socket is not immediately writable (non-blocking case)
            except BlockingIOError as e:
                if not blocking:
                    # Check if the socket is ready for writing
                    self._logger.warning("Socket not ready for sending, checking writability...")
                    self.check(mode='writable')
                else:
                    # For blocking mode, raise an exception
                    self._logger.error("Unexpected BlockingIOError in blocking socket mode")
                    raise Exception("Unexpected BlockingIOError in blocking socket mode") from e
            except Exception as e:
                self._logger.error("Error sending message: %s" % str(e))
                socket_failed = ''
                try:
                    self.check(mode='basic')
                except Exception:
                    socket_failed = 'Socket failed'
                raise Exception(f"Error sending message. {socket_failed}") from e
            
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

        # Check if the socket is in blocking mode
        blocking = self._socket.getblocking()

        # Initialize the full message and buffer
        full_msg = ''
        buffer=''

        # Loop until the entire message is received
        # Or an error occurs
        while True:
            try:
                # No check for readability because big Messages could fail
                #TCP/IP streams don't guarantee that the message will arrive in one complete chunk.
                # A large JSON file might be broken into several smaller packets. Using select()
                # to check readability could cause to read a partial message before the rest of
                # the packets arrive. If you then stop reading or assume the message is complete,
                # the loop will end up with an incomplete JSON file.

                # Receive the message
                msg = self._socket.recv(self._bytes_in)

                if not msg:
                    # Only a finished message can break the loop
                    pass

                # Convert the message to a string
                msg = msg.decode("utf-8")
            except BlockingIOError as e:
                if not blocking:
                    # Check if the socket is ready for reading
                    self._logger.warning("Socket not ready for receiving, checking readability...")
                    self.check(mode='readable')
                    # Continue receiving data
                    continue
                else:
                    # For blocking mode, raise an exception
                    self._logger.error("Unexpected BlockingIOError in blocking socket mode")
                    raise Exception("Unexpected BlockingIOError in blocking socket mode") from e
            except UnicodeDecodeError as e:
                self._logger.error("Error decoding message: %s" % str(e))
                raise Exception("Error decoding message") from e
            except Exception as e:
                self._logger.error("Error receiving message: %s" % str(e))
                socket_failed = ''
                try:
                    self.check(mode='basic')
                except Exception:
                    socket_failed = 'Socket failed'
                raise Exception(f"Error receiving message. {socket_failed}") from e

            # Fill buffer with recieved data package
            buffer += msg

            # Thanks to the JSON format we can easily check if the message is complete
            try:
                # Try to decode the buffer
                full_msg, pos = self._decoder.raw_decode(buffer)
                if pos == len(buffer):
                    # Entire buffer has been successfully decoded
                    buffer=''
                    # Exit the loop
                    break
                elif pos < len(buffer):
                    # Partially decoded, more data might follow
                    buffer = buffer[pos:].strip()
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

        Raises:
            None: If there is an error closing the connection.
        """
       
        # Check if the socket is in a basic state
        if self._socket.fileno() != -1:
            try:
                self._logger.info("Closing connection ...")
                # Close the connection
                self._socket.shutdown(socket.SHUT_RDWR)
                self._logger.info("Connections closed")
            except OSError as e:
                # For graceful shutdown no error message is allowed
                self._logger.debug("Error closing connection: %s" % str(e))
            
            try:
                self._logger.info("Closing socket ...")
                # Close the socket
                self._socket.close()
                self._logger.info("Socket closed")
            except OSError as e:
                self._logger.error("Error closing socket: %s" % str(e))
        else:
            self._logger.warning("Connection and socket already closed")
        
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