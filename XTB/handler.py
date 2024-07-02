import json
import re
import os
import logging
import time
import configparser
from math import floor
from threading import Thread, Lock
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

SEND_TIMEOUT=config.getint('CONNECTION','SEND_TIMEOUT')
SEND_INTERVAL=config.getint('CONNECTION','SEND_INTERVAL')
MAX_CONNECTIONS=config.getint('CONNECTION','MAX_CONNECTIONS')
MAX_CONNECTION_FAILS=config.getint('CONNECTION','MAX_CONNECTION_FAILS')
MAX_SEND_DATA=config.getint('CONNECTION','MAX_SEND_DATA')
MAX_RECIEVE_DATA=config.getint('CONNECTION','MAX_RECIEVE_DATA')


class _GeneralHandler(Client):
    """
    A class that handles general requests and responses to the XTB API.

    Args:
        host (str): The host address of the XTB API.
        port (int): The port number of the XTB API.
        userid (str): The user ID for authentication.
        logger: The logger object for logging messages.
    """
    def __init__(self, host: str=None, port: int=None, userid: str=None, reconnect=None, logger=None):
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='GeneralHandler', path=os.path.join(os.getcwd(), "logs"))

        if not callable(reconnect):
            self._reconnection_method=reconnect
        else:
            self._reconnection_method=lambda: None
            
        self._host=host
        self._port=port
        self._userid=userid

        self._encrypted=True
        self._timeout=SEND_TIMEOUT/1000
        self._interval=SEND_INTERVAL/1000
        self._max_fails=MAX_CONNECTION_FAILS
        self._bytes_out=MAX_SEND_DATA
        self._bytes_in=MAX_RECIEVE_DATA
        self._decoder = json.JSONDecoder()

        self._ping=dict()
        self._ping_lock = Lock()

        super().__init__(host=self._host, port=self._port,  encrypted=self._encrypted, timeout=self._timeout, interval=self._interval, max_fails=self._max_fails, bytes_out=self._bytes_out, bytes_in=self._bytes_in, logger=self._logger)
    
    def _send_request(self,command, stream=None, arguments=None, tag=None, pretty=None):
        """
        Send a request to the XTB API.

        Args:
            command (str): The command to send.
            stream (str): The stream session ID.
            arguments (dict): Additional arguments for the command.
            tag (str): A custom tag for the request.

        Returns:
            bool: True if the request was sent successfully, False otherwise.

        """
        self._logger.info("Sending request ...")

        req_dict=dict([('command',command)])

        if stream is not None:
            req_dict['streamSessionId']=stream
        if arguments is not None:
            req_dict.update(arguments)
        if tag is not None:
            req_dict['customTag']=tag
        if pretty is not None:
            req_dict['prettyPrint']=pretty

        if not self.send(json.dumps(req_dict)):
                self._logger.error("Failed to send request")
                return False
        else: 
                self._logger.info("Sent request: "+str(req_dict))
                return True

    def _receive_response(self):
        """
        Receive a response from the XTB API.

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
    
    def _start_ping(self, ssid: str=None):
        """
        Starts the ping process.

        Args:
            ssid (str, optional): The SSID to send the ping to. Defaults to None.

        Returns:
            bool: True if the ping process was started successfully.
        """
        self._logger.info("Starting ping ...")

        self._ping['ping'] = True
        self._ping['thread'] = Thread(target=self._send_ping, args=(ssid if bool(ssid) else None,), daemon=True)
        self._ping['thread'].start()
        self._logger.info("Ping started")

        return True

    def _send_ping(self, ssid: str=None):
        """
        Sends a ping request to the server at regular intervals.

        Args:
            ssid (str, optional): The stream ID. Defaults to None.

        Returns:
            bool: True if the ping request was successful, False otherwise.
        """
        next_ping = 0
        ping_interval = 60*9.5
        check_interval=self._interval/10
        while self._ping['ping']:
            start_time = time.time()
            if next_ping >= ping_interval:
                # thanks to th with statement the ping could fail to keep is sheduled interval
                # but thats not important because this is just the maximal needed interval and
                # a function that locks the ping_key also initiates a reset to the server
                with self._ping_lock:
                    if not self._request(command='ping', stream=ssid if not bool(ssid) else None):
                        self._logger.error("Ping failed")
                        return False

                    if not ssid:
                        response = self._receive()
                        if not response:
                            self._logger.error("Ping failed")
                            return False
                    
                        if not response['status']:
                            self._logger.error("Ping failed")
                            return False

                    self._logger.info("Ping")
                    
                    next_ping = 0
            time.sleep(check_interval)
            next_ping += time.time() - start_time

    def _stop_ping(self):
        """
        Stop the ping request.

        Returns:
            bool: True if the ping was stopped successfully, False otherwise.

        """
        self._logger.info("Stopping ping ...")

        self._ping['ping'] = False
        self._ping['thread'].join()

        self._logger.info("Ping stopped")

        return True

    def _receive_request(self, **kwargs):
        """
        Send a request and receive a response.

        Args:
            **kwargs: Additional arguments for the request.

        Returns:
            bool or dict: The response data if successful, False otherwise.

        """

        self._request(**kwargs)
        response=self._receive()
        
        return response
    
    def _request(self, **kwargs):
        """
        Send a request to the XTB API.

        Args:
            **kwargs: Additional arguments for the request.

        Returns:
            bool: True if the request was sent successfully, False otherwise.

        """
        retried=False
        while True:
            if not self._send_request(**kwargs):
                self._logger.error("Failed to send request")

                if not retried:
                    retried=True
                    self._reconnection_method()
                    continue

                return False
            break
        
        return True
    
    def _receive(self):
        """
        Receive a response from the XTB API.

        Returns:
            bool or dict: The response data if successful, False otherwise.

        """
        retried=False
        while True:
            response=self._receive_response()
            if not response:
                self._logger.error("Failed to receive data")

                if not retried:
                    retried=True
                    self._reconnection_method()
                    continue

                return False
            break
        
        return response
    

class _DataHandler(_GeneralHandler):
    """
    DataHandler class for retrieving data from the XTB API.

    Args:
        demo (bool, optional): Flag indicating whether to use the demo mode. Default is True.
        logger (object, optional): Logger object for logging messages.

    """

    def __init__(self, demo: bool=True, report=None, logger = None):
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='DataHandler', path=os.path.join(os.getcwd(), "logs"))
        
        if callable(report):
            self._report_method=report
        else:
            self._report_method=lambda: None

        self._demo=demo

        self._host=HOST
        if self._demo:
            self._port=PORT_DEMO
            self._userid=account.userid_demo
        else:
            self._port=PORT_REAL
            self._userid=account.userid_real

        self._logger.info("Creating DataHandler ...")

        super().__init__(host=self._host, port=self._port, userid=self._userid, reconnect=self._reconnect, logger=self._logger)
    
        self._ssid=None
        self._login()
        self._start_ping()
        
        self._stream_handlers=[]
        self._reconnect_lock = Lock()

        self._logger.info("DataHandler created")
        
    def __del__(self):
        self.delete()
    
    def delete(self):
        """
        Destructor method for the DataHandler class.
        Logs out the user if not already logged out.
        
        Returns:
            bool: True if successfully logged out, False otherwise.
        """
        self._logger.info("Deleting DataHandler ...")

        if not self._close_stream_handlers():
            self._logger.error("Could not close all StreamHandlers")
        
        if self._ping['ping']:
            self._stop_ping()
        else:
            self._logger.error("Ping already stopped")

        if self._ssid:
            if not self._logout():
                self._logger.error("Could not log out")
        else:
            self._logger.error("Already logged out")

        self._logger.info("DataHandler deleted")
        return True
            
    def _login(self):
        """
        Log in to the XTB API.

        Returns:
            bool: True if the login was successful, False otherwise.

        """
        with self._ping_lock: # waits for the ping check loop to finish
            self._logger.info("Logging in ...")

            if not self.open():
                self._logger.error("Log in failed")
                return False
            
            # request_response nicht mmöglich weil login teil der reconnect routine ist
            if not self._send_request(command='login',arguments={'arguments': {'userId': self._userid, 'password': account.password}}):
                self._logger.error("Log in failed")
                return False
            
            response=self._receive_response()
            if not response:
                self._logger.error("Log in failed")
                return False

            if response['status']:
                self._logger.info("Log in successfully")
                self._ssid=response['streamSessionId']
            else:
                self._logger.error("Log in failed")
                self._logger.error(response['errorCode'])
                self._logger.error(response['errorDescr'])

            #self._report_method(self,'active')
                                
            return response['status']

    def _logout(self):
        """
        Log out from the XTB API.

        Returns:
            bool: True if the logout was successful, False otherwise.

        """
        with self._ping_lock: # waits for the ping check loop to finish
            self._logger.info("Logging out ...")

            #self._report_method(self,'inactive')

            if not self._send_request(command='logout'):
                self._logger.error("Log out failed")
                return False
            
            response=self._receive_response()
            if not response:
                self._logger.error("Log out failed")
                return False

            if response['status']:
                self._logger.info("Logged out successfully")

                if not self.close():
                    self._logger.error("Could not close connection")
                    return False
                
                self._ssid=None
            else:
                self._logger.error("Logout failed")
                self._logger.error(response['errorCode'])
                self._logger.error(response['errorDescr'])

            return response['status']

    def getData(self, command, **kwargs):
        """
        Retrieves data from the XTB API.

        Args:
            command (str): The type of data to retrieve.
            **kwargs: Additional arguments for the data request.

        Returns:
            bool or list: The retrieved data if successful, False otherwise.

        Raises:
            RuntimeError: If no active socket is available.
        """
        if not self._ssid:
            self._logger.error("Got no StreamSessionId from Server")
            return False

        with self._ping_lock: # waits for the ping check loop to finish
            self._logger.info("Getting data ...")

            response = self._receive_request(command='get'+command,arguments={'arguments': kwargs} if bool(kwargs) else None)
            if not response:
                return False
            
            pretty_request = re.sub(r'([A-Z])', r'{}\1'.format(' '), command)
            if response['status']:
                if not response['returnData']:
                    self._logger.error("Status true but data not recieved")
                    return False
                
                self._logger.info(pretty_request +" recieved")
                return response['returnData']
            else:
                self._logger.error(pretty_request+" not recieved")
                self._logger.error(response['errorCode'])
                self._logger.error(response['errorDescr'])
                return False
        
    def _reconnect(self):
        """
        Reconnects to the server.

        This method attempts to reconnect to the server by creating a new socket connection,
        opening the connection, and logging in. If any of these steps fail, an error message
        is logged and the reconnection process is aborted.

        Returns:
            bool: True if the reconnection was successful, False otherwise.
        """
        # The reconnection by a StreamHandler is as good as the reconnection by the Datahandler itself
        # But the Datahandler has to wait for he reconnection because his functions depend directly on it
        with self._reconnect_lock:
            self._logger.info("Reconnecting ...")

            if not self.check('basic'):
                self._logger.info("Retry connection")
                
                if not self.create():
                    self._logger.error("Creation of socket failed")
                    #self._report_method(self,'failed')
                    return False
                if not self._login():
                    self._logger.error("Could not log in")
                    #self._report_method(self,'failed')
                    return False
            
                self._logger.info("Reconnection successful")
            else:
                self._logger.info("Data connection is already active")

        return True
    
    def _register_stream_handler(self, handler):
        """
        Register a ŚtreamHandler with the DataHandler.

        Args:
            handler (StreamHandler): The StreamHandler to register.

        Returns:
            None
        """
        if handler not in self._stream_handlers:
            self._stream_handlers.append(handler)
            self._logger.info("StreamHandler registered")
        else:
            self._logger.error("StreamHandler already registered")

    def _unregister_stream_handler(self, handler):
        """
        Unregister a StreamHandler from the DataHandler.

        Args:
            handler (StreamHandler): The StreamHandler to unregister.

        Returns:
            None
        """
        if handler in self._stream_handlers:
            self._stream_handlers.remove(handler)
            self._logger.info("StreamHandler unregistered")
        else:
            self._logger.error("StreamHandler not found")

    def _close_stream_handlers(self):
        """
        Close all StreamHandlers.

        Returns:
            bool: True if all StreamHandlers were closed successfully, False otherwise.
        """
        self._logger.info("Closing StreamHandlers ...")

        if not self._stream_handlers:
            self._logger.info("No StreamHandlers to close")
            return True

        for handler in list(self._stream_handlers):
            if not handler.delete():
                self._logger.error("Could not close StreamHandler")
                return False
        
        self._logger.info("All StreamHandlers closed")
        return True

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
    Class for handling streaming data from XTB API.

    Args:
        dataHandler (DataHandler): The DataHandler object.
        demo (bool, optional): Flag indicating whether to use demo mode. Defaults to True.
        logger (Logger, optional): The logger object. Defaults to None.
    """

    def __init__(self, dataHandler=None, demo: bool=True, report=None, logger = None):
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='StreamHandler', path=os.path.join(os.getcwd(), "logs"))

        if callable(report):
            self._report_method=report
        else:
            self._report_method=lambda: None

        if not isinstance(dataHandler, _DataHandler):
            raise ValueError("Error: DataHandler object required")
        else:
            self._dh=dataHandler

        self._demo=demo

        self._host=HOST
        if self._demo:
            self._port=PORT_DEMO_STREAM
            self._userid=account.userid_demo
        else:
            self._port=PORT_REAL_STREAM
            self._userid=account.userid_real

        self._logger.info("Creating StreamHandler ...")

        super().__init__(host=self._host, port=self._port, userid=self._userid, reconnect=self._reconnect, logger=self._logger)

        self.open()
        self._start_ping()
        
        self._dh._register_stream_handler(self)
        self._logger.info("Registered at DataHandler")

        self._streams=dict()

        self._logger.info("StreamHandler created")

    def __del__(self):
        self.delete()
            
    def delete(self):
        """
        Destructor method for the StreamHandler class.

        This method is automatically called when the object is about to be destroyed.
        It performs the necessary cleanup operations before the object is deleted.

        Returns:
            bool: True if the cleanup operations were successful, False otherwise.
        """
        self._logger.info("Deleting StreamHandler ...")

        for index in list(self._streams):
            self.endStream(index)

        if self._ping['ping']:
            self._stop_ping()
        else:
            self._logger.error("Ping already stopped")

        if not self.close():
            self._logger.error("Could not close connection")
            
        self._dh._unregister_stream_handler(self)
        self._logger.info("Unregistered at DataHandler")
    
        self._logger.info("StreamHandler deleted")
        return True
        
    def streamData(self, command, **kwargs):
        """
        Stream data for a given request.

        Args:
            command (str): The request to be sent.
            **kwargs: Additional arguments for the request.

        Returns:
            int: The index of the running stream.

        """
        if not self._dh._ssid:
            self._logger.error("Got no StreamSessionId from Server")
            return False

        # gracefully stops ping if active
        # ping is not needed as long as stream is active
        if self._ping['ping']:
            self._stop_ping()

        self._logger.info("Starting stream ...")

        self._ssid = self._dh._ssid

        self._request(command='get'+command, stream=self._ssid, arguments=kwargs if bool(kwargs) else None)

        index = len(self._streams)
        self._streams[index] = dict()
        self._streams[index]['command'] = command
        self._streams[index]['arguments'] = kwargs
        self._streams[index]['stream'] = True
        self._streams[index]['thread'] = Thread(target=self._readStream, args=(index,), daemon=True)
        self._streams[index]['thread'].start()
        

        self._logger.info("Stream started for "+command)
        
        return index
            
    def _readStream(self,index: int=False):
        """
        Read and process the streamed data for the specified request.

        Args:
            index (int): The index to read data for.

        Returns:
            bool: True if the data was successfully received, False otherwise.
        """
        while self._streams[index]['stream']:
            self._logger.info("Streaming Data ...")

            response=self._receive_response()
            if not response:
                self._logger.error("Failed to read stream")
                self.endStream(index,True)
                return False

            command=self._streams[index]['command']
            pretty_command = re.sub(r'([A-Z])', r'{}\1'.format(' '), command)
  
            if not response['data']:
                self._logger.error("Status true but data not recieved")
                self.endStream(index,True)
                return False
            
            print(response['data'])
            self._logger.info(pretty_command +" recieved")
            return response['data']

                
    def endStream(self, index: int, inThread: bool):
        """
        Stops the stream for the specified request.

        Parameters:
        - index (int): The index to stop the stream for.

        Returns:
        None
        """
        self._logger.info("Stopping stream ...")

        if not self._streams[index]['stream']:
            self._logger.error("Stream already ended")
        else:
            self._streams[index]['stream'] = False

        if not inThread:
            self._streams[index]['thread'].join()
            
        command=self._streams[index]['command']
        arguments=self._streams[index]['arguments']
        if not self._send_request(command='stop' + command, arguments=arguments['symbol'] if 'symbol' in arguments else None):
            self._logger.error("Failed to end stream")
        
        self._streams.pop(index)

        if len(self._streams) == 0:
            self._start_ping()

        self._logger.info("Stream ended for "+command)
        return True
            
    def _reconnect(self):
        """
        Reconnects the data and stream connections.

        This method attempts to acquire a lock and then reconnects the data and stream connections.
        If the data connection fails, it tries to reconnect. If the stream connection fails, it creates
        a new socket and opens the connection.

        Returns:
            bool: True if the reconnection is successful, False otherwise.
        """
        if self._dh._reconnect_lock.acquire(blocking=False):
            if not self._dh.check('basic'): 
                self._logger.info("Retry connection for DataHandler")
                # because of the with statement the db._reconnect function cannot be used directly
                if not self._dh.create():
                    self._logger.error("Creation of socket failed")
                    #self._dh._report_method(self,'failed')
                    self._dh._reconnect_lock.release()
                    return False
                if not self._dh._login():
                    self._logger.error("Could not log in")
                    #self._dh._report_method(self,'failed')
                    self._dh._reconnect_lock.release()
                    return False
            
                self._logger.info("Reconnection for DataHandler successful")
            else:
                self._logger.info("DataHandler connection is already active")

            self._dh._reconnect_lock.release()
        else:
            self._logger.info("Reconnection attempt for DataHandler is already in progress by another StreamHandler.")

        # to give all StreamHandler, that rely on the same DataHandker, the chance to reconnect
        with self._dh._reconnect_lock:
            if not self.check('basic'):
                self._logger.info("Retry connection")
                
                if not self.create():
                    self._logger.error("Creation of socket failed")
                    #self._report_method(self,'failed')
                    return False
                if not self.open():
                    self._logger.error("Could not open connection")
                    #self._report_method(self,'failed')
                    return False
                
                self._logger.info("Reconnection successful")
            else:
                self._logger.info("Stream connection is already active")

        return True
    
    def get_datahandler(self):
        return self._dh
    
    def set_datahandler(self, dataHandler):
        if not isinstance(dataHandler, _DataHandler):
            raise ValueError("Error: DataHandler object required")

        if len(self._streams) > 0:
            self._logger.error("Cannot change DataHandler. Streams still active")
            return False

        self._dh._unregister_stream_handler(self)
        self._logger.info("Unregistered at DataHandler")
        
        self._dh = dataHandler
        self._logger.info("DataHandler changed")

        self._dh._register_stream_handler(self)
        self._logger.info("Registered at DataHandler")

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
    The HandlerManager class manages the creation and deletion of Data- and StreamHandlers for the XTB package.

    Args:
        demo (bool, optional): Specifies whether to use the demo mode. Defaults to True.
        logger (logging.Logger, optional): The logger instance to use. Defaults to None.

    """
    def __init__(self, demo: bool=True, logger=None):
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

    def __del__(self):
        self.delete()

    def delete(self):
            """
            Destructor method that is automatically called when the object is about to be destroyed.
            It deletes all the handlers in the `_handlers['data']` list.
            """
            for handler in self._handlers['data']:
                if self._handlers['data'][handler]['status'] == 'active':
                    self._delete_handler(handler)

    def _delete_handler(self, handler):
        """
        Deletes the specified handler.

        Args:
            handler: The handler object to be deleted.

        Returns:
            bool: True if the handler is successfully deleted, False otherwise.

        Raises:
            ValueError: If the handler type is invalid.
        """
        if isinstance(handler, _DataHandler):
            if not handler.delete():
                self._logger.error("Could not delete DataHandler")
                return False
            else:
                self._handlers['data'][handler]['status'] = 'inactive'
                for stream in list(self._handlers['data'][handler]['streamhandler']):
                    self._handlers['stream'][stream]['status'] = 'inactive'
                    self._handlers['data'][handler]['streamhandler'].pop(stream)
        elif isinstance(handler, _StreamHandler):
            if not handler.delete():
                self._logger.error("Could not delete StreamHandler")
                return False
            else:
                self._handlers['stream'][handler]['status'] = 'inactive'
                parent = self._get_parentHandler(handler)
                self._handlers['data'][parent]['streamhandler'].remove(handler)
        else:
            raise ValueError("Error: Invalid handler type")
        
        return True

    def _get_name(self, handler):
        """
        Get the name of the handler.

        Parameters:
        - handler: The handler object whose name needs to be retrieved.

        Returns:
        - The name of the handler.

        Raises:
        - ValueError: If the handler type is invalid.
        """
        if isinstance(handler, _DataHandler):
            return self._handlers['data'][handler]['name']
        elif isinstance(handler, _StreamHandler):
            return self._handlers['stream'][handler]['name']
        else:
            raise ValueError("Error: Invalid handler type")
        
    def _report_status(self, handler, status):
        if isinstance(handler, _DataHandler):
            self._handlers['data'][handler]['status']=status
        elif isinstance(handler, _StreamHandler):
            self._handlers['stream'][handler]['status']=status
        else:
            raise ValueError("Error: Invalid handler type")
        
    def _get_status(self, handler):
        """
        Get the status of a handler.

        Parameters:
        - handler: The handler object whose status is to be retrieved.

        Returns:
        - The status of the handler.

        Raises:
        - ValueError: If an invalid handler type is provided.
        """
        if isinstance(handler, _DataHandler):
            return self._handlers['data'][handler]['status']
        elif isinstance(handler, _StreamHandler):
            return self._handlers['stream'][handler]['status']
        else:
            raise ValueError("Error: Invalid handler type")
        
    def _get_parentHandler(self, handler):
        """
        Returns the parent DataHandler for a given handler.

        Parameters:
        handler (_StreamHandler): The handler for which to retrieve the parent DataHandler.

        Returns:
        datahandler: The parent DataHandler associated with the given handler.

        Raises:
        ValueError: If the handler type is invalid.
        """
        if isinstance(handler, _StreamHandler):
            return self._handlers['stream'][handler]['datahandler']
        else:
            raise ValueError("Error: Invalid handler type")
        
    def _avlb_DataHandler(self):
        """
        Returns the first active DataHandler from the list of handlers.

        Returns:
            The first active DataHandler, or None if no active handler is found.
        """
        for handler in self._handlers['data']:
            if self._get_status(handler) == 'active':
                return handler
        return None
    
    def _avlb_StreamHandler(self):
        """
        Returns the available StreamHandler that is currently active and has fewer streams than the maximum allowed.

        Returns:
            str or None: The name of the available StreamHandler, or None if no handler is available.
        """
        for handler in self._handlers['stream']:
            if self._get_status(handler) == 'active':
                if handler._streams < self._max_streams:
                    return handler
        return None
    
    def _generate_DataHandler(self):
        """
        Generates a new DataHandler instance and adds it to the list of handlers.

        Returns:
            DataHandler: The newly created DataHandler instance.

        Raises:
            None
        """
        if self._connections >= self._max_connections:
            self._logger.error("Error: Maximum number of connections reached")
            return False

        index = len(self._handlers['data'])
        name = 'DH_' + str(index)
        dh_logger = self._logger.getChild(name)

        dh = _DataHandler(demo=self._demo, report = self._report_status, logger=dh_logger)

        self._handlers['data'][dh] = {'name': name, 'status': 'active', 'streamhandler': {}}
        self._connections += 1

        return dh

    def _generate_StreamHandler(self):
        """
        Generates a new StreamHandler instance.

        Returns:
            StreamHandler: The newly created StreamHandler instance.

        Raises:
            None
        """
        if self._connections >= self._max_connections:
            self._logger.error("Error: Maximum number of connections reached")
            return False

        index = len(self._handlers['stream'])
        name = 'SH_' + str(index)
        sh_logger = self._logger.getChild(name)

        dh = self.get_DataHandler()
        sh = _StreamHandler(dataHandler=dh, demo=self._demo, report = self._report_status, logger=sh_logger)

        self._handlers['stream'][sh] = {'name': name, 'status': 'active','datahandler': dh}
        self._handlers['data'][dh]['streamhandler'][sh] = None
        self._connections += 1

        return sh

    def get_DataHandler(self):
        """
        Returns the DataHandler for the XTB trading system.

        If a DataHandler is available, it is returned. Otherwise, a new DataHandler is generated and returned.

        Returns:
            DataHandler: The DataHandler for the XTB trading system.
        """
        handler=self._avlb_DataHandler()
        if handler:
            return handler
        else:
            return self._generate_DataHandler()

    def get_StreamHandler(self):
        """
        Retrieves the StreamHandler object.

        If a StreamHandler object is available, it is returned.
        Otherwise, a new StreamHandler object is generated and returned.

        Returns:
            StreamHandler: The StreamHandler object.
        """
        handler=self._avlb_StreamHandler()
        if handler:
            return handler
        else:
            return self._generate_StreamHandler()
