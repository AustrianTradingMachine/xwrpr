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
from xwrpr.client import Client
from xwrpr.utils import pretty ,generate_logger, CustomThread
from xwrpr.account import get_userId, get_password


# read api configuration
config = configparser.ConfigParser()
config_path=Path(__file__).parent.absolute()/ 'api.ini'
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

class _GeneralHandler(Client):
    """
    A class that handles general requests and responses.

    Attributes:
        _logger (logging.Logger): The logger instance.
        _host (str): The host address.
        _port (int): The port number.
        _stream (bool): A flag indicating whether to use streaming.
        _encrypted (bool): A flag indicating whether the connection is encrypted.
        _interval (float): The interval between sending requests.
        _max_fails (int): The maximum number of connection fails.
        _bytes_out (int): The maximum number of bytes to send.
        _bytes_in (int): The maximum number of bytes to receive.
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

    def __init__(self, host: str, port: int, stream: bool, logger=None):
        """
        Initializes the Handler object.

        Args:
            host (str): The host address.
            port (int): The port number.
            stream (bool): Indicates whether to use streaming or not.
            logger (logging.Logger, optional): The logger object. Defaults to None.
        
        Raises:
            ValueError: If the logger argument is provided but is not an instance of logging.Logger.
        """
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='GeneralHandler', path=Path.cwd() / "logs")

        self._host=host
        self._port=port
        self._stream=stream

        self._encrypted=True
        self._interval=SEND_INTERVAL/1000
        self._max_fails=MAX_CONNECTION_FAILS
        self._bytes_out=MAX_SEND_DATA
        self._bytes_in=MAX_RECIEVE_DATA

        super().__init__(host=self._host, port=self._port,  encrypted=self._encrypted, timeout=None, interval=self._interval, max_fails=self._max_fails, bytes_out=self._bytes_out, bytes_in=self._bytes_in, stream = self._stream, logger=self._logger)

        self._call_reconnect=None
        
        self._ping=dict()
        self._ping_lock = Lock()
    
    def send_request(self, command: str, ssid: str = None, arguments: dict = None, tag: str = None):
        """
        Sends a request to the server.

        Args:
            command (str): The command to send.
            ssid (str, optional): The stream session ID. Defaults to None.
            arguments (dict, optional): Additional arguments for the request. Defaults to None.
            tag (str, optional): A custom tag for the request. Defaults to None.

        Returns:
            bool: True if the request was sent successfully, False otherwise.
        """
        self._logger.info("Sending request ...")

        request = dict([('command', command)])

        if ssid is not None:
            request['streamSessionId'] = ssid
        if arguments is not None:
            request.update(arguments)
        if tag is not None:
            request['customTag'] = tag

        if not self.send(request):
            self._logger.error("Failed to send request")
            return False
        else:
            if command == 'login':
                request['arguments']['userId'] = '*****'
                request['arguments']['password'] = '*****'
            self._logger.info("Sent request: " + str(request))
            return True

    def receive_response(self, data: bool = True):
        """
        Receives a response from the server.

        Args:
            data (bool): Flag indicating whether to process the response data. Default is True.

        Returns:
            dict or bool: The received response as a dictionary if `data` is True and the response is valid,
                          otherwise False.

        """
        self._logger.info("Receiving response ...")

        response = self.receive()

        if not response:
            self._logger.error("Failed to receive response")
            return False
        
        self._logger.info("Received response: " + str(response)[:100] + ('...' if len(str(response)) > 100 else ''))

        if not isinstance(response, dict):
            self._logger.error("Response not a dictionary")
            return False

        if data:
            if not 'status' in response:
                self._logger.error("Response corrupted")
                return False

            if not response['status']:
                self._logger.error("Request failed")
                self._logger.error(response['errorCode'])
                self._logger.error(response['errorDescr'])
                return False

        return response
    
    def thread_monitor(self, name: str, thread_data: dict, reconnect=None):
        """
        Monitors the specified thread and handles reconnection if necessary.

        Args:
            name (str): The name of the thread being monitored.
            thread_data (dict): A dictionary containing information about the thread.
            reconnect (callable, optional): A method to be called for reconnection. Defaults to None.

        Raises:
            ValueError: If the reconnect parameter is provided but is not callable.

        Returns:
            None
        """
        if reconnect:
            if not callable(reconnect):
                raise ValueError("Reconnection method not callable")

        self._logger.info("Monitoring thread for " + name + " ...")

        while thread_data['run']:
            if thread_data['thread'].is_alive():
                continue

            # must be checked again because of thread asynchronity
            if not thread_data['run']:
                break

            self._logger.error("Thread for " + name + " died")
            if reconnect:
                reconnect()
            
            self._logger.error("Restarting thread for " + name + " ...")
            dead_thread=thread_data['thread']
            thread_data['thread'] = CustomThread(target=dead_thread._target, args=dead_thread._args, daemon=dead_thread._daemon, kwargs=dead_thread.kwargs)
            thread_data['thread'].start()

            time.sleep(self._interval)

        self._logger.info("Monitoring for thread " + name + " stopped")

    def start_ping(self, handler):
        """
        Starts the ping functionality.

        Args:
            handler: The handler object.

        Returns:
            bool: True if the ping is started successfully, False otherwise.
        """
        self._logger.info("Starting ping ...")

        self._ping['run'] = True
        self._ping['thread'] = CustomThread(target=self._send_ping, args=(handler,self._ping), daemon=True)
        self._ping['thread'].start()
        self._logger.info("Ping started")

        monitor_thread = CustomThread(target=self.thread_monitor, args=('Ping', self._ping, handler._reconnect,), daemon=True)
        monitor_thread.start()

        return True

    def _send_ping(self, handler, thread_data):
        """
        Sends ping requests to the server.

        Args:
            handler: The handler instance.
            run: A flag indicating whether the ping process should continue running.

        Returns:
            bool: False if the ping failed.
        """
        # sends ping all 10 minutes
        ping_interval = 60*9.9
        next_ping=0
        check_interval=self._interval/10

        while thread_data['run']:
            start_time = time.time()
            if next_ping >= ping_interval:
                # thanks to th with statement the ping could fail to keep is sheduled interval
                # but thats not important because this is just the maximal needed interval and
                # a function that locks the ping_key also initiates a reset to the server
                with self._ping_lock:
                    # dynamic allocation of ssid for StreamHandler
                    if isinstance(handler, _StreamHandler):
                        ssid = handler._dh._ssid
                    else:
                        ssid = None

                    if not self.send_request(command='ping', ssid=ssid):
                        self._logger.error("Ping failed")
                        return False

                    if not ssid:
                        if not self.receive_response(data = True):
                            self._logger.error("Ping failed")
                            return False

                    self._logger.info("Ping")
                    next_ping = 0

            time.sleep(check_interval)
            next_ping += time.time() - start_time

        self._logger.info("Ping stopped")

    def stop_ping(self):
        """
        Stops the ping process.

        Returns:
            bool: True if the ping process was stopped successfully, False otherwise.
        """
        self._logger.info("Stopping ping ...")

        if not self._ping:
            self._logger.error("Ping never started")
            return False
            
        if not self._ping['run']:
            self._logger.warning("Ping already stopped")
        else:
            self._ping['run'] = False

        self._ping['thread'].join()

        return True
    
class _DataHandler(_GeneralHandler):
    """
    Handles data-related operations for the XTB trading platform.

    Attributes:
        _demo (bool): Indicates whether the handler is for the demo mode or not.
        _host (str): The host address for the XTB trading platform.
        _port (int): The port number for the XTB trading platform.
        _userid (str): The user ID for the XTB trading platform.
        _logger (logging.Logger): The logger instance used for logging.
        _stream_handlers (list): A list of attached stream handlers.
        _reconnect_lock (threading.Lock): A lock used for thread safety during reconnection.
        _status (str): The status of the data handler ('active', 'inactive', or 'deleted').
        _ssid (str): The stream session ID received from the server.

    Methods:
        delete: Deletes the DataHandler.
        _login: Logs in to the XTB trading platform.
        _logout: Logs out the user from the XTB trading platform.
        getData: Retrieves data from the server.
        _retrieve_data: Retrieves data for the specified command.
        _reconnect: Reconnects to the server.
        _attach_stream_handler: Attaches a stream handler to the logger.
        _detach_stream_handler: Detaches a stream handler from the logger.
        _close_stream_handlers: Closes the stream handlers.
        get_status: Returns the status of the handler.
        get_StreamHandler: Returns the stream handlers associated with the XTB handler.
        get_demo: Returns the demo mode.
        set_demo: Sets the demo mode.
        get_logger: Returns the logger instance.
        set_logger: Sets the logger instance.

    """

    def __init__(self, demo: bool, logger=None):
        """
        Initializes the DataHandler object.

        Args:
            demo (bool): Specifies whether the DataHandler is for demo or real trading.
            logger (logging.Logger, optional): The logger object to use for logging. If not provided, a new logger will be generated.

        Raises:
            ValueError: If the logger argument is provided but is not an instance of logging.Logger.
        """
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='DataHandler', path=Path.cwd() / "logs")

        self._demo=demo

        self._host=HOST
        if self._demo:
            self._port=PORT_DEMO
        else:
            self._port=PORT_REAL

        self._logger.info("Creating DataHandler ...")

        super().__init__(host=self._host, port=self._port, stream = False, logger=self._logger)
        
        self._stream_handlers=[]
        self._reconnect_lock=Lock()

        self._status=None
        self._ssid=None
        self._login()

        # starts ping to keep connection open
        self.start_ping(handler=self)

        self._logger.info("DataHandler created")
        
    def __del__(self):
        """
        Destructor method for the Handler class.
        Deletes the instance of the Handler object.
        """
        self.delete()
    
    def delete(self):
        """
        Deletes the DataHandler.

        If the DataHandler is already deleted, an error message is logged and the method returns True.
        Otherwise, the DataHandler is deleted by closing stream handlers, stopping ping, logging out, and updating the status.
        Finally, a success message is logged and the method returns True.

        Returns:
            bool: True if the DataHandler is successfully deleted, False otherwise.
        """
        if self._status == 'deleted':
            self._logger.warning("DataHandler already deleted")
            return True

        self._logger.info("Deleting DataHandler ...")

        self._close_stream_handlers()
        self.stop_ping()
        self._logout()
        self._status = 'deleted'
            
        self._logger.info("DataHandler deleted")
        
        return True
            
    def _login(self):
        """
        Logs in to the XTB trading platform.

        Returns:
            bool: True if login is successful, False otherwise.
        """
        # No reconnection because login is part of reconnection routine
        self._logger.info("Logging in ...")

        if not self.open():
            self._logger.error("Log in failed")
            return False
            
        with self._ping_lock:
            if not self.send_request(command='login', arguments={'arguments': {'userId': get_userId(self._demo), 'password': get_password()}}):
                self._logger.error("Log in failed")
                return False
            
            response = self.receive_response(data=True)
            if not response:
                self._logger.error("Log in failed")
                return False

        self._logger.info("Log in successfully")
        self._ssid = response['streamSessionId']

        self._status = 'active'
                            
        return True

    def _logout(self):
        """
        Logs out the user from the XTB trading platform.

        Returns:
            bool: True if the logout was successful, False otherwise.
        """
        # no false return function must run through
        # No reconnection because login is undesirable

        if not self._ssid:
            self._logger.warning("Already logged out")
            
        with self._ping_lock:
            self._logger.info("Logging out ...")

            if not self.send_request(command='logout'):
                self._logger.error("Log out failed")
            
            response=self.receive_response(data = True)
            if not response:
                self._logger.error("Log out failed")

        self._logger.info("Logged out successfully")

        if not self.close():
            self._logger.error("Could not close connection")
            
        self._ssid=None
        self._status='inactive'

        return True

    def getData(self, command: str, **kwargs):
        """
        Retrieves data from the server.

        Args:
            command (str): The command to retrieve data.
            **kwargs: Additional keyword arguments for the command.

        Returns:
            The retrieved data if successful, False otherwise.
        """
        if not self._ssid:
            self._logger.error("Got no StreamSessionId from Server")
            return False
        
        for tries in range(2):
            response = self._retrieve_data(command, **kwargs)

            if response:
                return response
            elif tries == 0:
                self._reconnect()
                
        self._logger.error("Failed to retrieve data")
        return False

    def _retrieve_data(self, command: str, **kwargs):
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
        with self._ping_lock:
            self._logger.info("Getting data for " + pretty(command) + " ...")

            if not self.send_request(command='get'+command, arguments={'arguments': kwargs} if bool(kwargs) else None):
                self._logger.error("Request for data not possible")
                return False 
                
            response = self.receive_response(data=True)
            if not response:
                self._logger.error("No data received")
                return False
            
            if not 'returnData' in response:
                self._logger.error("No data in response")
                return False
                
            self._logger.info("Data for "+pretty(command) +" recieved")

            return response['returnData']
 
    def _reconnect(self):
        """
        Reconnects to the server.

        This method is used to establish a new connection to the server in case the current connection is lost.

        Returns:
            The result of the `_reconnect_sub` method.
        """
        with self._reconnect_lock:   
            return self._reconnect_sub()
    
    def _reconnect_sub(self):
        """
        Reconnects the data connection.

        This method attempts to reconnect the data connection.

        Returns:
            bool: True if the reconnection is successful, False otherwise.
        """
        self._status = 'inactive'

        if not self.check(mode='basic'):
            self._logger.info("Reconnecting ...")

            if not self.create():
                self._logger.error("Creation of socket failed")
                return False
            
            if not self._login():
                self._logger.error("Could not log in")
                return False

            self._logger.info("Reconnection successful")
        else:
            self._logger.info("Data connection is already active")

        self._status = 'active'

        return True

    def _attach_stream_handler(self, handler: '_StreamHandler'):
        """
        Attach a stream handler to the logger.

        Parameters:
        - handler: The stream handler to attach.

        Returns:
        None
        """
        if handler not in self._stream_handlers:
            self._stream_handlers.append(handler)
            self._logger.info("StreamHandler attached")
        else:
            self._logger.warning("StreamHandler already attached")

    def _detach_stream_handler(self, handler: '_StreamHandler'):
        """
        Detaches a stream handler from the logger.

        Args:
            handler (_StreamHandler): The stream handler to detach.

        Returns:
            None

        Raises:
            None
        """
        if handler in self._stream_handlers:
            self._stream_handlers.remove(handler)
            self._logger.info("StreamHandler detached")
        else:
            self._logger.warning("StreamHandler not found")

    def _close_stream_handlers(self):
        """
        Closes the stream handlers.

        This method closes all the stream handlers associated with the logger.
        If there are no stream handlers to close, it returns True.
        If any stream handler fails to close, it logs an error message but continues execution.

        Returns:
            bool: True if all stream handlers are closed successfully, False otherwise.
        """
        self._logger.info("Closing StreamHandlers ...")

        if not self._stream_handlers:
            self._logger.info("No StreamHandlers to close")
            return True

        for handler in list(self._stream_handlers):
            if not handler.delete():
                self._logger.error("Could not close StreamHandler")
                # no false return function must run through
                # detaching is only executed by StreamHandler itself

        return True
    
    def get_status(self):
        """
        Returns the status of the handler.

        Returns:
            str: The status of the handler.
        """
        return self._status

    def get_StreamHandler(self):
        """
        Returns the stream handlers associated with the XTB handler.

        Returns:
            list: A list of stream handlers.
        """
        return self._stream_handlers

    def get_demo(self):
        return self._demo
    
    def set_demo(self, demo):
        raise ValueError("Error: Demo cannot be changed")
    
    def get_logger(self):
        return self._logger
    
    def set_logger(self, logger):
        raise ValueError("Error: Logger cannot be changed")
    
    demo = property(get_demo, set_demo, doc='Get/set the demo mode')
    logger = property(get_logger, set_logger, doc='Get/set the logger')


class _StreamHandler(_GeneralHandler):
    """
    Handles streaming data from XTB API.

    Attributes:
        _logger (logging.Logger): The logger object used for logging.
        _demo (bool): Indicates whether the handler is in demo mode.
        _host (str): The host address for the connection.
        _port (int): The port number for the connection.
        _userid (str): The user ID for the connection.
        _dh (_DataHandler): The data handler object.
        _status (str): The status of the stream handler.
        _stream (dict): The stream dictionary.
        _stream_tasks (dict): The dictionary of stream tasks.
        _ssid (str): The stream session ID.

    Methods:
        delete: Deletes the StreamHandler.
        _start_stream: Starts the stream for the specified command.
        _receive_stream: Receives the stream data.
        _exchange_stream: Exchanges the stream data.
        _stop_task: Stops the stream task.
        _stop_stream: Stops the stream.
        _reconnect: Reconnects the stream handler.
        streamData: Streams data from the server.
        get_status: Returns the status of the stream handler.
        get_datahandler: Returns the data handler object.
        set_datahandler: Sets the data handler object.
        get_demo: Returns the demo mode.
        set_demo: Sets the demo mode.
        get_logger: Returns the logger object.
        set_logger: Sets the logger object.

    """

    def __init__(self, dataHandler: _DataHandler, demo: bool, logger=None):
        """
        Initialize the StreamHandler object.

        Args:
            dataHandler (_DataHandler): The data handler object.
            demo (bool): A boolean indicating whether the handler is for demo or real trading.
            logger (logging.Logger, optional): The logger object to use for logging. Defaults to None.
        
        Raises:
            ValueError: If the logger argument is provided but is not an instance of logging.Logger.
        """
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger = generate_logger(name='StreamHandler', path=Path.cwd() / "logs")

        self._demo = demo

        self._host = HOST
        if self._demo:
            self._port = PORT_DEMO_STREAM
        else:
            self._port = PORT_REAL_STREAM

        self._logger.info("Creating StreamHandler ...")

        super().__init__(host=self._host, port=self._port, stream=True, logger=self._logger)

        self._dh = dataHandler
        self._dh._attach_stream_handler(self)
        self._logger.info("Attached at DataHandler")

        self._status = 'active'
        if not self.open():
            self._status = 'inactive'

        # stream must be initialized right after connection is opened
        self._stream=dict()
        self._stream_tasks = dict()
        self._stop_lock = Lock()
        self.streamData(command='KeepAlive')
        
        # start ping to keep connection open
        self.start_ping(handler=self)
        
        self._logger.info("StreamHandler created")

    def __del__(self):
        """
        Destructor method for the Handler class.
        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations and deletes the object.
        """
        self.delete()
            
    def delete(self):
        """
        Deletes the StreamHandler.

        If the StreamHandler is already deleted, an error message is logged and the method returns True.
        Otherwise, the StreamHandler is deleted by stopping the stream, stopping the ping, closing the connection,
        detaching the StreamHandler from the DataHandler, and updating the status to 'deleted'.

        Returns:
            bool: True if the StreamHandler is successfully deleted, False otherwise.
        """
        if self._status == 'deleted':
            self._logger.warning("StreamHandler already deleted")
            return True

        self._logger.info("Deleting StreamHandler ...")

        self._stop_stream()
        self.stop_ping()
        self.close()
            
        self._dh._detach_stream_handler(self)
        self._logger.info("Detached from DataHandler")

        self._status= 'deleted'
    
        self._logger.info("StreamHandler deleted")
        return True
        
    def streamData(self, command: str, exchange: dict=None, **kwargs):
        """
        Start streaming data from the server.

        Args:
            command (str): The command to start streaming data.
            exchange (dict, optional): The exchange information. Defaults to None.
            **kwargs: Additional keyword arguments for the command.

        Returns:
            bool: True if the stream was started successfully, False otherwise.
        """
        if not self._dh._ssid:
            self._logger.error("Got no StreamSessionId from Server")
            return False

        for index in self._stream_tasks:
            if self._stream_tasks[index]['command'] == command and self._stream_tasks[index]['kwargs'] == kwargs:
                self._logger.warning("Stream for data already open")
                return False

        for tries in range(2):
            response = self._start_stream(command, **kwargs)

            if response:
                break
            elif tries == 0:
                self._reconnect()
            else:
                self._logger.error("Failed to stream data")
                return False

        if not self._stream:
            self._stream['run'] = True
            self._stream['thread'] = CustomThread(target=self._receive_stream, daemon=True)
            self._stream['thread'].start()

            monitor_thread = CustomThread(target=self.thread_monitor, args=('Stream', self._stream, self._reconnect,), daemon=True)
            monitor_thread.start()

        index = len(self._stream_tasks)
        self._stream_tasks[index] = {'command': command, 'arguments': kwargs}

        if command == 'KeepAlive':
            return True

        self._stream_tasks[index]['run'] = True
        self._stream_tasks[index]['queue'] = Queue()
        self._stream_tasks[index]['thread'] = CustomThread(target=self._exchange_stream, args=(index, exchange,), daemon=True)
        self._stream_tasks[index]['thread'].start()

        self._logger.info("Stream started for " + pretty(command))

        exchange['thread'] = CustomThread(target=self._stop_task, args=(index,), daemon=True)

    def _start_stream(self, command: str, **kwargs):
        """
        Starts a stream for the given command.

        Args:
            command (str): The command to start the stream for.
            **kwargs: Additional keyword arguments to be passed as arguments for the stream.

        Returns:
            bool: True if the request for the stream was sent successfully, False otherwise.
        """
        with self._ping_lock:
            self._logger.info("Starting stream for " + pretty(command) + " ...")

            self._ssid = self._dh._ssid

            if not self.send_request(command='get'+command, ssid=self._ssid, arguments=kwargs if bool(kwargs) else None):
                self._logger.error("Request for stream not possible")
                return False 
                
            return True
        
    def _receive_stream(self):
        """
        Receive and process streaming data from the server.

        This method continuously receives data from the server and processes it based on the registered stream tasks.
        It waits for the ping check loop to finish before processing each response.

        Returns:
            bool: True if the stream was successfully received and processed, False otherwise.
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

        while self._stream['run']:
            self._logger.info("Streaming data ...")

            with self._ping_lock: # waits for the ping check loop to finish
                response = self.receive_response(data=False)

            if not response:
                self._logger.error("Failed to read stream")
                return False
            
            if not response['data']:
                self._logger.error("No data received")
                return False
            
            for index in self._stream_tasks:
                command = self._stream_tasks[index]['command']
                arguments = self._stream_tasks[index]['arguments']
                
                if translate[command] != response['command']:
                    continue

                if command == 'KeepAlive':
                    continue

                if 'symbol' in response['data']:
                    if set(arguments['symbol']) != set(response['data']['symbol']):
                        continue
                
                self._logger.info("Data received for " + pretty(command))
                self._stream_tasks[index]['queue'].put(response['data'])

        self._logger.info("All streams stopped")

    def _exchange_stream(self, index: int, exchange: dict):
        """
        Stream data from a queue and update the exchange DataFrame.

        Args:
            index (int): The index of the stream task.
            exchange (dict): The exchange dictionary containing the DataFrame and lock.

        Returns:
            None
        """
        buffer_df = pd.DataFrame()
        
        while self._stream_tasks[index]['run']:
            try:
                # Attempt to get data from the queue with a timeout
                data = self._stream_tasks[index]['queue'].get(timeout=self._interval)
            except Empty:
                continue

            # Add the data to the buffer DataFrame
            if buffer_df.empty:
                buffer_df = pd.DataFrame([data])
            else:
                buffer_df = pd.concat([buffer_df,pd.DataFrame([data])], ignore_index=True)

            self._stream_tasks[index]['queue'].task_done()

            if exchange['lock'].acquire(blocking=False):
                # Append the buffer DataFrame to the exchange DataFrame
                exchange['df']  = pd.concat([exchange['df'], buffer_df], ignore_index=True)
                buffer_df = pd.DataFrame(columns=buffer_df.columns)

                # Limit the DataFrame to the last 1000 rows
                if len(exchange['df']) > 1000:
                    exchange['df'] = exchange['df'].iloc[-1000:]
                    exchange['df'] = exchange['df'].reset_index(drop=True)
                    
                exchange['lock'].release()

        self._logger.info("Stream stopped for " + pretty(self._stream_tasks[index]['command']))

    def _stop_task(self, index: int):
        """
        Stops a stream task at the specified index.

        Args:
            index (int): The index of the stream task to stop.

        Returns:
            bool: True if the stream task was successfully stopped, False otherwise.
        """
        # Necessary if task is stopped by user(thread) and handler(delete) at the same time
        with self._stop_lock:
            if index in self._stream_tasks:
                command = self._stream_tasks[index]['command']
                arguments = self._stream_tasks[index]['arguments']

                self._logger.info("Stopping stream for " + pretty(command) + " ...")

                with self._ping_lock:
                    if not self.send_request(command='stop' + command, arguments={'symbol': arguments['symbol']} if 'symbol' in arguments else None):
                        self._logger.error("Failed to end stream")

                if command == 'KeepAlive':
                    return True
                
                # KeepAlive has no thread
                if not self._stream_tasks[index]['run']:
                    self._logger.warning("Stream task already ended")
                else:
                    self._stream_tasks[index]['run'] = False

                self._stream_tasks[index]['thread'].join()

                del self._stream_tasks[index]

                return True
                    
    def _stop_stream(self):
        """
        Stops the stream and ends all associated tasks.

        Returns:
            bool: True if the stream was successfully stopped, False otherwise.
        """
        self._logger.info("Stopping all streams ...")

        if not self._stream:
            self._logger.error("Stream never started")
            return False

        if not self._stream['run']:
            self._logger.warning("Stream already ended")
        else:
            self._stream['run'] = False

            self._stream['thread'].join()

        for index in list(self._stream_tasks):
            self._stop_task(index=index)

        return True
    
    def _restart_streams(self):
        """
        Restarts all stream tasks.

        Returns:
            bool: True if all stream tasks are successfully restarted, False otherwise.
        """
        self._logger.info("Restarting all streams ...")

        for index in list(self._stream_tasks):
            command=self._stream_tasks[index]['command']
            kwargs=self._stream_tasks[index]['arguments']
            response  = self._start_stream(command, **kwargs)

            if not response:
                self._logger.error("Failed to restart stream")
                return False

        self._logger.info("All streams restarted")

        return True
 
    def _reconnect(self):
        """
        Reconnects the StreamHandler to the DataHandler.

        This method is responsible for handling the reconnection process of the StreamHandler to the DataHandler.
        It acquires a reconnection lock to ensure that only one StreamHandler can attempt reconnection at a time.
        If the lock is acquired, it calls the `_reconnect` method of the DataHandler and releases the lock.
        If the lock is not acquired, it logs a message indicating that another StreamHandler is already attempting reconnection.

        Returns:
            bool: True if the reconnection is successful, False otherwise.
        """
        if self._dh._reconnect_lock.acquire(blocking=False):
            self._dh._reconnect()
            self._dh._reconnect_lock.release()
        else:
            self._logger.info("Reconnection attempt for DataHandler is already in progress by another StreamHandler.")

        with self._dh._reconnect_lock:
            self._status='inactive'

            if not self.check('basic'):
                self._logger.info("Reconnecting ...")
                
                if not self.create():
                    self._logger.error("Creation of socket failed")
                    return False
                
                if not self.open():
                    self._logger.error("Could not open connection")
                    return False

                self._logger.info("Reconnection successful")

                self._restart_streams()
            else:
                self._logger.info("Stream connection is already active")

            self._status='active'
            
        return True
    
    def get_status(self):
        """
        Returns the status of the handler.

        Returns:
            str: The status of the handler.
        """
        return self._status

    def get_datahandler(self):
        """
        Returns the data handler associated with the XTB object.

        Returns:
            DataHandler: The data handler object.
        """
        return self._dh

    def set_datahandler(self, handler: _DataHandler):
        raise ValueError("Error: DataHandler cannot be changed")

    def get_demo(self):
        return self._demo
    
    def set_demo(self, demo):
        raise ValueError("Error: Demo cannot be changed")
    
    def get_logger(self):
        return self._logger
    
    def set_logger(self, logger):
        raise ValueError("Error: Logger cannot be changed")
    
    dataHandler = property(get_datahandler, set_datahandler, doc='Get/set the DataHandler object')
    demo = property(get_demo, set_demo, doc='Get/set the demo mode')
    logger = property(get_logger, set_logger, doc='Get/set the logger')

