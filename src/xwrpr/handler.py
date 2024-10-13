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

from enum import Enum
import logging
import configparser
from pathlib import Path
from typing import Union, List, Optional
import json
import time
from threading import Lock
from queue import Queue
from statistics import mean
from xwrpr.client import Client
from xwrpr.utils import pretty ,generate_logger, CustomThread
from xwrpr.account import get_userId, get_password, set_path


# Read the configuration file
config = configparser.ConfigParser()
config_path=Path(__file__).parent.absolute()/'api.ini'
config.read(config_path)

HOST=config.get('SOCKET','HOST')
PORT_DEMO=config.getint('SOCKET','PORT_DEMO')
PORT_DEMO_STREAM=config.getint('SOCKET','PORT_DEMO_STREAM')
PORT_REAL=config.getint('SOCKET','PORT_REAL')
PORT_REAL_STREAM=config.getint('SOCKET','PORT_REAL_STREAM')
TIMEOUT=config.getint('SOCKET','TIMEOUT')

THREAD_TICKER=config.getint('HANDLER','THREAD_TICKER')/1000
SM_INTERVAL=config.getint('HANDLER','SM_INTERVAL')
IDLE_THRESHOLD=config.getint('HANDLER','IDLE_THRESHOLD')/1000

class Status(Enum):
    """
    Enum class for the status of the handler.

    Attributes:
        ACTIVE: The handler is active.
        INACTIVE: The handler is inactive.
        SUSPENDED: The handler is suspended.
        FAILED: The handler failed.
        DELETED: The handler is deleted.
    
    Methods:
        None
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    FAILED = "failed"
    DELETED = "deleted"


class _GeneralHandler(Client):
    """
    Handles general requests to and from the XTB trading platform.

    Attributes:
        _logger (logging.Logger): The logger instance.
        _thread_ticker (float): The ticker for checking threads.
        _ping (dict): A dictionary to store ping related information.
        _ping_lock (Lock): A lock for ping operations.

    Methods:
        send_request: Sends a request to the server.
        receive_response: Receives a response from the server.
        thread_monitor: Monitors a thread and handles reactivation if necessary.
        start_ping: Starts the ping process.
        _send_ping: Sends ping requests to the server.
        stop_ping: Stops the ping process.
    """

    def __init__(
            self,
            host: str,
            port: int,

            max_send_data: int,
            max_received_data: int,
            min_request_interval: int,
            max_retries: int,
            max_reaction_time: int,

            stream: bool = False,
            logger: Optional[logging.Logger] = None
        ) -> None:
        """
        Initializes a new instance of the GeneralHandler class.

        Args:
            host (str): The host address.
            port (int): The port number.
            max_send_data (int): The maximum number of bytes to send.
            max_received_data (int): The maximum number of bytes to receive.
            min_request_interval (int): The minimum request interval in seconds.
            max_retries (int): The maximum number of retries.
            max_reaction_time (int): The maximum reaction time in seconds.
            stream (bool, optional): A flag indicating whether the handler is for stream requests. Defaults to False.
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
            timeout= TIMEOUT if stream else None,
            reaction_time = max_reaction_time,

            interval=min_request_interval,
            max_fails=max_retries,
            bytes_out=max_send_data,
            bytes_in=max_received_data,

            logger=self._logger
        )

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

        if response == '':
            if stream:
                # Stream responses can be empty
                # in this case just return an empty dictionary
                return {}
            
            self._logger.error("Empty response")
            raise ValueError("Empty response")
        
        self._logger.debug("Received response: " + str(response)[:100] + ('...' if len(str(response)) > 100 else ''))

        try:
            # Convert the response string to a dictionary
            response_dict = json.loads(response)
        except json.JSONDecodeError as e:
            self._logger.error(f"Error decoding JSON response: {e}")
            raise ValueError("Response not a valid JSON")

        if not stream:
            # Non stream responses have the flag "status"
            if 'status' not in response_dict:
                self._logger.error("Response corrupted")
                raise ValueError("Response corrupted")

            if not response_dict['status']:
                # If the status is False, the response contains an error code and description
                self._logger.error("Request failed. Error code: " + str(response_dict['errorCode']) + ", Error description: " + response_dict['errorDescr'])
                raise ValueError("Request failed. Error code: " + str(response_dict['errorCode']) + ", Error description: " + response_dict['errorDescr'])

        return response
    
    def thread_monitor(
        self,
        name: str,
        thread_data: dict,
        reactivate: Optional[callable] = None
    ) -> None:
        """
        Monitors the specified thread and handles reactivation if necessary.

        Args:
            name (str): The name of the thread being monitored.
            thread_data (dict): A dictionary containing information about the thread.
            reactivate (callable, optional): A method to reactivate the thread. Defaults to None.

        Raises:
            ValueError: If the reconnection method is not callable.

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

            # Check if the reactivation method is callable
            if reactivate:
                if not callable(reactivate):
                    self._logger.error("Reactivation method not callable")
                    raise ValueError("Reactivation method not callable")

            # Reactivate the thread if necessary
            if reactivate:
                reactivate()

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
            time.sleep(THREAD_TICKER)

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
            args=('Ping', self._ping, handler.reactivate,),
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
        # sends ping all 9 minutes
        # Ping should be sent at least every 10 minutes
        ping_interval = 60*9
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
                        ssid = handler._dh.ssid
                    else:
                        ssid = None

                    # Stream handler have to send their ssid with every request to the host
                    self.send_request(command='ping', ssid=ssid)

                    if not ssid:
                        # None stream pings receive a response
                        self.receive_response()

                    self._logger.info("Ping")

                    # reset the ping timer
                    elapsed_time = 0

            # Ping is checked every 1/10 of its interval
            time.sleep(THREAD_TICKER)

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
            self._ping['thread'].join(timeout=THREAD_TICKER*5)

        self._logger.info("Ping stopped")
    
class _DataHandler(_GeneralHandler):
    """
    Handles data requests to and from the XTB trading platform.

    Attributes:
        _logger (logging.Logger): The logger instance used for logging.
        _demo (bool): Indicates whether the handler is for the demo mode or not.
        _stream_handler (list): A list of attached stream handlers.
        _reactivation_lock (Lock): The lock for reactivation.
        _status (Status): The status of the handler.
        _ssid (str): The stream session ID received from the server.
        _idle_times (List[float]): The list of idle times.
        _sm_idle_time (float): The sliding mean idle time.

    Methods:
        delete: Deletes the DataHandler.
        _login: Logs in to the XTB trading platform.
        _logout: Logs out the user from the XTB trading platform.
        get_data: Retrieves data for the specified command.
        _retrieve_data: Retrieves data for the specified command.
        reactivate: Reactivates the DataHandler.
        attach_stream_handler: Attaches a stream handler to the DataHandler.
        detach_stream_handler: Detaches a stream handler from the DataHandler.
        _close_stream_handlers: Closes the stream handlers.

    Properties:
        stream_handler: The stream handlers attached to the DataHandler.
        reactivation_lock: The lock for reactivating the DataHandler.
        status: The status of the DataHandler.
        ssid: The stream session ID.
    """

    def __init__(
        self,
        demo: bool,
        username: str,
        password: str,

        max_send_data: int,
        max_received_data: int,
        min_request_interval: int,
        max_retries: int,
        max_reaction_time: int,

        logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Initializes a new instance of the DataHandler class.

        Args:
            demo (bool): Specifies whether the DataHandler is for demo or real trading.
            username (str): The username for the XTB trading platform.
            password (str): The password for the XTB trading platform.
            max_send_data (int): The maximum number of bytes to send.
            max_received_data (int): The maximum number of bytes to receive.
            min_request_interval (int): The minimum request interval in seconds.
            max_retries (int): The maximum number of retries.
            max_reaction_time (int): The maximum reaction time in seconds.
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
        # The username and password for the XTB trading platform
        # Username depends on the demo or real trading mode
        self._username=username
        self._password=password

        # Initialize the GeneralHandler instance
        super().__init__(
            host=HOST,
            port=PORT_DEMO if self._demo else PORT_REAL,

            max_send_data = max_send_data,
            max_received_data = max_received_data,
            min_request_interval = min_request_interval,
            max_retries = max_retries,
            max_reaction_time = max_reaction_time,

            logger=self._logger
        )
        
        # Stream handlers that are attached to the DataHandler
        self._stream_handler: List['_StreamHandler'] = []
        # The lock for reactivating the DataHandler
        self._reactivation_lock=Lock()

        # The status of the DataHandler is initially set to inactive
        # because not jet ready for usage
        self._status=Status.INACTIVE
        # Stream session ID is necessary for stream requests
        # It is provided from the server after login
        self._ssid: Optional[str] = None

        # Log in to the XTB trading platform
        self._login()
        # Starts ping to keep connection open
        self.start_ping(handler=self)

        self._logger.info("DataHandler initialized")
        
    def __del__(self) -> None:
        """
        Destructor method that is called when the DataHandler object is about to be destroyed.
        It ensures that any open connections are closed properly and any resources
        are released.

        Raises:
            None
        """

        try:
            self.delete()
        except Exception as e:
            # For graceful closing no raise of exception is not allowed
            self._logger.error(f"Exception in destructor: {e}")
    
    def delete(self) -> None:
        """
        Deletes the DataHandler.

        Returns:
            None

        Raises:
            None
        """

        # Check if the DataHandler is already deleted
        if self._status == Status.DELETED:
            self._logger.warning("DataHandler already deleted")
            return
        
        self._logger.info("Deleting DataHandler ...")

        try:
            # Close the stream handlers and stop the ping process
            self._close_stream_handlers()
            self.stop_ping()
            # Log out from the XTB trading platform
            self._logout()
        except Exception as e:
            # For graceful closing no raise of exception is not allowed
            self._logger.error(f"Failed to delete DataHandler: {e}")
        finally:
            # Set Status to deleted
            self._status = Status.DELETED
            
        self._logger.info("DataHandler deleted")
            
    def _login(self) -> None:
        """
        Logs in to the XTB trading platform.

        Returns:
            None

        Raises:
            None
        """

        self._logger.info("Logging in ...")

        # Open the connection to the server
        self.open()

        # Locks out the ping process
        # To avoid conflicts with the login process
        # Could happen if relogin of running handler is necessary
        with self._ping_lock:
            # Send the login request to the server
            # No reactivation if request fails because the login method
            # is part of the reactivation method
            self.send_request(
                command='login',
                arguments={
                    'arguments': {
                        'userId': self._username,
                        'password': self._password
                    }
                }
            )
            # Receive the response from the server
            response = self.receive_response()

        self._logger.info("Log in successfully")
        self._ssid = response['streamSessionId']

        # DataHandler is now ready for usage
        self._status = Status.ACTIVE
                            
    def _logout(self) -> None:
        """
        Logs out from the XTB trading platform.

        Returns:
            None

        Raises:
            None
        """

        if not self._ssid:
            # Logged in clients have a stream session ID
            self._logger.warning("Already logged out")
        
        # Locks out the ping process
        # To avoid conflicts with the login process
        with self._ping_lock:
            try:
                self._logger.info("Logging out ...")
                # Send the logout request to the server
                # Server sends no response for logout request
                # No reactivation if request fails because the login method
                # is part of the reactivation method
                self.send_request(command='logout')
                self._logger.info("Logged out successfully")
            except Exception as e:
                # For graceful logout no raise of exception is not allowed
                self._logger.error(f"Could not log out: {e}")
            finally:
                # Close the socket
                self.close()
                # Delete the stream session ID 
                self._ssid=None
                # DataHandler no longer ready for usage
                self._status=Status.INACTIVE

    def get_data(self, command: str, **kwargs) -> dict:
        """
        Retrieves data from the server.

        Args:
            command (str): The command to retrieve data.
            **kwargs: Additional keyword arguments for the command.

        Returns:
            The retrieved data if successful.
        """

        if not self._ssid:
            self._logger.error("Got no StreamSessionId from Server")
            raise ValueError("Got no StreamSessionId from Server")
        
        # Try to retrieve the data twice
        # This enables a automatic reactivation if the first attempt fails
        for tries in range(2):
            try:
                # Retrieve the data for the specified command
                return  self._retrieve_data(command, **kwargs)
            except Exception as e:
                self._logger.error(f"Failed to retrieve data: {e}")
                if tries == 0:
                    # Reactivate the DataHandler if the first attempt fails
                    self._logger.info("Try a reactivation ...")
                    # Until reactivated the DataHandler is suspended
                    self._status = Status.SUSPENDED
                    self.reactivate()
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
            if 'returnData' not in response or not response['returnData']:
                self._logger.error("No data in response")
                raise ValueError("No data in response")
                
            # Log the successful retrieval of data in pretty format
            self._logger.info("Data for "+pretty(command) +" received")

            # Return the data
            return response['returnData']
 
    def reactivate(self) -> None:
        """
        Reactivates the DataHandler.

        This method is used to establish a new connection to the server in case the current connection is lost.

        Returns:
            None

        Raises:
            None
        """

        # In case a reactivation is already in progress,
        # by a connected stream handler
        # the lock is used to avoid conflicts
        with self._reactivation_lock:
            try:
                self._logger.info("Checking connection ...")
                # Check the socket
                self.check(mode='basic')
                self._logger.info("Connection is active")
                # The DataHandlerr seems to be active
                self._status = Status.ACTIVE
            except Exception as e:
                try:
                    self._logger.info("Reactivating ...")
                    # Create a new socket
                    self.create()
                    # Relogin to the server
                    # Sets the status automatically to active
                    self._login()
                    self._logger.info("Reactivation successful")
                except Exception as e:
                    self._logger.error(f"Failed to reactivate: {e}")
                    # Reactivation failed
                    self._status = Status.FAILED

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

        if handler not in self._stream_handler:
            self._stream_handler.append(handler)
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

        if handler in self._stream_handler:
            self._stream_handler.remove(handler)
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

        if not self._stream_handler:
            self._logger.info("No StreamHandlers to close")
        else:
            for handler in list(self._stream_handler):
                handler.delete()
                # detaching is only executed by StreamHandler itself

    @property
    def stream_handler(self) -> List['_StreamHandler']:
        return self._stream_handler
    
    @property
    def reactivation_lock(self) -> Lock:
        return self._reactivation_lock
    
    @property
    def status(self) -> Status:
        return self._status
    
    @property
    def ssid(self) -> str:
        return self._ssid


class _StreamHandler(_GeneralHandler):
    """
    Handles stream requests to and from the XTB trading platform.

    Attributes:
        _logger (logging.Logger): The logger object used for logging.
        _dh (_DataHandler): The data handler object.
        _status (Status): The status of the stream handler.
        _stream (dict): The stream dictionary.
        _stream_tasks (dict): The dictionary of stream tasks.
        _stop_lock (Lock): The lock for stopping the stream.
        _ssid (str): The stream session ID.

    Methods:
        delete: Deletes the StreamHandler.
        stream_data: Starts streaming data from the server.
        _start_stream: Starts the stream for the specified command.
        _export_stream: Exports the stream data.
        _receive_stream: Receives the stream data.
        _stop_task: Stops the stream task.
        _stop_stream: Stops the stream.
        _restart_stream: Restarts the stream.
        _reactivate: Reactivates the StreamHandler.
        transplant_stream_task: Transplants the stream tasks from another StreamHandler.

    Properties:
        dh: The data handler object.
        status: The status of the stream handler.
        ssid: The stream session ID.
        sm_idle_time: The sliding mean idle time.
    """

    def __init__(
        self,
        data_handler: _DataHandler,
        demo: bool,

        max_send_data: int,
        max_received_data: int,
        min_request_interval: int,
        max_retries: int,
        max_reaction_time: int,

        logger: Optional[logging.Logger] = None
        ) -> None:
        """
        Initializes a new instance of the StreamHandler class.

        Args:
            data_handler (_DataHandler): The data handler object.
            demo (bool): A boolean indicating whether the handler is for demo or real trading.
            max_send_data (int): The maximum number of bytes to send.
            max_received_data (int): The maximum number of bytes to receive.
            min_request_interval (int): The minimum request interval in seconds.
            max_retries (int): The maximum number of retries.
            max_reaction_time (int): The maximum reaction time in seconds.
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
            stream=True,

            max_send_data = max_send_data,
            max_received_data = max_received_data,
            min_request_interval = min_request_interval,
            max_retries = max_retries,
            max_reaction_time = max_reaction_time,

            logger=self._logger
        )

        # Attach the StreamHandler to the DataHandler
        self._dh = data_handler
        self._dh.attach_stream_handler(self)

        # Open connection to the server
        self.open()

        # Set the status to active
        # StreamHandler need no login
        # so the status is active right after the connection is open
        self._status = Status.ACTIVE

        # The dictionary for the thread control of the stream
        self._stream=dict()
        # Stream tasks are stored in a dictionary
        self._stream_tasks = dict()
        # Lock for stopping a stream task
        self._stop_lock = Lock()

        # The idle time list
        self._idle_times = List[float]
        # The sliding mean idle time
        self._sm_idle_time = 0

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
        It ensures that any open connections are closed properly and any resources
        are released.

        Raises:
            None
        """
        
        try:
            self.delete()
        except Exception as e:
            # For graceful closing no raise of exception is not allowed
            self._logger.error(f"Exception in destructor: {e}")
            
    def delete(self) -> None:
        """
        Deletes the StreamHandler.

        Returns:
            None

        Raises:
            None
        """

        if self._status == Status.DELETED:
            self._logger.warning("StreamHandler already deleted")
            return
        
        self._logger.info("Deleting StreamHandler ...")

        try:
            # Stop the stream and ping processes
            self._stop_stream()
            self.stop_ping()
            # Detach the StreamHandler from the DataHandler
            self._dh.detach_stream_handler(self)
        except Exception as e:
            # For graceful closing no raise of exception is not allowed
            self._logger.error(f"Failed to delete StreamHandler: {e}")
        finally:
            # Close the connection to the server
            self.close()
            # Set Status to deleted
            self._status= Status.DELETED
        
            self._logger.info("StreamHandler deleted")
        
    def stream_data(
        self,
        command: str,
        exchange: Optional[dict] = None, # Not necessary for KeepAlive
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
        if not self._dh.ssid:
            self._logger.error("DataHandler got no StreamSessionId from Server")
            raise ValueError("DataHandler got no StreamSessionId from Server")
        
        # Check if the specific stream is already open
        for index in self._stream_tasks:
            if self._stream_tasks[index]['command'] == command and self._stream_tasks[index]['arguments'] == kwargs:
                self._logger.warning("Stream for data already open")
                raise ValueError("Stream for data already open")
            
        # Start the stream for the specified command
        self._start_stream(command, **kwargs)
        
        # Initiate the stream thread for the handler
        if not self._stream:
            # Set the run flag for the stream on true
            self._stream['run'] = True
            # Create a new thread for the stream
            self._stream['thread'] = CustomThread(
                target=self._export_stream,
                daemon=True
            )
            # Start the stream thread
            self._stream['thread'].start()

            # Create the thread monitor for the stream thread
            monitor_thread = CustomThread(
                target=self.thread_monitor,
                args=('Stream', self._stream, self._reactivate,),
                daemon=True
            )
            # Start the thread monitor
            monitor_thread.start()

        # Register the stream task
        index = len(self._stream_tasks)
        self._stream_tasks[index] = {'command': command, 'arguments': kwargs}

        # The data from the KeepAlive command is unnecessary
        if command != 'KeepAlive':
            # Put a killswitch for the stream task into the exchange dictionary
            exchange['thread'] = CustomThread(
                target=self._stop_task,
                args=(index,),
                daemon=True
            )
            # Put the queue for the exchange into the exchange dictionary
            exchange['queue'] = Queue(maxsize=1000)

            # The data from the stream is put into the queue for the exchange
            self._stream_tasks[index]['queue'] = exchange['queue']

            # Store the exchange dictionary in the stream task
            # In case the stream task has to switch the StreamHandler
            self._stream_tasks[index]['exchange'] = exchange


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
            self._ssid = self._dh.ssid

            # Try to start the stream twice
            # This enables a automatic reactivation if the first attempt fails
            for tries in range(2):
                try:
                    # Send the request for the stream to the server
                    self.send_request(
                        command='get'+command,
                        ssid=self._ssid,
                        arguments=kwargs if bool(kwargs) else None
                    )
                except Exception as e:
                    self._logger.error(f"Failed to start stream: {e}")
                    if tries == 0:
                        # Reactivateif the first attempt fails
                        self._logger.info("Try a reactivation ...")
                        # Until reactivated the DataHandler is suspended
                        self._status = Status.SUSPENDED
                        self._reactivate()
                    else:
                        # If the stream could not be started, raise an error
                        self._logger.error(f"Failed to start stream {e}")
                        raise
 
    def _export_stream(self) -> None:
        """
        Exports the stream data to the exchange.

        Returns:
            None

        Raises:
            None
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
            # Start timer
            start_time = time.time()

            self._logger.info("Streaming data ...")
    
            # Get the stream data from the server
            response = self._receive_stream()

            # Calculate idle time
            idle_time = time() - start_time
            total_idle_time += idle_time

            if response == {}:
                # Stream responses can be empty
                continue

            if response['command'] == 'KeepAlive':
                # KeepAlive stream is not necessary for the exchange
                continue

            # Reset the idle time
            self._calculate_sm_idle_time(total_idle_time)
            total_idle_time = 0

            # Assign streamed data to the corresponding stream task
            for index in self._stream_tasks:
                command = self._stream_tasks[index]['command']
                arguments = self._stream_tasks[index]['arguments']
                
                # Skip if the command does not match
                if translate[command] != response['command']:
                    continue

                # Not just the command but also the arguments must match
                # symbol is the only additional argument that could be passed
                if 'symbol' in response['data']:
                    if set(arguments['symbol']) != set(response['data']['symbol']):
                        continue
                
                self._logger.info("Data received for " + pretty(command))

                # Put the data into the queue for the exchange
                self._stream_tasks[index]['queue'].put(response['data'])

        self._logger.info("All streams stopped")

    def _calculate_sm_idle_time(self, idle_time: float) -> None:
        """
        Calculates the sliding mean idle time for the stream.

        Args:
            idle_time (float): The last idle time.

        Returns:
            None

        Raises:
            None
        """

        # Sliding mean idle time is calculated
        # by the last 10 idle times
        self._idle_times.append(idle_time)
        if len(self._idle_times) > SM_INTERVAL:
            self._idle_times.pop(0)

        # Calculate the mean idle time
        self._sm_idle_time = mean(self._idle_times)

    def _receive_stream(self) -> dict:
        """
        Receives the stream data from the server.

        Returns:
            The stream data as a dictionary.

        Raises:
            ValueError: If the response does not contain a command key.
            ValueError: If the response does not contain a data key.
        """

        self._logger.info("Getting stream data ...")

        # Locks out the ping process
        # To avoid conflicts with the receive process
        with self._ping_lock:
            # Try to get the stream data twice
            # This enables a automatic reactivation if the first attempt fails
            for tries in range(2):
                try:
                    # Receive the response from the server
                    response = self.receive_response(stream=True)
                except Exception as e:
                    self._logger.error(f"Failed to stream data: {e}")
                    if tries == 0:
                        # Reactivateif the first attempt fails
                        self._logger.info("Try a reactivation ...")
                        # Until reactivated the DataHandler is suspended
                        self._status = Status.SUSPENDED
                        self._reactivate()
                    else:
                        # If the stream data could not be received, raise an error
                        self._logger.error(f"Failed to stream data {e}")
                        raise

        if response == {}:
            # Stream responses can be empty
            return response

        # Response must contain 'command' key with command
        if 'command' not in response:
            self._logger.error("No command in response")
            raise ValueError("No command in response")

        # Response must contain 'data' key with data
        if 'data' not in response:
            self._logger.error("No data in response")
            raise ValueError("No data in response")

        self._logger.info("Stream data received")

        # Return the stream data
        return response

    def _stop_task(self, index: int, kill: bool=True) -> None:
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
            if index in self._stream_tasks:
                command = self._stream_tasks[index]['command']
                arguments = self._stream_tasks[index]['arguments']

                self._logger.info("Stopping stream for " + pretty(command) + " ...")

                # Locks out the ping process
                # To avoid conflicts with the stop request
                with self._ping_lock:
                    # Send the stop request to the server
                    self.send_request(
                        command='stop' + command,
                        arguments={'symbol': arguments['symbol']} if 'symbol' in arguments else None
                    )

                if kill:
                    # Deregister the stream task
                    del self._stream_tasks[index]
                    
    def _stop_stream(self, kill: bool=True) -> None:
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
            self._stream['thread'].join(timeout=THREAD_TICKER*5)

        # Stop all stream tasks
        for index in list(self._stream_tasks):
            self._stop_task(index=index, kill=kill)
            
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
        for index in list(self._stream_tasks):
            command=self._stream_tasks[index]['command']
            kwargs=self._stream_tasks[index]['arguments']
            self._start_stream(command,**kwargs)

        self._logger.info("All streams restarted")

    def _reactivate(self) -> None:
        """
        Reactivates the StreamHandler to the DataHandler.

        Returns:
            None

        Raises:
            None
        """

        # Check if reactivation of the DataHandler is already in progress
        # either by the DataHandler itself or another StreamHandler
        if self._dh.reactivation_lock.acquire(blocking=False):
            # If the DataHandler is not already reactivated
            # the StreamHandler can initiate a reactivation
            try:
                # Reactivate the DataHandler
                self._dh.reactivate()
            except Exception as e:
                self._logger.error(f"Failed to reactivate DataHandler: {e}")
                raise
            finally:
                # Release the lock after the reactivationis done
                self._dh.reactivation_lock.release()
        else:
            # If the lock couldnt be acquired, the Streamhandler stops
            # the reactivation process immediately
            self._logger.info("Reactivation attempt for DataHandler is already in progress by another StreamHandler.")

        # Wait for the DataHandler to reactivate
        with self._dh.reactivation_lock:
            try:
                self._logger.info("Checking connection ...")
                # Check the socket
                self.check('basic')
                self._logger.info("Connection is active")
                # The StreamHandler seems to be active
                self._status=Status.ACTIVE
            except Exception as e:
                try:
                    self._logger.info("Reactivating ...")
                    # Create a new socket
                    self.create()
                    # Open the connection
                    self.open()
                    # Restart the stream tasks
                    self._restart_streams()
                    # Set the status to active
                    self._status=Status.ACTIVE
                    self._logger.info("Reactivation successful")
                except Exception as e:
                    self._logger.error(f"Failed to reactivate: {e}")
                    # Set the status to failed
                    self._status = Status.FAILED

    def transplant_stream_task(self, task: dict) -> None:
        """
        Transplants the stream tasks from another StreamHandler.

        Args:
            task (dict): The task to transplant.

        Returns:
            None

        Raises:
            None
        """

        self._logger.info("Transplanting stream tasks ...")

        # Extract the necessary information from the task
        command = task['command']
        arguments = task['arguments']
        exchange = task['exchange']

        # Start the stream for the specified command
        self.stream_data(
            command=command,
            exchange=exchange,
            **arguments
        )

        self._logger.info("Stream tasks transplanted")

    @property
    def dh(self) -> _DataHandler:
        return self._dh

    @dh.setter
    def dh(self, value: _DataHandler) -> None:
        # Shut down the StreamHandler
        self._stop_stream(kill=False)
        self.stop_ping()
        self.close()
        self._dh.detach_stream_handler(self)

        # Change the DataHandler
        self._dh = value

        # Boot up the StreamHandler
        self._dh.attach_stream_handler(self)
        self.open()
        self._restart_streams()
        self.start_ping(handler=self)
    
    @property
    def status(self) -> Status:
        return self._status

    @property
    def stream_tasks(self) -> dict:
        return self._stream_tasks
    
    @property
    def sm_idle_time(self) -> float:
        return self._sm_idle_time

