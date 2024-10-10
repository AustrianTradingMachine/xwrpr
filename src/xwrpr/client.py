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
from threading import Lock
from typing import List, Optional, Union
from xwrpr.utils import generate_logger


class Client():
    """
    The Client class provides a simple interface for creating and managing
    a socket connection to a server

    Attributes:
    _logger (logging.Logger): The logger instance to use for logging.
    _host (str): The host address to connect to.
    _port (int): The port number to connect to.
    _encrypted (bool): Indicates whether the connection should be encrypted.
    timeout (float): The timeout value for the connection.
    reaction_time (float): Wait time for Socket reaction.
    interval (float): The interval between requests in seconds.
    max_fails (int): The maximum number of consecutive failed requests before giving up.
    bytes_out (int): The maximum number of bytes to send in each request.
    bytes_in (int): The maximum number of bytes to receive in each response.
    _lock (threading.Lock): A lock for thread safety.
    _decoder (json.JSONDecoder): The JSON decoder instance.
    _addresses (dict): A dictionary of available addresses for the socket connection.
    _address_key (str): The key of the current address.
    _socket (socket): The socket connection.

    Methods:
        _get_addresses: Gets the available addresses for the socket connection.
        check: Check the socket for readability, writability, or errors.
        create: Creates a socket connection.
        open: Opens a connection to the server.
        send: Sends a message over the socket connection.
        receive: Receives a message from the socket.
        close: Closes the connection and releases the socket.

    Properties:
        reaction_time: Wait time for Socket reaction.
        interval: The interval between requests in seconds.
        max_fails: The maximum number of consecutive failed requests before giving up.
        bytes_out: The maximum number of bytes to send in each request.
        bytes_in: The maximum number of bytes to receive in each response.
    """

    def __init__(
        self,
        host: str,
        port: int,
        
        encrypted: bool,
        timeout: float,
        reaction_time: float=2.0,
        
        interval: float=0.5,
        max_fails: int=10,
        bytes_out: int=1024,
        bytes_in: int=1024,
        
        logger: Optional[logging.Logger]=None
    ) -> None:
        """
        Initializes a new instance of the Client class.

        Args:
            host (str): The host address to connect to.
            port (int): The port number to connect to.
            encrypted (bool): Indicates whether the connection should be encrypted.
            timeout (float): The timeout value for the connection.
            reaction_time (float, optional): Wait time for Socket reaction. Defaults to 2.0.
            interval (float, optional): The interval between requests in seconds. Defaults to 0.5.
            max_fails (int, optional): The maximum number of consecutive failed requests before giving up. Defaults to 10.
            bytes_out (int, optional): The maximum number of bytes to send in each request. Defaults to 1024.
            bytes_in (int, optional): The maximum number of bytes to receive in each response. Defaults to 1024.
            logger (logging.Logger, optional): The logger instance to use for logging. Defaults to None.

        Raises:
            None
        """

        if logger:
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
        self.reaction_time = reaction_time
        self.interval = interval
        self.max_fails = max_fails
        self.bytes_out = bytes_out
        self.bytes_in = bytes_in

        # Lock for thread safety
        self._lock = Lock()

        # Initialize the JSON decoder
        self._decoder=json.JSONDecoder()

        # A dictionary of available addresses for the socket connection.
        self._addresses = {}
        # Get the available addresses
        self._get_addresses()
        # Create the socket
        self.create()

        self._logger.info("Client initialized")

    def _get_addresses(self) -> None:
        """
        Gets the available addresses for the socket connection.

        Raises:
            ValueError: If no available addresses are found.
            ValueError: If no suitable addresses are found.

        Returns:
            None
        """

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
            self._logger.error(f"Failed to query address info: {e}")
            raise
        
        # Log the available addresses
        num_addresses = len(avl_addresses)
        self._logger.debug(f"{num_addresses} addresses found")

        # Check if there are any available addresses
        if num_addresses == 0:
            self._logger.error("No available addresses found")
            raise ValueError("No available addresses found")
        
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
            else:
                # Skip other address families
                continue

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
                'last_attempt': time.time(),
                'last_error': None,
                'family': family,
                'socktype': socktype,
                'proto': proto,
                'sockaddr': sockaddr
            }

        # Check the number of suitable addresses
        num_addresses = len(self._addresses)
        if num_addresses == 0:
            self._logger.error("No suitable addresses found")
            raise ValueError("No suitable addresses found")
        self._logger.debug(f"{num_addresses} suitable addresses found")

    def check(self, mode: str) -> None:
        """
        Check the socket for readability, writability, or errors.

        Args:
            mode (str): The mode to check for. Can be one of 'basic', 'readable', or 'writable'.

        Raises:
            ValueError: If the mode argument is not one of 'basic', 'readable', or 'writable'.
            socket.error: If there is an error checking the socket.
            TimeoutError: If the socket does not become ready within the specified timeout.

        Returns:
            None
        """

        # Checking check the status of the socket
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
        readable, writable, errored  = select.select(rlist, wlist, xlist, self.reaction_time)

        # Check if the socket is ready
        if not readable and not writable and not errored:
            self._logger.debug("Socket didnt answer")
            raise TimeoutError("Socket didnt answer")

        # Check the results
        if mode == 'basic' and self._socket in errored:
            self._logger.error("Socket error")
            # Log the failure cause
            self._addresses[self.adress_key]['last_error'] = 'check'
            raise socket.error("Socket error")
        if mode == 'readable' and self._socket not in readable:
            self._logger.debug("Socket not readable")
            raise TimeoutError("Socket not readable")
        if mode == 'writable' and self._socket not in writable:
            self._logger.debug("Socket not writable")
            raise TimeoutError("Socket not writable")
         
    def create(self, excluded_errors: List[str] = []) -> None:
        """
        Creates a socket

        Args:
            excluded_errorors (List[str], optional): A list of error values to exclude from retrying. Defaults to [].

        Raises:
            RuntimeError: If all attempts to create the socket fail.

        Returns:
            None
        """

        # Thread safety necessary
        # There can just be one socket at a time
        with self._lock:
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
                errors = [error for error in possible_errors if error not in excluded_errors]
            # Fill the list of available addresses
            avl_addresses = []
            for error in [None] + errors:
                avl_addresses.extend([key for key, value in self._addresses.items() if value['last_error'] == error])

            # Try to create the socket
            created = False
            while avl_addresses and not created:
                # Get the next address
                self.address_key = avl_addresses.pop(0)
                # If the address has been tried before
                self._addresses[self.address_key]['retries'] += 1
                self._addresses[self.address_key]['last_atempt'] = time.time()

                try:
                    # Create the socket
                    self._socket = socket.socket(
                        family = self._addresses[self.address_key]['family'],
                        type = self._addresses[self.address_key]['type'],
                        proto = self._addresses[self.address_key]['proto'],
                    )
                except socket.error as e:
                    self._logger.error(f"Failed to create socket: {e}")
                    # Log the failure cause
                    self._addresses[self.address_key]['last_error'] = 'create'
                    # Close the socket if it is not stable
                    self.close()
                    # Try the next address
                    continue

                self._logger.info("Socket created")

                # If the connection is ssl encrypted
                if self._encrypted:
                    try:
                        self._logger.info("Wrapping socket with SSL ...")
                        context = ssl.create_default_context()
                        self._socket=context.wrap_socket(
                            sock = self._socket,
                            server_hostname=self._host)
                    except socket.error as e:
                        self._logger.error(f"Failed to wrap socket: {e}")
                        # Log the failure cause
                        self._addresses[self.address_key]['last_error'] = 'wrap'
                        # Close the socket if it is not stable
                        self.close()
                        # Try the next address
                        continue

                    self._logger.info("Socket wrapped")

                # Set the socket blocking mode
                if self._timeout:
                    # The socket is in non-blocking mode
                    # The timeout avoids that the socket is raising
                    # a timout exeption immediately
                    self._socket.settimeout(value = self._timeout)
                    self._socket.setblocking(flag = False)
                else:
                    # The socket is in blocking mode
                    self._socket.settimeout(value = None)
                    self._socket.setblocking(flag = True)


                # Socket successfully created
                created = True

            # If all attempts to create the socket failed raise an exception
            if not created:
                self._logger.error("All attempts to create socket failed")
                raise RuntimeError("All attempts to create socket failed")

    def open(self, recreate: bool = True) -> None:
        """
        Opens a connection to the server.

        Raises:
            RuntimeError: If all attempts to open the connection fail.

        Returns:
            None
        """

        # Thread safety necessary
        # Socket can just be connected once
        with self._lock:
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
                    for attempt in range(1, self.max_fails + 1):
                        try:
                            # Connect to the server
                            self._socket.connect(self._addresses[self.address_key]['sockaddr'])
                            # Connection successful
                            connected = True
                            # Exit loop if connection is successful
                            break  
                        except (socket.error, InterruptedError) as e:
                            self._logger.error(f"Error connecting to server {attempt}/{self.max_fails}: {e}")
                            
                            if attempt < self.max_fails:
                                # For request limitation
                                time.sleep(self.reaction_time)
                            else:
                                # If max fails reached raise an exception
                                self._logger.error(f"Max fails reached. Unable to connect to server: {e}")
                                raise RuntimeError("Max fails reached. Unable to connect to server") from e
                except RuntimeError as e:
                    self._logger.error(f"Error opening connection: {e}")
                    # Log the failure cause
                    self._addresses[self.address_key]['last_error'] = 'connect'
                    # Close the connection if it is not stable
                    self.close()

                    if recreate:
                        # Try to create a new socket
                        self._logger.error("Attempting to recreate socket ...")
                        self.create(excluded_errors=['all'])

            self._logger.info("Connection opened")

    def send(self, msg: str) -> None:
        """
        Sends a message over the socket connection.

        Args:
            msg (str): The message to send.

        Raises:
            Exception: If there is an error sending the message

        Returns:
            None
        """

        # Thread safety necessary
        # To guarantee request limitation
        with self._lock:
            self._logger.info("Sending message ...")

            try:
                # Convert the message to bytes
                msg =  json.dumps(msg)
                msg = msg.encode("utf-8")
            except json.JSONDecodeError as e:
                self._logger.error(f"Error dumping message: {e}")
                raise Exception("Error dumping message") from e
            except UnicodeEncodeError as e:
                self._logger.error(f"Error encoding message: {e}")
                raise Exception("Error encoding message") from e

            # Check if the socket is in blocking mode
            blocking = self._socket.getblocking()
            
            # Loop until the entire message is sent
            # Or an error occurs
            send_msg_length = 0
            msg_length = len(msg)
            while send_msg_length < msg_length:
                # Calculate the package size
                package_size = min(self.bytes_out, msg_length - send_msg_length)

                try:
                    # Attempt to send the message chunk
                    send_msg_length += self._socket.send(msg[send_msg_length:send_msg_length + package_size])
                    self._logger.debug(f"Sent message chunk of size {package_size} bytes")

                    # For request limitation
                    time.sleep(self.interval)
                except BlockingIOError as e:
                    if not blocking:
                        # Check if the socket is ready for writing
                        self._logger.warning("Socket not ready for sending, checking writability...")
                        self.check(mode='writable')
                    else:
                        # For blocking mode, raise an exception
                        self._logger.error(f"Unexpected BlockingIOError in blocking socket mode: {e}")
                        raise RuntimeError("Unexpected BlockingIOError in blocking socket mode") from e
                except socket.error as e:
                    self._logger.error(f"Error sending message: {e}")
                    self.check(mode='basic')
                
            self._logger.info("Message sent")

    def receive(self) -> str:
        """
        Receives a message from the socket.

        Returns:
            str: The received message.

        Raises:
            ValueError: If no message is received.
            Exception: If there is an error receiving the message.

        Returns:
            str: The received message
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
                # TCP/IP streams don't guarantee that the message will arrive in one complete chunk.
                # A large JSON file might be broken into several smaller packets. Using select()
                # to check readability could cause to read a partial message before the rest of
                # the packets arrive. If you then stop reading or assume the message is complete,
                # the loop will end up with an incomplete JSON file.

                # Receive the message
                msg = self._socket.recv(self.bytes_in)
                # Check if the message is empty
                if not msg:
                    raise ValueError("No message received")

                # Convert the message to a string
                msg = msg.decode("utf-8")
                self._logger.debug(f"Received message chunk of size {len(msg)} bytes")
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
                    raise RuntimeError("Unexpected BlockingIOError in blocking socket mode") from e
            except UnicodeDecodeError as e:
                self._logger.error(f"Error decoding message: {e}")
                raise Exception("Error decoding message") from e
            except socket.error as e:
                self._logger.error(f"Error receiving message: {e}")
                self.check(mode='basic')

            # Thanks to the JSON format we can easily check if the message is complete
            try:
                # Fill buffer with recieved data package
                buffer += msg
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

        self._logger.info("Message received")

        # Return the full message
        return full_msg

    def __del__(self) -> None:
        """
        Clean up resources and close the connection.

        This method is automatically called when the object is about to be destroyed.
        It ensures that any open connections are closed properly and any resources
        are released.

        Raises:
            None
        """

        self.close()

    def close(self) -> None:
        """
        Closes the connection and releases the socket.

        Raises:
            None: If there is an error closing the connection.

        Returns:
            None
        """

        # Thread safety necessary
        # Socket can just be closed once
        with self._lock:
            # Check if the socket is in a basic state
            if self._socket.fileno() != -1:
                try:
                    # Shut down the connection
                    self._logger.info("Closing connection ...")
                    self._socket.shutdown(socket.SHUT_RDWR)
                    self._logger.info("Connections closed")
                except OSError as e:
                    # For graceful shutdown no raise of exception is not allowed
                    self._logger.debug(f"Error during connection shutdown: {e}")
                finally:
                    # Close the socket
                    self._logger.info("Closing socket ...")
                    self._socket.close()
                    self._logger.info("Socket closed")
                
            else:
                self._logger.warning("Connection and socket already closed")

    @property
    def timeout(self) -> Union[float, None]:
        return self.timeout
    
    @timeout.setter
    def timeout(self, value: Optional[float] = None) -> None:
        if value is None:
            self._socket.settimeout(value = None)
            self._socket.setblocking(flag = True)  
        elif value > 0:
            self._socket.settimeout(value = self.timeout)
            self._socket.setblocking(flag = False)
        else:
            raise ValueError("Timeout must be greater than or equal to zero")
        
        self.timeout = value

    @property
    def reaction_time(self) -> float:
        return self.reaction_time

    @reaction_time.setter
    def reaction_time(self, value: float) -> None:
        if value < 0:
            raise ValueError("Reaction time must be greater than or equal to zero")
        self.reaction_time = value

    @property
    def interval(self) -> float:
        return self.interval

    @interval.setter
    def interval(self, value: float) -> None:
        if value < 0:
            raise ValueError("Interval must be greater than or equal to zero")
        self.interval = value

    @property
    def max_fails(self) -> int:
        return self.max_fails

    @max_fails.setter
    def max_fails(self, value: int) -> None:
        if value < 0:
            raise ValueError("Max fails must be greater than or equal to zero")
        self.max_fails = value

    @property
    def bytes_out(self) -> int:
        return self.bytes_out

    @bytes_out.setter
    def bytes_out(self, value: int) -> None:
        if value < 1:
            raise ValueError("Bytes out must be greater than or equal to one")
        self.bytes_out = value

    @property
    def bytes_in(self) -> int:
        return self.bytes_in

    @bytes_in.setter
    def bytes_in(self, value: int) -> None:
        if value < 1:
            raise ValueError("Bytes in must be greater than or equal to one")
        self.bytes_in = value