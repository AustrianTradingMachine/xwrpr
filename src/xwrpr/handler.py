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

import logging
import time
from pathlib import Path
import configparser
from math import floor
from threading import Lock
from queue import Queue, Empty
import pandas as pd
from typing import Union, List, Optional
from xwrpr.client import Client
from xwrpr.utils import pretty ,generate_logger, CustomThread
from xwrpr.account import get_userId, get_password


# read api configuration
config = configparser.ConfigParser()
config_path=Path(__file__).parent.absolute()/'api.ini'
config.read(config_path)

HOST=config.get('SOCKET','HOST')
PORT_DEMO=config.getint('SOCKET','PORT_DEMO')
PORT_DEMO_STREAM=config.getint('SOCKET','PORT_DEMO_STREAM')
PORT_REAL=config.getint('SOCKET','PORT_REAL')
PORT_REAL_STREAM=config.getint('SOCKET','PORT_REAL_STREAM')

SEND_INTERVAL=config.getint('CONNECTION','SEND_INTERVAL')
MAX_CONNECTIONS=config.getint('CONNECTION','MAX_CONNECTIONS')
MAX_CONNECTION_FAILS=config.getint('CONNECTION','MAX_CONNECTION_FAILS')
MAX_SEND_DATA=config.getint('CONNECTION','MAX_SEND_DATA')
MAX_RECIEVE_DATA=config.getint('CONNECTION','MAX_RECIEVE_DATA')
MAX_REACTION_TIME=config.getint('CONNECTION','MAX_REACTION_TIME')