class HandlerManager():
    """
    The HandlerManager class manages the creation and deletion of data and stream handlers.
    It keeps track of the maximum number of connections and provides available handlers when requested.
    """

    def __init__(self, demo: bool=True, logger=None):
        """
        Initializes a new instance of the HandlerManager class.

        Args:
            demo (bool, optional): Specifies whether the handlers are for demo purposes. Defaults to True.
            logger (logging.Logger, optional): The logger instance to use for logging. Defaults to None.
        """
        self._demo=demo

        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='HandlerManager', path=Path.cwd() / "logs")

        self._handlers = {'data': {}, 'stream': {}}
        self._max_streams=floor(1000/SEND_INTERVAL)
        self._max_connections=MAX_CONNECTIONS
        self._connections=0
        self._deleted=False

    def __del__(self):
        """
        Destructor method that is called when the HandlerManager instance is deleted.
        """
        self.delete()

    def delete(self):
        """
        Deletes the HandlerManager instance and all associated handlers.
        """
        if self._deleted:
            self._logger.warning("HandlerManager already deleted")
            return True
        
        for handler in self._handlers['data']:
            if handler.get_status() == 'active':
                self._delete_handler(handler)

        self._deleted=True

    def _delete_handler(self, handler):
        """
        Deletes a specific handler and deregisters it from the HandlerManager.

        Args:
            handler: The handler to delete.

        Returns:
            bool: True if the handler was successfully deleted, False otherwise.
        """
        if isinstance(handler, _DataHandler):
            for stream in list(handler.get_StreamHandler()):
                self._logger.info("Deregister StreamHandler "+self._handlers['stream'][stream]['name'])
                self._connections -= 1
            
            self._logger.info("Deregister DataHandler "+self._handlers['data'][handler]['name'])
            self._connections -= 1
        elif isinstance(handler, _StreamHandler):
            self._logger.info("Deregister StreamHandler "+self._handlers['stream'][handler]['name'])
            self._connections -= 1

        handler.delete()
        
        return True

    def _get_name(self, handler):
        """
        Gets the name of a specific handler.

        Args:
            handler: The handler to get the name of.

        Returns:
            str: The name of the handler.
        """
        return self._handlers['data'][handler]['name']
        
    def _avlb_DataHandler(self):
        """
        Gets an available data handler.

        Returns:
            _DataHandler or None: An available data handler if found, None otherwise.
        """
        for handler in self._handlers['data']:
            if handler.get_status() == 'active':
                return handler
        return None
    
    def _avlb_StreamHandler(self):
        """
        Gets an available stream handler.

        Returns:
            _StreamHandler or None: An available stream handler if found, None otherwise.
        """
        for handler in self._handlers['stream']:
            if handler.get_status() == 'active':
                if len(handler._stream_tasks) < self._max_streams:
                    return handler
        return None
    
    def _generate_DataHandler(self):
        """
        Generates a new data handler.

        Returns:
            _DataHandler or False: A new data handler if the maximum number of connections is not reached, False otherwise.
        """
        if self._connections >= self._max_connections:
            self._logger.error("Maximum number of connections reached")
            return False

        index = len(self._handlers['data'])
        name = 'DH_' + str(index)
        dh_logger = self._logger.getChild(name)

        dh = _DataHandler(demo=self._demo, logger=dh_logger)

        self._logger.info("Register DataHandler")
        self._handlers['data'][dh] = {'name': name}
        self._connections += 1

        return dh

    def _generate_StreamHandler(self):
        """
        Generates a new stream handler.

        Returns:
            _StreamHandler or False: A new stream handler if the maximum number of connections is not reached, False otherwise.
        """
        if self._connections >= self._max_connections:
            self._logger.error("Maximum number of connections reached")
            return False

        index = len(self._handlers['stream'])
        name = 'SH_' + str(index)
        sh_logger = self._logger.getChild(name)

        dh = self.provide_DataHandler()
        sh = _StreamHandler(dataHandler=dh, demo=self._demo, logger=sh_logger)

        self._logger.info("Register StreamHandler")
        self._handlers['stream'][sh] = {'name': name}
        self._connections += 1

        return sh

    def provide_DataHandler(self):
        """
        Provides an available data handler.

        Returns:
            _DataHandler: An available data handler if found, otherwise a new data handler.
        """
        handler=self._avlb_DataHandler()
        if handler:
            return handler
        else:
            return self._generate_DataHandler()

    def provide_StreamHandler(self):
        """
        Provides an available stream handler.

        Returns:
            _StreamHandler: An available stream handler if found, otherwise a new stream handler.
        """
        handler=self._avlb_StreamHandler()
        if handler:
            return handler
        else:
            return self._generate_StreamHandler()