class HandlerManager():
    """
    Manages the handlers for the XTB trading platform.

    Attributes:
        _logger (logging.Logger): The logger object used for logging.
        _demo (bool): A boolean indicating whether the handlers are for demo or real trading.
        _username (str): The username for the XTB trading platform.
        _password (str): The password for the XTB trading platform.
        _max_connections (int): The maximum number of connections to the server allowed at the same time.
        _max_send_data (int): The maximum number of bytes to send.
        _max_received_data (int): The maximum number of bytes to receive.
        _min_request_interval (int): The minimum request interval in seconds.
        _max_retries (int): The maximum number of retries.
        _max_reaction_time (int): The maximum reaction time in seconds.
        _handler_register (dict): The dictionary of registered handlers.
        _status (Status): The status of the handler manager.
        _handler_management_thread (CustomThread): The handler management thread.

    Methods:
        delete: Deletes the HandlerManager instance.
        _delete_handler: Deletes a specific handler and deregisters it from the HandlerManager..
        _avlb_DataHandler: Gets an available data handler.
        _avlb_StreamHandler: Gets an available stream handler.
        _get_connection_number: Gets the number of active connections.
        _generate_DataHandler: Generates a new data handler.
        _generate_StreamHandler: Generates a new stream handler.
        _provide_DataHandler: Provides a data handler for the stream handler.
        _provide_StreamHandler: Provides a stream handler for the data handler.
        get_data: Retrieves data from the server.
        stream_data: Starts streaming data from the server.
        _healthcheck: Checks the health of the handlers.
    """
        

    def __init__(
        self,
        
        max_connections: int,
        max_send_data: int,
        max_received_data: int,
        min_request_interval: float,
        max_retries: int,
        max_reaction_time: float,

        demo: bool=True,

        username: Optional[str]=None,
        password: Optional[str]=None,
        path: Optional[str]=None,

        logger: Optional[logging.Logger]=None
        ) -> None:
        """
        Initializes a new instance of the HandlerManager class.

        Args:
            max_connections (int): The maximum number of connections to the server allowed at the same time.
            max_send_data (int): The maximum number of bytes to send.
            max_received_data (int): The maximum number of bytes to receive.
            min_request_interval (int): The minimum request interval in seconds.
            max_retries (int): The maximum number of retries.
            max_reaction_time (int): The maximum reaction time in seconds.
            demo (bool, optional): Specifies whether the handlers are for demo purposes. Defaults to True.
            username (str, optional): The username for the XTB trading platform. Defaults to None.
            password (str, optional): The password for the XTB trading platform. Defaults to None.
            path (str, optional): The path to the XTB API credentials file. Defaults to None.
            logger (logging.Logger, optional): The logger instance to use for logging. Defaults to None.

        Raises:
            None
        """
        
        if logger:
            # Use the provided logger
            self._logger = logger
        else:
            # Generate a new logger
            self._logger=generate_logger(name='HandlerManager', path=Path.cwd() / "logs")

        self._logger.info("Initializing HandlerManager ...")

        self._demo=demo

        # Check if username and password are provided
        if username and password:
            # Set the username and password
            self._username=username
            self._password=password
        else:
            # Sets the path to the credentials file
            if path:
                set_path(path = path)

            # Get the username and password from the config file
            self._username=get_userId(self._demo)
            self._password=get_password()

        self._max_connections=max_connections
        self._max_send_data=max_send_data
        self._max_received_data=max_received_data
        self._min_request_interval=min_request_interval
        self._max_retries=max_retries
        self._max_reaction_time=max_reaction_time

        # Initialize the handlers dictionary
        self._handler_register = {'data': {}, 'stream': {}}

        # The HandlerManager is automatically active after initialization
        self._status = Status.ACTIVE

        # Start the handler management thread
        self._handler_management_thread = CustomThread(
            target=self._healthcheck,
            daemon=True
        )

        self._logger.info("HandlerManager initialized")

    def __del__(self) -> None:
        """
        Destructor method that is called when the HandlerManager object is about to be destroyed.
        It ensures that any open connections are closed properly and any resources
        are released.

        Raises:
            None
        """

        try:
            self.delete()
        except Exception as e:
            # For graceful closing no raise of exception is not allowed
            self._logger.error(f"Exception in destructor: {e}")

    def delete(self) -> None:
        """
        Deletes the HandlerManager instance and all associated handlers.

        Returns:
            None

        Raises:
            None
        """

        if self._status == Status.DELETED:
            self._logger.warning("HandlerManager already deleted")
            return
        
        self._logger.info("Deleting HandlerManager ...")
        
        for handler in self._handler_register['data']:
            # Delete all data handlers
            # The DataHandler wil send a delete command to every attached StreamHandler
            if handler.status != Status.DELETED:
                self._delete_handler(handler)

        # Set the deleted flag to True
        self._status = Status.DELETED

        # Wait for the handler management thread to stop
        self._handler_management_thread.join(timeout=THREAD_TICKER*5)

        self._logger.info("HandlerManager deleted")
    
    def _delete_handler(self, handler: Union[_DataHandler, _StreamHandler]) -> None:
        """
        Deletes a specific handler and deregisters it from the HandlerManager.

        Args:
            handler (Union[_DataHandler, _StreamHandler]): The handler to delete.

        Returns:
            None
        """

        if isinstance(handler, _DataHandler):
            self._logger.info("Deregister DataHandler "+self._handler_register['data'][handler]['name'])
            del self._handler_register['data'][handler]
        elif isinstance(handler, _StreamHandler):
            self._logger.info("Deregister StreamHandler "+self._handler_register['stream'][handler]['name'])
            del self._handler_register['stream'][handler]

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

        for handler in self._handler_register['data']:
            # Check if the handler is active
            if handler.status == Status.ACTIVE:
                return handler
    
    def _avlb_StreamHandler(self) -> _StreamHandler:
        """
        Gets an available stream handler.

        Returns:
            _StreamHandler: An available StreamHandler if found.

        Raises:
            None
        """

        for handler in self._handler_register['stream']:
            # Check if the handler is active
            # and the idle time is above the threshold
            if handler.status == Status.ACTIVE and handler.sm_idle_time > IDLE_THRESHOLD:
                return handler

    def _get_connection_number(self) -> int:
        """
        Gets the number of active connections.

        Returns:
            int: The number of active connections.

        Raises:
            None
        """

        return len(self._handler_register['data']) + len(self._handler_register['stream'])

    def _generate_DataHandler(self) -> _DataHandler:
        """
        Generates a new data handler.

        Returns:
            _DataHandler: A new DataHandler.

        Raises:
            RuntimeError: If the maximum number of connections is reached.
            RuntimeError: If the DataHandler is not ready for usage.
        """

        self._logger.info("Generating DataHandler ...")

        if self._get_connection_number() >= self._max_connections:
            self._logger.error("Maximum number of connections reached")
            raise RuntimeError("Maximum number of connections reached")

        # Index the new DataHandler
        index = len(self._handler_register['data'])
        name = 'DH_' + str(index)
        dh_logger = self._logger.getChild(name)

        # Create the new DataHandler
        dh = _DataHandler(
            demo=self._demo,

            username=self._username,
            password=self._password,

            max_send_data=self._max_send_data,
            max_received_data=self._max_received_data,
            min_request_interval=self._min_request_interval,
            max_retries=self._max_retries,
            max_reaction_time=self._max_reaction_time,

            logger=dh_logger
        )

        # Check if the initialization of the DataHandler was successful
        if dh.status != Status.ACTIVE:
            self._logger.error("DataHandler not ready for usage")
            raise RuntimeError("DataHandler not ready for usage")

        # Register the new DataHandler
        self._handler_register['data'][dh] = {'name': name}

        self._logger.info("DataHandler generated")

        return dh

    def _generate_StreamHandler(self) -> _StreamHandler:
        """
        Generates a new stream handler.

        Returns:
            _StreamHandler: A new StreamHandler.

        Raises:
            RuntimeError: If the maximum number of connections is reached.
            RuntimeError: If the StreamHandler is not ready for usage.
        """

        self._logger.info("Generating StreamHandler ...")

        if self._get_connection_number() >= self._max_connections:
            self._logger.error("Maximum number of connections reached")
            raise RuntimeError("Maximum number of connections reached")

        # Index the new StreamHandler
        index = len(self._handler_register['stream'])
        name = 'SH_' + str(index)
        sh_logger = self._logger.getChild(name)

        # Create the new StreamHandler
        dh = self._provide_DataHandler()
        sh = _StreamHandler(
            data_handler=dh,
            demo=self._demo,

            max_send_data=self._max_send_data,
            max_received_data=self._max_received_data,
            min_request_interval=self._min_request_interval,
            max_retries=self._max_retries,
            max_reaction_time=self._max_reaction_time,

            logger=sh_logger
        )

        # Check if the initialization of the StreamHandler was successful
        if sh.status != Status.ACTIVE:
            self._logger.error("StreamHandler not ready for usage")
            raise RuntimeError("StreamHandler not ready for usage")

        # Register the new StreamHandler
        self._handler_register['stream'][sh] = {'name': name}

        self._logger.info("StreamHandler generated")

        return sh

    def _provide_DataHandler(self) -> _DataHandler:
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

    def _provide_StreamHandler(self) -> _StreamHandler:
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
    
    def get_data(
        self,
        command: str,
        **kwargs
        ) -> dict:
        """
        Retrieves data from the server.

        Args:
            command (str): The command to get data.
            **kwargs: Additional keyword arguments for the command.

        Returns:
            dict: The data from the server.

        Raises:
            None
        """

        # Provide a new DataHandler that is ready for usage
        dh = self._provide_DataHandler()

        # Get the data from the server
        data = dh.get_data(command=command, **kwargs)

        return data

    def stream_data(
        self,
        command: str,
        exchange: Optional[dict] = None,
        **kwargs
        ) -> None:
        """
        Starts streaming data from the server.

        Args:
            command (str): The command to start streaming data.
            exchange (dict, optional): The exchange information. Defaults to None.
            **kwargs: Additional keyword arguments for the command.

        Returns:
            None

        Raises:
            None
        """

        # Provide a new StreamHandler that is ready for usage
        sh = self._provide_StreamHandler()

        # Start the stream for the specified command
        sh.stream_data(command=command, exchange=exchange, **kwargs)

    def _healthcheck(self) -> None:
        """
        Manages the handlers and ensures that the maximum number of connections is not exceeded.

        Returns:
            None

        Raises:
            None
        """

        while self._status == Status.ACTIVE:
            for handler in self._handler_register['data']:
                # Check if the handler is failed
                if handler.status == Status.FAILED:
                    # Check for connected stream handlers
                    if len(handler.stream_handler) > 0:
                        # Provide a new DataHandler that is ready for usage
                        dh_new = self._provide_DataHandler()
                        if dh_new:
                            # Assign the new DataHandler to the connected stream handlers
                            for sh in handler.stream_handler:
                                sh.dh = dh_new
                        else:
                            self._logger.error("No DataHandler available")
                    # Eventually delete the handler
                    self._delete_handler(handler)

            for handler in self._handler_register['stream']:
                # Check if the handler is failed
                if handler.status == Status.FAILED:
                    # Check for open stream tasks
                    if len(handler.stream_tasks) > 0:
                        for _, task in handler.stream_tasks.items():
                            # Provide a new StreamHandler that is ready for usage
                            sh_new = self._provide_StreamHandler()
                            if sh_new:
                                # Assign the new StreamHandler to the stream tasks
                                sh_new.transplant_stream_tasks(task)
                            else:
                                self._logger.error("No StreamHandler available")
                    # Eventually delete the handler
                    self._delete_handler(handler)

            time.sleep(THREAD_TICKER)