class _GeneralHandler(Client):
    """
    A class that handles general requests and responses to and from the XTB trading platform.

    Attributes:
        _logger (logging.Logger): The logger instance.
        _thread_ticker (float): The ticker for checking threads.
        _ping (dict): A dictionary to store ping related information.
        _ping_lock (Lock): A lock for ping operations.

    Methods:
        send_request: Sends a request to the server.
        receive_response: Receives a response from the server.
        thread_monitor: Monitors a thread and handles reconnection.
        start_ping: Starts the ping process.
        _send_ping: Sends ping requests to the server.
        stop_ping: Stops the ping process.
    """

    def __init__(
            self,
            host: str,
            port: int,
            logger: Optional[logging.Logger] = None
        ) -> None:
        """
        Initializes the general handler.

        Args:
            host (str): The host address.
            port (int): The port number.
            logger (logging.Logger, optional): The logger object. Defaults to None.

        Raises:
            None
        """

        if logger:
            # Use the provided logger
            self._logger = logger
        else:
            # Generate a new logger
            self._logger=generate_logger(name='GeneralHandler', path=Path.cwd() / "logs")

        self._logger.info("Initializing GeneralHandler ...")

        # Iinitialize the Client instance
        super().__init__(
            host=host,
            port=port, 

            encrypted=True,
            timeout=None,
            reaction_time = MAX_REACTION_TIME/1000,

            interval=SEND_INTERVAL/1000,
            max_fails=MAX_CONNECTION_FAILS,
            bytes_out=MAX_SEND_DATA,
            bytes_in=MAX_RECIEVE_DATA,

            logger=self._logger
        )

        # Set ticker for checking threads
        self._thread_ticker = 0.5

        # Initialize the ping dictionary and lock
        self._ping=dict()
        self._ping_lock = Lock()

        self._logger.info("GeneralHandler initialized")
    
    def send_request(
        self,
        command: str,
        ssid: Optional[str] = None,
        arguments: Optional[dict] = None,
        tag: Optional[str] = None
        ) -> None:
        """
        Sends a request to the server.

        Args:
            command (str): The command to send.
            ssid (str, optional): The stream session ID. Defaults to None.
            arguments (dict, optional): Additional arguments for the request. Defaults to None.
            tag (str, optional): A custom tag for the request. Defaults to None.

        Raises:
            None

        Returns:
            None
        """

        self._logger.info("Sending request ...")

        # Every request must at least contain the command
        request = {'command': command}

        # Add the stream session ID, arguments, and custom tag to the request
        if ssid is not None:
            # For stream commands the stream session ID is required
            request['streamSessionId'] = ssid
        if arguments is not None:
            # Some commands require additional arguments
            request.update(arguments)
        if tag is not None:
            # Tags ar always optional and can be used for debugging
            # The response will contain the same tag
            request['customTag'] = tag

        # Send the request to the server
        self.send(request)

        # For the login command, the user ID and password are masked
        if command == 'login':
            request['arguments']['userId'] = '*****'
            request['arguments']['password'] = '*****'

        self._logger.info(f"Request sent: {request}")

    def receive_response(self, stream: bool = False) -> dict:
        """
        Receives a response from the server.

        Args:
            stream (bool, optional): A flag indicating whether the response is for a stream request. Defaults to False.

        Raises:
            ValueError: If the response is empty or not a dictionary.
            ValueError: If the response is corrupted.
            ValueError: If the request failed.

        Returns:
            dict: The response from the server.
        """

        self._logger.info("Receiving response ...")

        # Receive the response from the server
        response = self.receive()

        if not response:
            self._logger.error("Empty response")
            raise ValueError("Empty response")
        
        self._logger.debug("Received response: " + str(response)[:100] + ('...' if len(str(response)) > 100 else ''))

        if not isinstance(response, dict):
            self._logger.error("Response not a dictionary")
            raise ValueError("Response not a dictionary")

        if not stream:
            # Non stream responses have the flag "status"
            if not 'status' in response:
                self._logger.error("Response corrupted")
                raise ValueError("Response corrupted")

            if not response['status']:
                # If the status is False, the response contains an error code and description
                self._logger.error("Request failed")
                self._logger.error(response['errorCode'])
                self._logger.error(response['errorDescr'])
                raise ValueError("Request failed. Error code: " + str(response['errorCode']) + ", Error description: " + response['errorDescr'])

        return response
    
    def thread_monitor(
        self,
        name: str,
        thread_data: dict,
        reconnect: Optional[callable] = None
    ) -> None:
        """
        Monitors the specified thread and handles reconnection if necessary.

        Args:
            name (str): The name of the thread being monitored.
            thread_data (dict): A dictionary containing information about the thread.
            reconnect (callable, optional): A method to be called for reconnection. Defaults to None.

        Raises:
            ValueError: If the reconnection method is not callable

        Returns:
            None
        """

        self._logger.info(f"Monitoring thread for {name} ...")

        while thread_data['run']:
            # If the thread is still running, continue monitoring
            if thread_data['thread'].is_alive():
                continue

            # Check if the thread should still be running
            if not thread_data['run']:
                break

            self._logger.error(f"Thread for {name} died")

            # Check if the reconnection method is callable
            if reconnect:
                if not callable(reconnect):
                    self._logger.error("Reconnection method not callable")
                    raise ValueError("Reconnection method not callable")

            # Reconnect to the server
            if reconnect:
                reconnect()

            self._logger.error(f"Restarting thread for {name} ...")

            # Create a new thread with the parameters of the dead thread
            dead_thread = thread_data['thread']
            thread_data['thread'] = CustomThread(
                target=dead_thread._target,
                args=dead_thread._args,
                daemon=dead_thread._daemon,
                kwargs=dead_thread.kwargs
            )
            thread_data['thread'].start()

            # Wait for the interval before checking the thread again
            time.sleep(self._thread_ticker)

        self._logger.info(f"Monitoring for thread {name} stopped")

    def start_ping(
        self,
        handler: Union['_DataHandler', '_StreamHandler']
    ) -> None:
        """
        Starts the ping functionality.

        Args:
            handler (_DataHandler or _StreamHandler): The handler instance.

        Raises:
            RuntimeError: If the ping was never started.

        Returns:
            None
        """

        self._logger.info("Starting ping ...")

        # Set the run flag for the ping on true
        self._ping['run'] = True
        # Create a new thread for the ping
        self._ping['thread'] = CustomThread(
            target=self._send_ping,
            args=(handler,self._ping),
            daemon=True
        )
        self._ping['thread'].start()

        self._logger.info("Ping started")


        self._logger.info("Starting ping monitor ...")

        # Create the thread monitor for the ping thread
        monitor_thread = CustomThread(
            target=self.thread_monitor,
            args=('Ping', self._ping, handler.reconnect,),
            daemon=True)
        # Start the thread monitor
        monitor_thread.start()

        self._logger.info("Ping monitor started")

    def _send_ping(
        self,
        handler: Union['_DataHandler', '_StreamHandler'],
        thread_data: dict
        ) -> None:
        """
        Sends ping requests to the server.

        Args:
            handler: The handler instance.
            run: A flag indicating whether the ping process should continue running.

        Returns:
            bool: False if the ping failed.

        Raises:
            Exception: If the ping failed.
        """
        # sends ping all 10 minutes
        ping_interval = 60*9.9
        elapsed_time=0

        self._logger.info("Start sending ping ...")

        # Loop until the run flag is set to False
        while thread_data['run']:
            # Start the timer
            start_time = time.time()

            # Check if the ping timer has reached the interval
            if elapsed_time >= ping_interval:
                # thanks to th with statement the ping could fail to keep is sheduled interval
                # but thats not important because this is just the maximal needed interval and
                # a function that locks the ping_key also initiates a reset to the server
                
                # When the hanler need the socket for a request the ping will be stopped
                # to avoid a conflict with the request
                with self._ping_lock:
                    # dynamic allocation of ssid for StreamHandler
                    # ssid could change during the ping process
                    if isinstance(handler, _StreamHandler):
                        ssid = handler.dh.ssid
                    else:
                        ssid = None

                    # Stream handler have to send their ssid with every request to the host
                    self.send_request(command='ping', ssid=ssid)

                    if not ssid:
                        # None stream pings recieve a response
                        self.receive_response()

                    self._logger.info("Ping")

                    # reset the ping timer
                    elapsed_time = 0

            # Ping is checked every 1/10 of its interval
            time.sleep(self._thread_ticker)

            # Calculate the elapsed time
            elapsed_time += time.time() - start_time

        self._logger.info("Ping stopped")

    def stop_ping(self) -> None:
        """
        Stops the ping process.

        Returns:
            bool: True if the ping process was stopped successfully, False otherwise.

        Raises:
            RuntimeError: If the ping was never started.
        """

        self._logger.info("Stopping ping ...")

        # Check if ping was ever created
        if not self._ping:
            self._logger.error("Ping never started")
            raise RuntimeError("Ping never started")

        # Check if the ping is intended to run 
        if not self._ping['run']:
            self._logger.warning("Ping already stopped")
        else:
            self._ping['run'] = False

            # Wait for the ping thread to stop
            self._ping['thread'].join(timeout=self._thread_ticker*5)

        self._logger.info("Ping stopped")
    
