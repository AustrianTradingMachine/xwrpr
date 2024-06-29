import json
import re
import os
import logging
from math import floor
from threading import Thread, Lock
from XTB.client import Client
from XTB.utils import generate_logger
from XTB import account


# XTB API socket
XTP_API_HOST='xapi.xtb.com'
XTB_API_PORT_DEMO=5124
XTB_API_PORT_DEMO_STREAM=5125
XTB_API_PORT_REAL=5112
XTB_API_PORT_REAL_STREAM=5113

# XTB API connection parameters
XTB_API_SEND_TIMEOUT=800 #max 1000ms possible
XTB_API_SEND_INTERVAL=250 #min 200ms possible
XTB_API_MAX_CONNECTIONS=50
XTB_API_MAX_CONNECTION_FAILS=5
XTB_API_MAX_SEND_DATA=960 # max size of data sent to server at once. 1024 possible
XTB_API_MAX_RECIEVE_DATA=4096 # max size of data sent to server at once


class _GeneralHandler(Client):
    """
    A class that handles general requests and responses to the XTB API.

    Args:
        host (str): The host address of the XTB API.
        port (int): The port number of the XTB API.
        userid (str): The user ID for authentication.
        logger: The logger object for logging messages.
    """
    def __init__(self, host: str=None, port: int=None, userid: str=None, logger=None):
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='GeneralHandler', path=os.path.join(os.getcwd(), "logs"))

        self._host=host
        self._port=port
        self._userid=userid

        self._encrypted=True
        self._timeout=XTB_API_SEND_TIMEOUT/1000
        self._interval=XTB_API_SEND_INTERVAL/1000
        self._max_fails=XTB_API_MAX_CONNECTION_FAILS
        self._bytes_out=XTB_API_MAX_SEND_DATA
        self._bytes_in=XTB_API_MAX_RECIEVE_DATA
        self._decoder = json.JSONDecoder()

        super().__init__(host=self._host, port=self._port,  encrypted=self._encrypted, timeout=self._timeout, interval=self._interval, max_fails=self._max_fails, bytes_out=self._bytes_out, bytes_in=self._bytes_in, logger=self._logger)
    
    def _send_request(self,command, stream=None, arguments=None, tag=None):
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
        req_dict=dict([('command',command)])

        if stream is not None:
            req_dict['streamSessionId']=stream
        if arguments is not None:
            req_dict['arguments']=arguments
        if tag is not None:
            req_dict['customTag']=tag

        if not self.send(json.dumps(req_dict)):
                self._logger.error("Failed to send message")
                return False
        else: 
                self._logger.info("Sent message"+str(req_dict))
                return True

    def _recieve_response(self):
        """
        Receive a response from the XTB API.

        Returns:
            bool: True if the response was received successfully, False otherwise.

        """
        message=self.receive()

        if not message:
            self._logger.error("Failed to receive message")
            return False
        
        try:
            (message, _) = self._decoder.raw_decode(message)
        except json.JSONDecodeError:
            self._logger.error("Error: JSON decode error")
            return False
        self._logger.info("Received message"+str(message)[:100] + ('...' if len(str(message)) > 100 else ''))

        return message

