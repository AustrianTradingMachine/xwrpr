import json
import re
import os
import logging
import time
import configparser
from math import floor
from threading import Thread, Lock
from queue import Queue
import pandas as pd
from XTB.client import Client
from XTB.utils import generate_logger
from XTB import account


# read api configuration
config = configparser.ConfigParser()
config.read('XTB/api.cfg')

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
    This class represents a general handler for XTB API requests.

    Methods:
        _send_request: Sends a request to the server.
        _receive_response: Receives a response from the server.
        _set_reconnect_method: Sets the callback function for reconnection.
        _request: Sends a request and handles retries.
        _receive: Receives a response and handles retries.
        _start_ping: Starts the ping process.
        _send_ping: Sends ping requests to the server.
        _stop_ping: Stops the ping process.

    """
    def __init__(self, host: str, port: int, userid: str, stream: bool, logger=None):
        """
        Initializes the Handler object.

        Args:
            host (str): The host address.
            port (int): The port number.
            userid (str): The user ID.
            stream (bool): A boolean indicating whether to use streaming mode.
            logger (logging.Logger, optional): The logger object. Defaults to None.
        
        Raises:
            ValueError: If the logger argument is provided but is not an instance of logging.Logger.
        """
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='GeneralHandler', path=os.path.join(os.getcwd(), "logs"))

        self._host=host
        self._port=port
        self._userid=userid
        self._stream=stream

        self._encrypted=True
        self._interval=SEND_INTERVAL/1000
        self._max_fails=MAX_CONNECTION_FAILS
        self._bytes_out=MAX_SEND_DATA
        self._bytes_in=MAX_RECIEVE_DATA
        self._decoder=json.JSONDecoder()

        super().__init__(host=self._host, port=self._port,  encrypted=self._encrypted, timeout=None, interval=self._interval, max_fails=self._max_fails, bytes_out=self._bytes_out, bytes_in=self._bytes_in, stream = self._stream, logger=self._logger)

        self._call_reconnect=None
        
        self._ping=dict()
        self._ping_lock = Lock()
    
    def _send_request(self, command: str, ssid: str = None, arguments: dict = None, tag: str = None):
        """
        Sends a request to the server.

        Args:
            command (str): The command to be sent.
            ssid (str, optional): The stream session ID. Defaults to None.
            arguments (dict, optional): Additional arguments for the request. Defaults to None.
            tag (str, optional): Custom tag for the request. Defaults to None.

        Returns:
            bool: True if the request was successfully sent, False otherwise.
        """
        self._logger.info("Sending request ...")

        req_dict = dict([('command', command)])

        if arguments is not None:
            req_dict.update(arguments)
        if ssid is not None:
            req_dict['streamSessionId'] = ssid
        if tag is not None:
            req_dict['customTag'] = tag

        if not self.send(json.dumps(req_dict)):
            self._logger.error("Failed to send request")
            return False
        else:
            self._logger.info("Sent request: " + str(req_dict))
            return True

    def _receive_response(self):
        """
        Receives a response from the server.

        Returns:
            bool: True if the response was received successfully, False otherwise.
        """
        self._logger.info("Receiving response ...")

        response=self.receive()

        if not response:
            self._logger.error("Failed to receive response")
            return False
        
        try:
            (response, _) = self._decoder.raw_decode(response)
        except json.JSONDecodeError:
            self._logger.error("JSON decode error")
            return False
        self._logger.info("Received response: "+str(response)[:100] + ('...' if len(str(response)) > 100 else ''))

        return response

    def _set_reconnect_method(self, callback):
        """
        Sets the callback function for reconnection.

        Args:
            callback (callable): The callback function for reconnection.

        Returns:
            bool: True if the callback function was set successfully, False otherwise.
        """
        if callable(callback):
            self._call_reconnect = callback
        else:
            self._logger.error("Reconnection method not callable")
            return False
            
    def _request(self, retry: bool, **kwargs):
        """
        Sends a request and handles retries if necessary.

        Args:
            retry (bool): Indicates whether to retry the request if it fails.
            **kwargs: Additional keyword arguments to be passed to the _send_request method.

        Returns:
            bool: True if the request was sent successfully, False otherwise.
        """
        while True:
            if not self._send_request(**kwargs):
                self._logger.error("Failed to send request")

                if retry:
                    self._call_reconnect()
                    retry = False
                    continue

                return False
            break

        return True
    
    def _receive(self, retry: bool, data: bool):
        """
        Receives a response from the server.

        Args:
            retry (bool): Indicates whether to retry the connection if receiving data fails.
            data (bool): Indicates whether to process the received data.

        Returns:
            dict or bool: The received response if `data` is True and the response is valid, False otherwise.
        """
        while True:
            response = self._receive_response()
            if not response:
                self._logger.error("Failed to receive data")

                if retry:
                    self._call_reconnect()
                    retry = False
                    continue

                return False
            break

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
    
    def _start_ping(self, ssid: str=None):
        """
        Starts the ping process.

        Args:
            ssid (str, optional): The stream session ID. Defaults to None.

        Returns:
            bool: True if the ping process was started successfully, False otherwise.
        """
        self._logger.info("Starting ping ...")

        # in case ping is already started
        # but failed
        if 'ping' in self._ping:
            if self._ping['ping']:
                self._stop_ping(inThread=False)


        self._ping['ping'] = True
        self._ping['thread'] = Thread(target=self._send_ping, args=((ssid,) if bool(ssid) else ()), daemon=True)
        self._ping['thread'].start()
        self._logger.info("Ping started")

        return True

    def _send_ping(self, ssid: str=None):
        """
        Sends ping requests to the server.

        Args:
            ssid (str, optional): The stream session ID. Defaults to None.

        Returns:
            bool: True if the ping requests were sent successfully, False otherwise.
        """
        # sends ping all 10 minutes
        ping_interval = 60*9.9
        next_ping=0
        check_interval=self._interval/10
        while self._ping['ping']:
            start_time = time.time()
            if next_ping >= ping_interval:
                # thanks to th with statement the ping could fail to keep is sheduled interval
                # but thats not important because this is just the maximal needed interval and
                # a function that locks the ping_key also initiates a reset to the server
                with self._ping_lock:
                    if not self._request(command='ping', retry=True, ssid=ssid):
                        self._logger.error("Ping failed")
                        self._stop_ping(inThread=True)
                        return False

                    if not ssid:
                        if not self._receive(data = True, retry=True):
                            self._logger.error("Ping failed")
                            self._stop_ping(inThread=True)
                            return False

                    self._logger.info("Ping")
                    
                    next_ping = 0
            time.sleep(check_interval)
            next_ping += time.time() - start_time

    def _stop_ping(self, inThread: bool):
        """
        Stops the ping functionality.

        Args:
            inThread (bool): Indicates whether the method is called from a separate thread.

        Returns:
            bool: True if the ping was successfully stopped, False otherwise.
        """
        self._logger.info("Stopping ping ...")

        if not 'ping' in self._ping:
            self._logger.error("Ping never started")
            return False
            
        if not self._ping['ping']:
            self._logger.error("Ping already stopped")

        self._ping['ping'] = False
        if not inThread:
            self._ping['thread'].join()

        self._logger.info("Ping stopped")

        return True


class _DataHandler(_GeneralHandler):
    """
    The `_DataHandler` class handles data-related operations for the XTB trading platform.

    Methods:
        __init__: Initializes the DataHandler object.
        __del__: Destructor method for the DataHandler object.
        delete: Deletes the DataHandler object.
        _login: Logs in to the XTB trading platform.
        _logout: Logs out the user from the XTB trading platform.
        getData: Retrieves data from the server based on the specified command and arguments.
        _reconnect: Reconnects the data handler to the server.
        _attach_stream_handler: Attaches a stream handler to the logger.
        _detach_stream_handler: Detaches a stream handler from the logger.
        _close_stream_handlers: Closes the stream handlers.
        get_status: Returns the status of the handler.
        get_StreamHandler: Returns the stream handlers associated with the XTB handler.
        get_demo: Returns the demo mode.
        set_demo: Sets the demo mode.
        get_logger: Returns the logger.
        set_logger: Sets the logger.

    """

    def __init__(self, demo: bool, logger=None):
        """
        Initializes a new instance of the DataHandler class.

        Args:
            demo (bool): Specifies whether the instance is for demo or real trading.
            logger (logging.Logger, optional): The logger to be used for logging. If not provided, a new logger will be generated.

        Raises:
            ValueError: If the logger argument is provided but is not an instance of logging.Logger.
        """
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='DataHandler', path=os.path.join(os.getcwd(), "logs"))

        self._demo=demo

        self._host=HOST
        if self._demo:
            self._port=PORT_DEMO
            self._userid=account.userid_demo
        else:
            self._port=PORT_REAL
            self._userid=account.userid_real

        self._logger.info("Creating DataHandler ...")

        super().__init__(host=self._host, port=self._port, userid=self._userid, stream = False, logger=self._logger)
        self._set_reconnect_method(self._reconnect)
        self._status=None
        self._deleted=False

        self._ssid=None
        self._login()

        # starts ping to keep connection open
        self._start_ping()

        self._stream_handlers=[]
        self._reconnect_lock = Lock()

        self._logger.info("DataHandler created")
        
    def __del__(self):
        """
        Destructor method for the Handler class.
        
        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations and deletes the object.
        """
        self.delete()
    
    def delete(self):
        """
        Deletes the DataHandler.

        This method performs the necessary cleanup operations to delete the DataHandler.
        It closes stream handlers, stops the ping, logs out, and marks the DataHandler as deleted.

        Returns:
            bool: True if the DataHandler is successfully deleted, False otherwise.
        """
        if self._deleted:
            self._logger.error("DataHandler already deleted")
            return True

        self._logger.info("Deleting DataHandler ...")

        self._close_stream_handlers()
        self._stop_ping(inThread=False)
        self._logout()
        self._deleted = True
            
        self._logger.info("DataHandler deleted")
        
        return True
            
    def _login(self):
        """
        Logs in to the XTB trading platform.

        Returns:
            bool: True if the login is successful, False otherwise.
        """
        with self._ping_lock: # waits for the ping check loop to finish
            self._logger.info("Logging in ...")

            if not self.open():
                self._logger.error("Log in failed")
                return False
            
            # retry False because login is part of reconnection routine
            if not self._request(retry=False, command='login', arguments={'arguments': {'userId': self._userid, 'password': account.password}}):
                self._logger.error("Log in failed")
                return False
            
            # retry False because login is part of reconnection routine
            response = self._receive(retry=False, data=True)
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
        if not self._ssid:
            self._logger.error("Already logged out")
            # no false return function must run through
            
        with self._ping_lock: # waits for the ping check loop to finish
            self._logger.info("Logging out ...")

            # retry False because login is undesirable
            if not self._request(retry=False, command='logout'):
                self._logger.error("Log out failed")
                # no false return function must run through
            
            # retry False because login is undesirable
            response=self._receive(retry = False, data = True)
            if not response:
                self._logger.error("Log out failed")
                # no false return function must run through

            self._logger.info("Logged out successfully")

            if not self.close():
                self._logger.error("Could not close connection")
                 # no false return function must run through
                
            self._ssid=None
            self._status='inactive'

            return True

    def getData(self, command: str, **kwargs):
        """
        Retrieves data from the server based on the specified command and arguments.

        Args:
            command (str): The command to be executed.
            **kwargs: Additional keyword arguments to be passed as arguments to the command.

        Returns:
            The data received from the server as a response to the command.

        """
        if not self._ssid:
            self._logger.error("Got no StreamSessionId from Server")
            return False

        with self._ping_lock: # waits for the ping check loop to finish
            self._logger.info("Getting data ...")

            if not self._request(retry=True, command='get'+command, arguments={'arguments': kwargs} if bool(kwargs) else None):
                self._logger.error("Request for data not possible")
                return False 
                
            response = self._receive(retry=True, data = True)
            if not response:
                self._logger.error("No data received")
                return False
            
            if not 'returnData' in response:
                self._logger.error("No data in response")
                return False
                
            pretty_command = re.sub(r'([A-Z])', r'{}\1'.format(' '), command)[1:]
            self._logger.info(pretty_command +" recieved")
            return response['returnData']

        
    def _reconnect(self):
        """
        Reconnects the data handler to the server.

        This method is responsible for reconnecting the data handler to the server in case of disconnection.
        It first checks if the basic connection is established, and if not, it retries the connection.
        If the connection is successfully created, it then logs in to the server.
        After a successful reconnection, the data handler's status is set to 'active' and the ping process is started.

        Returns:
            bool: True if the reconnection is successful, False otherwise.
        """
        with self._reconnect_lock:
            self._logger.info("Reconnecting ...")

            self._status = 'inactive'

            if not self.check(mode='basic'):
                self._logger.info("Retry connection")

                if not self.create():
                    self._logger.error("Creation of socket failed")
                    return False
                if not self._login():
                    self._logger.error("Could not log in")
                    return False

                self._status = 'active'
                self._logger.info("Reconnection successful")
                self._start_ping()
            else:
                self._logger.info("Data connection is already active")

        return True

    def _attach_stream_handler(self, handler: '_StreamHandler'):
        """
        Attach a stream handler to the logger.

        Args:
            handler (_StreamHandler): The stream handler to attach.

        Returns:
            None
        """
        if handler not in self._stream_handlers:
            self._stream_handlers.append(handler)
            self._logger.info("StreamHandler attached")
        else:
            self._logger.error("StreamHandler already attached")

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
            self._logger.error("StreamHandler not found")

    def _close_stream_handlers(self):
        """
        Closes the stream handlers.

        This method closes all the stream handlers associated with the logger.
        If there are no stream handlers to close, it returns True.
        If any stream handler fails to close, it logs an error message and continues.

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

    Args:
        dataHandler (_DataHandler): The data handler object.
        demo (bool): Flag indicating whether to use the demo mode.
        logger (logging.Logger, optional): The logger object. Defaults to None.

    Methods:
        __init__(self, dataHandler: _DataHandler, demo: bool, logger=None): Initializes the stream handler.
        __del__(self): Destructor method.
        delete(self): Deletes the stream handler.
        streamData(self, command: str, df: pd.DataFrame=None, lock: Lock=None, **kwargs): Starts streaming data.
        _start_task(self, command: str, df: pd.DataFrame, lock: Lock, **kwargs): Starts a stream task.
        _reveive_stream(self): Receives the stream data.
        _exchange_stream(self, index: int, df: pd.DataFrame, lock: Lock): Exchanges the stream data.
        _stop_task(self, index: int): Stops a stream task.
        _stop_stream(self, inThread: bool): Stops the stream.
        _reconnect(self): Reconnects the stream handler.
        get_status(self): Returns the status of the stream handler.
        get_datahandler(self): Returns the data handler object.
        set_datahandler(self, handler: _DataHandler): Sets the data handler object.
        get_demo(self): Returns the demo mode.
        set_demo(self, demo): Sets the demo mode.
        get_logger(self): Returns the logger object.
        set_logger(self, logger): Sets the logger object.
    """

    def __init__(self, dataHandler: _DataHandler, demo: bool, logger=None):
        """
        Initializes the stream handler.

        Args:
            dataHandler (_DataHandler): The data handler object.
            demo (bool): Flag indicating whether to use the demo mode.
            logger (logging.Logger, optional): The logger object. Defaults to None.
        """
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger = generate_logger(name='StreamHandler', path=os.path.join(os.getcwd(), "logs"))

        if not isinstance(dataHandler, _DataHandler):
            raise ValueError("Error: DataHandler object required")
        else:
            self._dh = dataHandler

        self._demo = demo

        self._host = HOST
        if self._demo:
            self._port = PORT_DEMO_STREAM
            self._userid = account.userid_demo
        else:
            self._port = PORT_REAL_STREAM
            self._userid = account.userid_real

        self._logger.info("Creating StreamHandler ...")

        super().__init__(host=self._host, port=self._port, userid=self._userid, stream=True, logger=self._logger)
        self._set_reconnect_method(self._reconnect)
        self._status = 'active'
        self._deleted = False

        self.open()
        
        # stream must be initialized right after connection is opened
        self._stream=dict()
        self._stream_tasks = dict()
        self.streamData(command='KeepAlive')
        
        # start ping to keep connection open
        self._start_ping(ssid=self._dh._ssid)
        
        self._dh._attach_stream_handler(self)
        self._logger.info("Attached at DataHandler")

        self._logger.info("StreamHandler created")

    def __del__(self):
        """
        Destructor method for the Handler class.

        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations, such as deleting any resources associated with the object.

        """
        self.delete()
            
    def delete(self):
        """
        Deletes the StreamHandler.

        If the StreamHandler has already been deleted, an error message is logged and the method returns True.
        Otherwise, the StreamHandler is deleted by performing the following steps:
        1. Stops the stream and ping processes.
        2. Closes the StreamHandler.
        3. Sets the status of the StreamHandler to 'inactive'.
        4. Detaches the StreamHandler from the DataHandler.
        5. Marks the StreamHandler as deleted.

        Returns:
            bool: True if the StreamHandler is successfully deleted, False otherwise.
        """
        if self._deleted:
            self._logger.error("StreamHandler already deleted")
            return True

        self._logger.info("Deleting StreamHandler ...")

        self._stop_stream(inThread=False)
        self._stop_ping(inThread=False)
        self.close()
        self._status='inactive'
            
        self._dh._detach_stream_handler(self)
        self._logger.info("Detached from DataHandler")

        self._deleted = True
    
        self._logger.info("StreamHandler deleted")
        return True
        
    def streamData(self, command: str, df: pd.DataFrame=None, lock: Lock=None,**kwargs):
        """
        Starts streaming data from the server.

        Args:
            command (str): The command to be sent to the server.
            df (pd.DataFrame, optional): The DataFrame to be used for streaming data. Defaults to None.
            lock (Lock, optional): The lock object to synchronize access to shared resources. Defaults to None.
            **kwargs: Additional keyword arguments to be passed to the server.

        Returns:
            bool: True if the streaming started successfully, False otherwise.
        """
        if not self._dh._ssid:
            self._logger.error("Got no StreamSessionId from Server")
            return False

        with self._ping_lock: # waits for the ping check loop to finish
            self._logger.info("Starting stream ...")

            self._ssid = self._dh._ssid

            if not self._request(retry= True, command='get'+command, ssid=self._ssid, arguments=kwargs if bool(kwargs) else None):
                self._logger.error("Request for stream not possible")
                return False
            
            if not 'stream' in self._stream:
                self._stream['stream'] = True
                self._stream['thread'] = Thread(target=self._reveive_stream, daemon=True)
                self._stream['thread'].start()
                self._logger.info("Stream started")
            
            if command != 'KeepAlive':
                self._start_task(command=command, df=df, lock=lock, **kwargs)

            return True
        
    def _start_task(self, command: str, df: pd.DataFrame, lock: Lock, **kwargs):
        """
        Starts a new streaming task.

        Args:
            command (str): The command for the streaming task.
            df (pd.DataFrame): The DataFrame to be used in the streaming task.
            lock (Lock): The lock object to synchronize access to shared resources.
            **kwargs: Additional keyword arguments for the streaming task.

        Returns:
            bool: True if the streaming task was successfully started.

        """
        index = len(self._stream_tasks)
        self._stream_tasks[index] = {'command': command, 'arguments': kwargs}
        self._stream_tasks[index]['task'] = True
        self._stream_tasks[index]['thread'] = Thread(target=self._exchange_stream, args=(index, df, lock,), daemon=True)
        self._stream_tasks[index]['queue'] = Queue()

        self._logger.info("Stream started for " + command)

        return True

    def _reveive_stream(self):
        """
        Receive and process streaming data.

        This method continuously receives data from the stream and processes it.
        It checks for any errors in the received data and stops the stream if necessary.
        It also filters the received data based on the configured stream tasks.

        Returns:
            bool: True if the stream is successfully processed, False otherwise.
        """
        while self._stream['stream']:
            self._logger.info("Streaming Data ...")

            with self._ping_lock: # waits for the ping check loop to finish
                response=self._receive(retry=True, data=False)

            if not response:
                self._logger.error("Failed to read stream")
                self._stop_stream(inThread=True)
                return False
            
            if not response['data']:
                self._logger.error("No data recieved")
                self._stop_stream(inThread=True)
                return False
            
            print(response['data'])

            for index in self._stream_tasks:
                if self._stream_tasks[index]['command'] != response['command']:
                    continue

                if 'symbol' in response['data']:
                    if set(self._stream_tasks[index]['arguments']['symbol']) != set(response['data']['symbol']):
                        continue

                self._stream_tasks[index]['queue'].put(response['data'])

    def _exchange_stream(self, index: int, df: pd.DataFrame, lock: Lock):
        """
        Stream data from the exchange and append it to the given DataFrame.

        Parameters:
            index (int): The index of the stream task.
            df (pd.DataFrame): The DataFrame to append the data to.
            lock (Lock): The lock object to synchronize access to the DataFrame.

        Returns:
            None
        """
        while self._stream_tasks[index]['task']:
            data = self._stream_tasks[index]['queue'].get()
            lock.acquire()
            df.append(data)
            lock.release()

    def _stop_task(self, index: int):
        """
        Stops the specified stream task at the given index.

        Args:
            index (int): The index of the stream task to stop.

        Returns:
            None
        """
        command = self._stream_tasks[index]['command']
        arguments = self._stream_tasks[index]['arguments']

        with self._ping_lock:
            if not self._request(retry=False, command='stop' + command, arguments={'symbol': arguments['symbol']} if 'symbol' in arguments else None):
                self._logger.error("Failed to end stream")

        if not self._stream_tasks[index]['task']:
            self._logger.error("Stream task already ended")
        else:
            # in case loop still runs
            self._stream_tasks[index]['task'] = False

        # be sure join is not called in Thread target function
        if not inThread:
            self._stream_tasks['thread'].join()

        self._stream_tasks.pop(index)
        self._logger.info("Stream task ended for " + command)
                
    def _stop_stream(self, inThread: bool):
        """
        Stops the stream.

        Args:
            inThread (bool): Indicates whether the method is called from a separate thread.

        Returns:
            bool: True if the stream was successfully stopped, False otherwise.
        """
        self._logger.info("Stopping stream ...")

        if not self._stream['stream']:
            self._logger.error("Stream already ended")
        else:
            # in case loop still runs
            self._stream['stream'] = False

        # be sure join is not called in Thread target function
        if not inThread:
            self._stream['thread'].join()

        for index in list(self._stream_tasks):
            self._stop_task(index)

        return True
            
    def _reconnect(self):
        """
        Reconnects the DataHandler and StreamHandler if the connection is inactive or lost.

        Returns:
            bool: True if reconnection is successful, False otherwise.
        """
        if self._dh._reconnect_lock.acquire(blocking=False):
            if not self._dh.check('basic'): 
                self._logger.info("Retry connection for DataHandler")
                self._status='inactive'
                
                # because of the with statement the db._reconnect function cannot be used directly
                if not self._dh.create():
                    self._logger.error("Creation of socket failed")
                    self._dh._reconnect_lock.release()
                    return False
                if not self._dh._login():
                    self._logger.error("Could not log in")
                    self._dh._reconnect_lock.release()
                    return False

                self._status='active'
                self._logger.info("Reconnection for DataHandler successful")
                self._dh._start_ping()
            else:
                self._logger.info("DataHandler connection is already active")

            self._dh._reconnect_lock.release()
        else:
            self._logger.info("Reconnection attempt for DataHandler is already in progress by another StreamHandler.")

        # to give all StreamHandler, that rely on the same DataHandker, the chance to reconnect
        with self._dh._reconnect_lock:
            if not self.check('basic'):
                self._logger.info("Retry connection")
                self._status='inactive'
                
                if not self.create():
                    self._logger.error("Creation of socket failed")
                    return False
                if not self.open():
                    self._logger.error("Could not open connection")
                    return False

                self._status='active'
                self._logger.info("Reconnection successful")
                self.streamData('KeepAlive')
                self._start_ping(ssid = self._dh._ssid)
            else:
                self._logger.info("Stream connection is already active")

        return True
    
    def get_status(self):
        """
        Returns status of StreamHandler.

        Args:
            None

        Returns:
            Status (str)
        """
        return self._status

    def get_datahandler(self):
            """
            Returns the data handler associated with this object.

            Returns:
                DataHandler: The data handler object.
            """
            return self._dh
    
    def set_datahandler(self, handler: _DataHandler):
        if len(self._stream_tasks) > 0:
            self._logger.error("Cannot change DataHandler. Streams still active")
            return False

        self._dh._detach_stream_handler(self)
        self._logger.info("Detached from DataHandler")
        
        self._dh = handler
        self._logger.info("DataHandler changed")

        self._dh._detach_stream_handler(self)
        self._logger.info("Attached at DataHandler")

    
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
            self._logger=generate_logger(name='HandlerManager', path=os.path.join(os.getcwd(), "logs"))

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
            self._logger.error("HandlerManager already deleted")
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
            self._logger.error("Error: Maximum number of connections reached")
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
            self._logger.error("Error: Maximum number of connections reached")
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