class _DataHandler(_GeneralHandler):
    """
    Handles data-related operations for the XTB trading platform.

    Attributes:
        _logger (logging.Logger): The logger instance used for logging.
        _demo (bool): Indicates whether the handler is for the demo mode or not.
        stream_handler (list): A list of attached stream handlers.
        reconnection_lock (Lock): A lock for reconnection operations.
        status (str): The status of the data handler ('active', 'inactive', or 'deleted').
        ssid (str): The stream session ID received from the server.

    Methods:
        delete: Deletes the DataHandler.
        _login: Logs in to the XTB trading platform.
        _logout: Logs out the user from the XTB trading platform.
        get_data: Retrieves data for the specified command.
        _retrieve_data: Retrieves data for the specified command.
        _reconnect: Reconnects to the server.
        attach_stream_handler: Attaches a stream handler to the DataHandler.
        detach_stream_handler: Detaches a stream handler from the DataHandler.
        _close_stream_handlers: Closes the stream handlers.

    Properties:
        stream_handler: The stream handlers attached to the DataHandler.
        reconnection_lock: The lock used for reconnection.
        status: The status of the DataHandler.
        ssid: The stream session ID.
    """

    def __init__(
        self,
        demo: bool,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Initializes the DataHandler.

        Args:
            demo (bool): Specifies whether the DataHandler is for demo or real trading.
            logger (logging.Logger, optional): The logger object to use for logging. If not provided, a new logger will be generated.

        Raises:
            None
        """

        if logger:
            # Use the provided logger
            self._logger = logger
        else:
            # Generate a new logger
            self._logger=generate_logger(name='DataHandler', path=Path.cwd() / "logs")

        self._logger.info("Initializing DataHandler ...")

        # Defines if the server is called for demo or real trading
        self._demo=demo

        # Initialize the GeneralHandler instance
        super().__init__(
            host=HOST,
            port=PORT_DEMO if self._demo else PORT_REAL,
            logger=self._logger
        )
        
        # Stream handlers that are attached to the DataHandler
        self.stream_handler=[]
        # The lock for reconnection operations
        self.reconnection_lock=Lock()

        # Initialize the status and stream session ID
        self.status='inactive'
        self.ssid=None

        # Log in to the XTB trading platform
        self._login()
        # Starts ping to keep connection open
        self.start_ping(handler=self)

        self._logger.info("DataHandler initialized")
        
    def __del__(self) -> None:
        """
        Destructor method that is called when the DataHandler object is about to be destroyed.

        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations and deletes the object

        Raises:
            None
        """

        self.delete()
    
    def delete(self) -> None:
        """
        Deletes the DataHandler.

        Returns:
            None

        Raises:
            None
        """

        # Check if the DataHandler is already deleted
        if self.status == 'deleted':
            self._logger.warning("DataHandler already deleted")
        else:
            self._logger.info("Deleting DataHandler ...")

            try:
                # Close the stream handlers and stop the ping process
                self._close_stream_handlers()
                self.stop_ping()
                self._logout()
            except Exception as e:
                # For graceful closing no raise of exception is not allowed
                self._logger.error(f"Failed to close stream handlers and stop ping: {e}")
            finally:
                # Set Status to deleted
                self.status = 'deleted'
                
            self._logger.info("DataHandler deleted")
            
    def _login(self) -> None:
        """
        Logs in to the XTB trading platform.

        Returns:
            None

        Raises:
            None
        """

        # No reconnection because login is part of reconnection routine
        self._logger.info("Logging in ...")

        # Open the connection to the server
        self.open()

        # Locks out the ping process
        # To avoid conflicts with the login process
        # Could happen if relogin of running handler is necessary
        with self._ping_lock:
            # Send the login request to the server
            self.send_request(
                command='login',
                arguments={
                    'arguments': {
                        'userId': get_userId(self._demo), # get_userId() returns the user ID for the demo or real trading mode
                        'password': get_password() # get_password() returns the password for the user ID
                    }
                }
            )
            # Receive the response from the server
            response = self.receive_response()

        self._logger.info("Log in successfully")
        self.ssid = response['streamSessionId']

        self.status = 'active'
                            
    def _logout(self) -> None:
        """
        Logs out from the XTB trading platform.

        Returns:
            None

        Raises:
            None
        """
        # No reconnection because login is undesirable!

        if not self.ssid:
            # Logged in clients have a stream session ID
            self._logger.warning("Already logged out")
        
        # Locks out the ping process
        # To avoid conflicts with the login process
        with self._ping_lock:
            try:
                self._logger.info("Logging out ...")
                # Send the logout request to the server
                # Server sends no response for logout request
                self.send_request(command='logout')
                self._logger.info("Logged out successfully")
            except Exception as e:
                # For graceful logout no raise of exception is not allowed
                self._logger.error(f"Could not log out: {e}")
            finally:
                # Close the socket
                self.close()
                # Delete the stream session ID 
                self.ssid=None
                # Set the status to inactive
                self.status='inactive'

    def get_data(self, command: str, **kwargs) -> dict:
        """
        Retrieves data from the server.

        Args:
            command (str): The command to retrieve data.
            **kwargs: Additional keyword arguments for the command.

        Returns:
            The retrieved data if successful.
        """

        if not self.ssid:
            self._logger.error("Got no StreamSessionId from Server")
            raise ValueError("Got no StreamSessionId from Server")
        
        # Try to retrieve the data twice
        # This enables a automatic reconnection if the first attempt fails
        for tries in range(2):
            try:
                # Retrieve the data for the specified command
                response = self._retrieve_data(command, **kwargs)
                # Return the response if successful
                return response
            except Exception as e:
                self._logger.error(f"Failed to retrieve data: {e}")
                if tries == 0:
                    # Reconnect if the first attempt fails
                    self._logger.info("Try a reconnection ...")
                    self.reconnect()
                else:
                    # If the data could not be retrieved, raise an error
                    self._logger.error("Failed to retrieve data")
                    raise

    def _retrieve_data(self, command: str, **kwargs) -> dict:
        """
        Retrieve data for the specified command.

        Args:
            command (str): The command to retrieve data for.
            **kwargs: Additional keyword arguments to be passed to the command.

        Returns:
            The retrieved data as a dictionary.

        Raises:
            None.
        """

        # Locks out the ping process
        # To avoid conflicts with the login process
        with self._ping_lock:
            self._logger.info("Getting data for " + pretty(command) + " ...")

            # Send the request to the server
            self.send_request(
                command='get'+command,
                arguments={'arguments': kwargs} if bool(kwargs) else None)
                
            # Receive the response from the server
            response = self.receive_response()
            
            # Response must contain 'returnData' key with data
            if not 'returnData' in response or not response['returnData']:
                self._logger.error("No data in response")
                raise ValueError("No data in response")
                
            # Log the successful retrieval of data in pretty format
            self._logger.info("Data for "+pretty(command) +" recieved")

            # Return the data
            return response['returnData']
 
    def reconnect(self) -> None:
        """
        Reconnects to the server.

        This method is used to establish a new connection to the server in case the current connection is lost.

        Returns:
            None

        Raises:
            None
        """

        # In case a reconnection is already in progress,
        # by a connected stream handler
        # the lock is used to avoid conflicts
        with self.reconnection_lock:
            try:
                # Set the status to inactive
                self.status = 'inactive'
                # Check the socket
                self.check(mode='basic')
            except Exception as e:
                self._logger.info("Reconnecting ...")
                # Create a new socket
                self.create()
                # Relogin to the server
                self._login()
                self._logger.info("Reconnection successful")

            self.status = 'active'
            self._logger.info("Data connection is already active")
 
    def attach_stream_handler(self, handler: '_StreamHandler') -> None:
        """
        Attach a StreamHandler to the DataHandler.

        Parameters:
        - handler: The stream handler to attach.

        Returns:
            None

        Raises:
            None
        """

        self._logger.info("Attaching StreamHandler ...")

        if handler not in self.stream_handler:
            self.stream_handler.append(handler)
            self._logger.info("StreamHandler attached")
        else:
            self._logger.warning("StreamHandler already attached")

    def detach_stream_handler(self, handler: '_StreamHandler') -> None:
        """
        Detaches a StreamHandler from the DataHandler.

        Args:
            handler (_StreamHandler): The stream handler to detach.

        Returns:
            None

        Raises:
            None
        """

        self._logger.info("Detaching StreamHandler ...")

        if handler in self.stream_handler:
            self.stream_handler.remove(handler)
            self._logger.info("StreamHandler detached")
        else:
            self._logger.warning("StreamHandler not found")

    def _close_stream_handlers(self) -> None:
        """
        Closes the stream handlers.

        This method closes all the stream handlers associated with the logger.

        Returns:
            None
        """

        self._logger.info("Closing StreamHandlers ...")

        if not self.stream_handler:
            self._logger.info("No StreamHandlers to close")
        else:
            for handler in list(self.stream_handler):
                try:
                    handler.delete()
                except KeyError as e:
                    # For graceful closing no error message raise of exception not is allowed
                    self._logger.error(f"Failed to close StreamHandler: {e}")
                    # detaching is only executed by StreamHandler itself

    @property
    def stream_handler(self) -> List['_StreamHandler']:
        return self.stream_handler
    
    @property
    def reconnection_lock(self) -> Lock:
        return self.reconnection_lock
    
    @property
    def status(self) -> str:
        return self.status
    
    @status.setter
    def status(self, value: str) -> None:
        if value not in ['active', 'inactive', 'deleted']:
            raise ValueError("Invalid status value")
        self.status = value

    @property
    def ssid(self) -> str:
        return self.ssid


class _StreamHandler(_GeneralHandler):
    """
    Handles streaming data from XTB API.

    Attributes:
        _logger (logging.Logger): The logger object used for logging.
        dh (_DataHandler): The data handler object.
        status (str): The status of the stream handler.
        _stream (dict): The stream dictionary.
        stream_tasks (dict): The dictionary of stream tasks.
        _stop_lock (Lock): The lock for stopping the stream.
        _ssid (str): The stream session ID.

    Methods:
        delete: Deletes the StreamHandler.
        stream_data: Starts streaming data from the server.
        _start_stream: Starts the stream for the specified command.
        _receive_stream: Receives the stream data.
        _stop_task: Stops the stream task.
        _stop_stream: Stops the stream.
        _restart_stream: Restarts the stream.
        _reconnect: Reconnects the stream handler.

    Properties:
        dh: The data handler object.
        status: The status of the stream handler.
        ssid: The stream session ID.
    """

    def __init__(
        self,
        dataHandler: _DataHandler,
        demo: bool,
        logger: Optional[logging.Logger] = None
        ) -> None:
        """
        Initialize the StreamHandler object.

        Args:
            dataHandler (_DataHandler): The data handler object.
            demo (bool): A boolean indicating whether the handler is for demo or real trading.
            logger (logging.Logger, optional): The logger object to use for logging. Defaults to None.
        
        Raises:
            None
        """

        if logger:
            # Use the provided logger
            self._logger = logger
        else:
            # Generate a new logger
            self._logger = generate_logger(name='StreamHandler', path=Path.cwd() / "logs")

        self._logger.info("Initializing StreamHandler ...")

        # Initialize the GeneralHandler instance
        super().__init__(
            host=HOST,
            port=PORT_DEMO_STREAM if demo else PORT_REAL_STREAM,
            logger=self._logger
        )

        # Attach the StreamHandler to the DataHandler
        self.dh = dataHandler
        self.dh.attach_stream_handler(self)

        # Open connection to the server
        self.open()

        # Set the status to active
        # StreamHandler need no login
        # so the status is active right after the connection is open
        self.status = 'active'

        self._stream=dict()
        self.stream_tasks = dict()
        self._stop_lock = Lock()

        # Send KeepAlive to keep connection open
        # First command must beb sent 1 second after connection is opened
        # Otherwise the server will close the connection
        self.stream_data(command='KeepAlive')
        # Start ping to keep connection open
        self.start_ping(handler=self)
        
        self._logger.info("StreamHandler initialized")

    def __del__(self) -> None:
        """
        Destructor method that is called when the StreamHandler object is about to be destroyed.

        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations and deletes the object.

        Returns:
            None

        Raises:
            None
        """
        
        self.delete()
            
    def delete(self) -> None:
        """
        Deletes the StreamHandler.

        Returns:
            None

        Raises:
            None
        """

        if self.status == 'deleted':
            self._logger.warning("StreamHandler already deleted")
        else:
            self._logger.info("Deleting StreamHandler ...")

            try:
                # Stop the stream and ping processes
                self._stop_stream()
                self.stop_ping()
                self.close()
                self.dh.detach_stream_handler(self)
            except Exception as e:
                # For graceful closing no raise of exception is not allowed
                self._logger.error(f"Failed to stop stream and ping: {e}")
            finally:
                # Set Status to deleted
                self.status= 'deleted'
        
            self._logger.info("StreamHandler deleted")
        
    def stream_data(
        self,
        command: str,
        exchange: Optional[dict] = None,
        **kwargs
        ) -> None:
        """
        Start streaming data from the server.

        Args:
            command (str): The command to start streaming data.
            exchange (dict, optional): The exchange information. Defaults to None.
            **kwargs: Additional keyword arguments for the command.

        Returns:
            None

        Raises:
            ValueError: If the DataHandler has no StreamSessionId from the server.
            ValueError: If the stream for the data is already open.
        """
        
        # Check if DataHandler can provide a ssid
        if not self.dh.ssid:
            self._logger.error("DataHandler got no StreamSessionId from Server")
            raise ValueError("DataHandler got no StreamSessionId from Server")
        
        # Check if the specific stream is already open
        for index in self.stream_tasks:
            if self.stream_tasks[index]['command'] == command and self.stream_tasks[index]['kwargs'] == kwargs:
                self._logger.warning("Stream for data already open")
                raise ValueError("Stream for data already open")


        # Try to retrieve the data twice
        # This enables a automatic reconnection if the first attempt fails
        for tries in range(2):
            try:
                # Retrieve the data for the specified command
                self._start_stream(command, **kwargs)
            except Exception as e:
                self._logger.error(f"Failed to stream data: {e}")
                if tries == 0:
                    # Reconnect if the first attempt fails
                    self._logger.info("Try a reconnection ...")
                    self._reconnect()
                else:
                    # If the data could not be retrieved, raise an error
                    self._logger.error("Failed to retrieve data")
                    raise

        # Initiate the stream thread for the handler
        if not self._stream:
            # Set the run flag for the stream on true
            self._stream['run'] = True
            # Create a new thread for the stream
            self._stream['thread'] = CustomThread(
                target=self._receive_stream,
                daemon=True
            )
            # Start the stream thread
            self._stream['thread'].start()

            # Create the thread monitor for the stream thread
            monitor_thread = CustomThread(
                target=self.thread_monitor,
                args=('Stream', self._stream, self._reconnect,),
                daemon=True
            )
            # Start the thread monitor
            monitor_thread.start()

        # Register the stream task
        index = len(self.stream_tasks)
        self.stream_tasks[index] = {'command': command, 'arguments': kwargs}

        # The data from the KeepAlive command is unnecessary
        if command != 'KeepAlive':
            # The data from the stream is put into the queue for the exchange
            self.stream_tasks[index]['queue'] = exchange['queue']

            # Put a killswitch nfor the stream task into the exchange dictionary
            exchange['thread'] = CustomThread(
                target=self._stop_task,
                args=(index,),
                daemon=True
            )

        self._logger.info("Stream started for " + pretty(command))

    def _start_stream(self, command: str, **kwargs) -> None:
        """
        Starts a stream for the given command.

        Args:
            command (str): The command to start the stream for.
            **kwargs: Additional keyword arguments to be passed as arguments for the stream.

        Returns:
            None

        Raises:
            None
        """

        # Locks out the ping process
        # To avoid conflicts with the stream request
        with self._ping_lock:
            self._logger.info("Starting stream for " + pretty(command) + " ...")

            # Dynamic allocation of ssid for StreamHandler
            # ssid could change during DataHandler is open
            self._ssid = self.dh.ssid

            # Send the request for the stream to the server
            self.send_request(
                command='get'+command,
                ssid=self._ssid,
                arguments=kwargs if bool(kwargs) else None
            )
        
    def _receive_stream(self) -> None:
        """
        Receive and process streaming data from the server.

        Returns:
            None

        Raises:
            ValueError: If the response does not contain a command.
            ValueError: If the response does not contain data.
            ValueError: If the stream task does not match
        """

        # Thanks to the inconsstency of the API necessary to translate the command
        translate = {
            'Balance': 'balance',
            'Candles': 'candle',
            'KeepAlive': 'keepAlive',
            'News': 'news',
            'Profits': 'profit',
            'TickPrices': 'tickPrices',
            'Trades':'trade',
            'TradeStatus': 'tradeStatus',
            }

        # Loop until the run flag is set to False
        while self._stream['run']:
            self._logger.info("Streaming data ...")
    
            # Locks out the ping process
            # To avoid conflicts with the receive process
            with self._ping_lock:
                response = self.receive_response(stream = True)

            # Response must contain 'command' key with command
            if not 'command' in response:
                self._logger.error("No command in response")
                raise ValueError("No command in response")

            # Response must contain 'data' key with data
            if not 'data' in response:
                self._logger.error("No data in response")
                raise ValueError("No data in response")
            
            # Assign streamed data to the corresponding stream task
            for index in self.stream_tasks:
                command = self.stream_tasks[index]['command']
                arguments = self.stream_tasks[index]['arguments']
                
                # Skip if the command does not match
                if translate[command] != response['command']:
                    continue
                
                # Skip if its the KeepAlive stream
                if command == 'KeepAlive':
                    continue

                # Not just the command but also the arguments must match
                # symbol is the only additional argument that could be passed
                if 'symbol' in response['data']:
                    if set(arguments['symbol']) != set(response['data']['symbol']):
                        continue
                
                self._logger.info("Data received for " + pretty(command))

                # Put the data into the queue for the exchange
                self.stream_tasks[index]['queue'].put(response['data'])

        self._logger.info("All streams stopped")

    def _stop_task(self, index: int) -> None:
        """
        Stops a stream task at the specified index.

        Args:
            index (int): The index of the stream task to stop.

        Returns:
            None

        Raises:
            None
        """

        # Necessary if task is stopped by user(thread) and handler(delete) at the same time
        with self._stop_lock:
            if index in self.stream_tasks:
                command = self.stream_tasks[index]['command']
                arguments = self.stream_tasks[index]['arguments']

                self._logger.info("Stopping stream for " + pretty(command) + " ...")

                # Locks out the ping process
                # To avoid conflicts with the stop request
                with self._ping_lock:
                    # Send the stop request to the server
                    self.send_request(
                        command='stop' + command,
                        arguments={'symbol': arguments['symbol']} if 'symbol' in arguments else None
                    )

                # Deregister the stream task
                del self.stream_tasks[index]
                    
    def _stop_stream(self) -> None:
        """
        Stops the stream and ends all associated tasks.

        Returns:
            None

        Raises:
            RuntimeError: If the stream was never started.
        """

        self._logger.info("Stopping all streams ...")

        # Check if the stream was ever created
        if not self._stream:
            self._logger.error("Stream never started")
            raise RuntimeError("Stream never started")
        
        # Check if the stream is intended to run
        if not self._stream['run']:
            self._logger.warning("Stream already ended")
        else:
            self._stream['run'] = False

            # Wait for the stream thread to stop
            self._stream['thread'].join()

        # Stop all stream tasks
        for index in list(self.stream_tasks):
            self._stop_task(index=index)
            
        self._logger.info("All streams stopped")

    def _restart_streams(self) -> None:
        """
        Restarts all stream tasks.

        Returns:
            None

        Raises:
            None
        """

        self._logger.info("Restarting all streams ...")

        # Restart all stream tasks
        for index in list(self.stream_tasks):
            command=self.stream_tasks[index]['command']
            kwargs=self.stream_tasks[index]['arguments']
            self._start_stream(command,**kwargs)

        self._logger.info("All streams restarted")
 
    def _reconnect(self) -> None:
        """
        Reconnects the StreamHandler to the DataHandler.

        Returns:
            None

        Raises:
            None
        """

        # Check if reconnection of the DataHandler is already in progress
        # either by the DataHandler itself or another StreamHandler
        if self.dh.reconnection_lock.acquire(blocking=False):
            # If the DataHandler is not already reconnected
            # the StreamHandler can initiate a reconnection
            try:
                # Reconnect the DataHandler
                self.dh.reconnect()
            except Exception as e:
                self._logger.error(f"Failed to reconnect: {e}")
                raise
            finally:
                # Release the lock after the reconnection is done
                self.dh.reconnection_lock.release()
        else:
            # If the lock couldnt be acquired, the Streamhandler stops
            # the reconnection process immediately
            self._logger.info("Reconnection attempt for DataHandler is already in progress by another StreamHandler.")

        # Wait for the DataHandler to reconnect
        with self.dh.reconnection_lock:
            try:
                # Set the status to inactive
                self.status='inactive'
                # Check the socket
                self.check('basic')
            except Exception as e:
                self._logger.info("Reconnecting ...")
                # Create a new socket
                self.create()
                # Open the connection
                self.open()
                # Restart the stream tasks
                self._restart_streams()
 
            self.status='active'
            self._logger.info("Stream connection is already active")

    @property
    def dh(self) -> _DataHandler:
        return self.dh
    
    @property
    def status(self) -> str:
        return self.status
    
    @status.setter
    def status(self, value: str) -> None:
        if value not in ['active', 'inactive', 'deleted']:
            raise ValueError("Invalid status value")
        self.status = value

    @property
    def stream_tasks(self) -> dict:
        return self.stream_tasks

class HandlerManager():
    """
    The HandlerManager class manages the creation and deletion of data and stream handlers.
    It keeps track of the maximum number of connections and provides available handlers when requested.
    """

    def __init__(
        self,
        demo: bool=True,
        logger: Optional[logging.Logger]=None
        ) -> None:
        """
        Initializes a new instance of the HandlerManager class.

        Args:
            demo (bool, optional): Specifies whether the handlers are for demo purposes. Defaults to True.
            logger (logging.Logger, optional): The logger instance to use for logging. Defaults to None.
        """
        
        if logger:
            # Use the provided logger
            self._logger = logger
        else:
            # Generate a new logger
            self._logger=generate_logger(name='HandlerManager', path=Path.cwd() / "logs")

        self._demo=demo

        self._handlers = {'data': {}, 'stream': {}}
        self._max_streams=floor(1000/SEND_INTERVAL)
        self._max_connections=MAX_CONNECTIONS
        self._connections=0
        self._deleted=False

    def __del__(self) -> None:
        """
        Destructor method that is called when the HandlerManager instance is deleted.

        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations and deletes the object.

        Returns:
            None

        Raises:
            None
        """

        self.delete()

    def delete(self) -> None:
        """
        Deletes the HandlerManager instance and all associated handlers.

        Returns:
            None

        Raises:
            None
        """

        if self._deleted:
            self._logger.warning("HandlerManager already deleted")
        else:
            for handler in self._handlers['data']:
                # 
                if handler.status == 'active':
                    self._delete_handler(handler)

            # Set the deleted flag to True
            self._deleted=True

    def _delete_handler(self, handler: Union[_DataHandler, _StreamHandler]) -> bool:
        """
        Deletes a specific handler and deregisters it from the HandlerManager.

        Args:
            handler: The handler to delete.

        Returns:
            bool: True if the handler was successfully deleted, False otherwise.
        """
        if isinstance(handler, _DataHandler):
            # Just deregister the Streamhandler from the DataHandler
            for stream in list(handler.stream_handler):
                self._logger.info("Deregister StreamHandler "+self._handlers['stream'][stream]['name'])
                self._connections -= 1
            
            self._logger.info("Deregister DataHandler "+self._handlers['data'][handler]['name'])
            self._connections -= 1
        elif isinstance(handler, _StreamHandler):
            self._logger.info("Deregister StreamHandler "+self._handlers['stream'][handler]['name'])
            self._connections -= 1

        # Delete the handler
        handler.delete()

    def _avlb_DataHandler(self) -> _DataHandler:
        """
        Gets an available data handler.

        Returns:
            _DataHandler: An available DataHandler if found.

        Raises:
            None
        """
        for handler in self._handlers['data']:
            if handler.status == 'active':
                return handler
    
    def _avlb_StreamHandler(self) -> _StreamHandler:
        """
        Gets an available stream handler.

        Returns:
            _StreamHandler: An available StreamHandler if found.

        Raises:
            None
        """
        for handler in self._handlers['stream']:
            if handler.status == 'active':
                if len(handler.stream_tasks) < self._max_streams:
                    return handler

    
    def _generate_DataHandler(self) -> _DataHandler:
        """
        Generates a new data handler.

        Returns:
            _DataHandler: A new DataHandler.

        Raises:
            RuntimeError: If the maximum number of connections is reached.
        """

        self._logger.info("Generating DataHandler ...")

        if self._connections >= self._max_connections:
            self._logger.error("Maximum number of connections reached")
            raise RuntimeError("Maximum number of connections reached")

        # Index the new DataHandler
        index = len(self._handlers['data'])
        name = 'DH_' + str(index)
        dh_logger = self._logger.getChild(name)

        # Create the new DataHandler
        dh = _DataHandler(demo=self._demo, logger=dh_logger)

        # Register the new DataHandler
        self._handlers['data'][dh] = {'name': name}
        self._connections += 1

        self._logger.info("DataHandler generated")

        return dh

    def _generate_StreamHandler(self) -> _StreamHandler:
        """
        Generates a new stream handler.

        Returns:
            _StreamHandler: A new StreamHandler.

        Raises:
            RuntimeError: If the maximum number of connections is reached.
        """

        self._logger.info("Generating StreamHandler ...")

        if self._connections >= self._max_connections:
            self._logger.error("Maximum number of connections reached")
            raise RuntimeError("Maximum number of connections reached")

        # Index the new StreamHandler
        index = len(self._handlers['stream'])
        name = 'SH_' + str(index)
        sh_logger = self._logger.getChild(name)

        # Create the new StreamHandler
        dh = self.provide_DataHandler()
        sh = _StreamHandler(dataHandler=dh, demo=self._demo, logger=sh_logger)

        # Register the new StreamHandler
        self._handlers['stream'][sh] = {'name': name}
        self._connections += 1

        self._logger.info("StreamHandler generated")

        return sh

    def provide_DataHandler(self) -> _DataHandler:
        """
        Provides an available data handler.

        Returns:
            _DataHandler: An DataHandler if found, otherwise a new DataHandler.

        Raises:
            None
        """

        # Check if an available data handler is available
        handler=self._avlb_DataHandler()

        # If no available data handler is found, generate a new one
        if not handler:
            try:
                handler = self._generate_DataHandler()
            except RuntimeError as e:
                self._logger.error(f"Failed to generate DataHandler: {e}")

        return handler

    def provide_StreamHandler(self) -> _StreamHandler:
        """
        Provides an available stream handler.

        Returns:
            _StreamHandler: An available stream handler if found, otherwise a new stream handler.

        Raises:
            None
        """

        # Check if an available stream handler is available
        handler=self._avlb_StreamHandler()

        # If no available stream handler is found, generate a new one
        if not handler:
            try:
                handler = self._generate_StreamHandler()
            except RuntimeError as e:
                self._logger.error(f"Failed to generate StreamHandler: {e}")

        return handler