class _DataHandler(_GeneralHandler):
    """
    DataHandler class for retrieving data from the XTB API.

    Args:
        demo (bool, optional): Flag indicating whether to use the demo mode. Default is True.
        logger (object, optional): Logger object for logging messages.

    """

    def __init__(self, demo: bool=True, logger = None):
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='DataHandler', path=os.path.join(os.getcwd(), "logs"))
        
        self._demo=demo

        self._host=XTP_API_HOST
        if self._demo:
            self._port=XTB_API_PORT_DEMO
            self._userid=account.userid_demo
        else:
            self._port=XTB_API_PORT_REAL
            self._userid=account.userid_real

        super().__init__(host=self._host, port=self._port, userid=self._userid, logger=self._logger)
        
        self._ssid=None
        self._login()
        
        # to handle connected stream handlers
        self._stream_handlers=[]
        self._reconnect_lock = Lock()

        self._logger.info("Data handler created")
        
    def delete(self):
            """
            Destructor method for the handler class.
            Logs out the user if not already logged out.
            
            Returns:
                bool: True if successfully logged out, False otherwise.
            """
            if not self._close_stream_handlers():
                self._logger.error("Error: Could not close stream handlers")
            
            if not self._logout():
                self._logger.error("Error: Could not log out")
                return False
            
            self._logger.info("Handler deleted")
            return True
            
    def _login(self):
        """
        Log in to the XTB API.

        Returns:
            bool: True if the login was successful, False otherwise.

        """
        if not self.open():
            self._logger.error("Log in failed")
            return False
        if not self._send_request(command='login',arguments=dict(userId=self._userid, password=account.password)):
            self._logger.error("Log in failed")
            return False
        response=self._recieve_response()
        if not response:
            self._logger.error("Log in failed")
            return False
        
        status=response['status']

        if status:
            self._logger.info("Log in successfully")
            self._ssid=response['streamSessionId']
        else:
            self._logger.error("Log in failed")
            self._logger.error(response['errorCode'])
            self._logger.error(response['errorDescr'])
                               
        return status

    def _logout(self):
        """
        Log out from the XTB API.

        Returns:
            bool: True if the logout was successful, False otherwise.

        """
        if not self._send_request(command='logout'):
            self._logger.error("Log out failed")
            return False
        response=self._recieve_response()
        if not response:
            self._logger.error("Log out failed")
            return False
        
        status=response['status']

        if status:
            self._logger.info("Logged out successfully")
            if not self.close():
                self._logger.error("Error: Could not close connection")
                return False
            self._ssid=None
        else:
            self._logger.error("Logout failed")
            self._logger.error(response['errorCode'])
            self._logger.error(response['errorDescr'])

        return status

    def getData(self, request, **kwargs):
        """
        Retrieves data from the XTB API.

        Args:
            request (str): The type of data to retrieve.
            **kwargs: Additional arguments for the data request.

        Returns:
            bool or list: The retrieved data if successful, False otherwise.

        Raises:
            RuntimeError: If no active socket is available.
        """
        if not self._ssid:
            raise RuntimeError("Error: No active Socket")
              
        retried=False
        while True:
            if not self._send_request(command='get'+request,arguments=kwargs if bool(kwargs) else None):
                self._logger.error("Failed to send request")
                if not retried:
                    retried=True
                    self._reconnect()
                    continue
                return False
            response=self._recieve_response()
            if not response:
                self._logger.error("Failed to receive data")
                if not retried:
                    retried=True
                    self._reconnect()
                    continue
                return False
            break

        status=response['status']

        pretty_request = re.sub(r'([A-Z])', r'{}\1'.format(' '), request)
        if status:
            self._logger.info(pretty_request +" recieved")
            return response['returnData']
        else:
            self._logger.error("Error: "+pretty_request+" not recieved")
            self._logger.error(response['errorCode'])
            self._logger.error(response['errorDescr'])
            return status
        
    def _reconnect(self):
        """
        Reconnects to the server.

        This method attempts to reconnect to the server by creating a new socket connection,
        opening the connection, and logging in. If any of these steps fail, an error message
        is logged and the reconnection process is aborted.

        Returns:
            bool: True if the reconnection was successful, False otherwise.
        """
        with self._reconnect_lock:
            self._logger.info("Retry connection")
            if not self.create():
                self._logger.error("Error: Creation of socket failed")
                return False
            if not self.open():
                self._logger.error("Error: Could not open connection")
                return False
            if not self.login():
                self._logger.error("Error: Could not log in")
                return False
            
            self._logger.info("Reconnection successful")
            return True
    
    def _register_stream_handler(self, handler):
        """
        Register a stream handler with the DataHandler.

        Args:
            handler (StreamHandler): The stream handler to register.

        Returns:
            None
        """
        self._stream_handlers.append(handler)
        self._logger.info("Stream handler registered")

    def _unregister_stream_handler(self, handler):
        """
        Unregister a stream handler from the DataHandler.

        Args:
            handler (StreamHandler): The stream handler to unregister.

        Returns:
            None
        """
        self._stream_handlers.remove(handler)
        self._logger.info("Stream handler unregistered")

    def _close_stream_handlers(self):
        """
        Close all stream handlers.

        Returns:
            bool: True if all stream handlers were closed successfully, False otherwise.
        """
        for handler in list(self._stream_handlers):
            if not handler.delete():
                self._logger.error("Error: Could not close stream handler")
                return False
        
        self._logger.info("All stream handlers closed")
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

    def __init__(self, dataHandler=None, demo: bool=True, logger = None):
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger=generate_logger(name='StreamHandler', path=os.path.join(os.getcwd(), "logs"))
        
        self._dh=dataHandler
        if not isinstance(self._dh, _DataHandler):
            raise ValueError("Error: DataHandler object required")
        
        self._demo=demo

        self._host=XTP_API_HOST
        if self._demo:
            self._port=XTB_API_PORT_DEMO_STREAM
            self._userid=account.userid_demo
        else:
            self._port=XTB_API_PORT_REAL_STREAM
            self._userid=account.userid_real

        super().__init__(host=self._host, port=self._port, userid=self._userid, logger=self._logger)

        self.open()
        
        self._dh._register_stream_handler(self)
        self._logger.info("Stream handler registered")

        self._running=dict()
        self._thread=dict()

        self._logger.info("Stream handler created")
            
    def delete(self):
        """
        Destructor method for the handler class.

        This method is automatically called when the object is about to be destroyed.
        It performs the necessary cleanup operations before the object is deleted.

        Returns:
            bool: True if the cleanup operations were successful, False otherwise.
        """
        for request in self._running:
            self._endStream(request)

        if not self.close():
            self._logger.error("Error: Could not close connection")
            return False
            
        self._dh._unregister_stream_handler(self)
        self._logger.info("Stream handler unregistered")
    
        self._logger.info("Handler deleted")
        return True
        
    def streamData(self, request, **kwargs):
        """
        Stream data for a given request.

        Args:
            request (str): The request to stream data for.
            **kwargs: Additional keyword arguments.

        Returns:
            bool: True if the request was successfully sent, False otherwise.
        """
        self._ssid = self._dh._ssid

        retried = False
        while True:
            if not self._send_request(command='get'+request, stream=self._ssid, arguments=kwargs if bool(kwargs) else None):
                self._logger.error("Failed to send request")
                if not retried:
                    retried = True
                    self._reconnect()
                    continue
                return False
            break

        self._running[request] = True
        self._thread[request] = Thread(target=self._readStream, args=(request), deamon=True)
        self._thread[request].start()

        self._logger.info("Stream started for "+request)
        return True
            
    def _readStream(self,request):
        """
        Read and process the streamed data for the specified request.

        Args:
            request (str): The request to read data for.

        Returns:
            bool: True if the data was successfully received, False otherwise.
        """
        while self._running[request]:
            retried=False
            while True: 
                response= self._recieve_response()
                if not response:
                    self._logger.error("Failed to receive data")
                    if not retried:
                        retried=True
                        self._reconnect()
                        continue
                    return False
                break
            
            status=response['status']
                
            pretty_request = re.sub(r'([A-Z])', r'{}\1'.format(' '), request)
            if status:
                self._logger.info(pretty_request +" recieved")
                return response['data']
            else:
                self._logger.error("Error: "+pretty_request+" not recieved")
                self._logger.error(response['errorCode'])
                self._logger.error(response['errorDescr'])
                self._running[request]=False
                return status
                
    def endStream(self, request):
        """
        Stops the stream for the specified request.

        Parameters:
        - request (str): The request to stop the stream for.

        Returns:
        None
        """
        self._ssid = self._dh._ssid

        if not self._send_request(command='stop' + request, stream=self._ssid):
            self._logger.error("Failed to end stream")
            return False
        self._running[request] = False

        self._logger.info("Stream ended for "+request)
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
        self._logger.info("Retry connection")
        # Attempt to acquire the lock and reconnect
        if not self._dh.check('basic'):
            self._logger.error("Info: Data connection failed.")
            if self._dh._reconnect_lock.acquire(blocking=False):
                try:
                    self._logger.error("Try reconnection")
                    if not self._dh._reconnect():
                        self._logger.error("Error: Data reconnection failed")
                        return False
                finally:
                    self._dh._reconnect_lock.release()
        else:
            self._logger.info("Reconnection attempt is already in progress by another stream handler.")

        if not self.check('basic'):
            self._logger.error("Info: Stream connection failed. Try reconnection")
            if not self.create():
                self._logger.error("Error: Creation of socket failed")
                return False
            if not self.open():
                self._logger.error("Error: Could not open connection")
                return False
        
        self._logger.info("Reconnection successful")
        return True
    
    def get_datahandler(self):
        return self._dh
    
    def set_datahandler(self, dataHandler):
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
    The HandlerManager class manages the creation and deletion of data and stream handlers for the XTB package.

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
        self._max_streams=floor(1/(XTB_API_SEND_INTERVAL/1000))
        self._max_connections=XTB_API_MAX_CONNECTIONS
        self._connections=0

    def __del__(self):
            """
            Destructor method that is automatically called when the object is about to be destroyed.
            It deletes all the handlers in the `_handlers['data']` list.
            """
            for handler in self._handlers['data']:
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
                self._logger.error("Error: Could not delete handler")
                return False
            else:
                self._handlers['data'][handler]['status'] = 'inactive'
                for stream in list(self._handlers['data'][handler]['streamhandler']):
                    self._delete_handler(stream)
                return True
        elif isinstance(handler, _StreamHandler):
            if not handler.delete():
                self._logger.error("Error: Could not delete handler")
            else:
                self._handlers['stream'][handler]['status'] = 'inactive'
                parent = self._get_parentHandler(handler)
                self._handlers['data'][parent]['streamhandler'].remove(handler)
        else:
            raise ValueError("Error: Invalid handler type")

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
        Returns the parent data handler for a given handler.

        Parameters:
        handler (_StreamHandler): The handler for which to retrieve the parent data handler.

        Returns:
        datahandler: The parent data handler associated with the given handler.

        Raises:
        ValueError: If the handler type is invalid.
        """
        if isinstance(handler, _StreamHandler):
            return self._handlers['stream'][handler]['datahandler']
        else:
            raise ValueError("Error: Invalid handler type")
        
    def _avlb_DataHandler(self):
        """
        Returns the first active data handler from the list of handlers.

        Returns:
            The first active data handler, or None if no active handler is found.
        """
        for handler in self._handlers['data']:
            if self._get_status(handler) == 'active':
                return handler
        return None
    
    def _avlb_StreamHandler(self):
        """
        Returns the available stream handler that is currently active and has fewer streams than the maximum allowed.

        Returns:
            str or None: The name of the available stream handler, or None if no handler is available.
        """
        for handler in self._handlers['stream']:
            if self._get_status(handler) == 'active':
                if len(self._handlers['stream'][handler]['streams']) < self._max_streams:
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

        self._logger.info("Creating DataHandler")

        index = len(self._handlers['data'])
        name = 'DataHandler' + str(index)
        dh_logger = self._logger.getChild(name)

        dh = _DataHandler(demo=self._demo, logger=dh_logger)
        self._handlers['data'][dh] = {'name': name, 'status': 'active'}
        self._handlers['data'][dh]['streamhandler'] = []
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

        self._logger.info("Creating StreamHandler")

        index = len(self._handlers['stream'])
        name = 'StreamHandler' + str(index)
        sh_logger = self._logger.getChild(name)

        dh = self._get_DataHandler()
        sh = _StreamHandler(dataHandler=dh, demo=self._demo, logger=sh_logger)
        self._handlers['stream'][sh] = {'name': name, 'status': 'active', 'datahandler': dh, 'streams': []}
        self._handlers['data'][dh]['streamhandler'][sh] = []
        self._connections += 1

        return sh

    def get_DataHandler(self):
        """
        Returns the data handler for the XTB trading system.

        If a data handler is available, it is returned. Otherwise, a new data handler is generated and returned.

        Returns:
            DataHandler: The data handler for the XTB trading system.
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