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

import json
import logging
import time
from pathlib import Path
import websocket
from xwrpr.utils import generate_logger


class Client():
    def __init__(
        self,

        url: str,
        interval: float = 0.5,

        logger=None
    ) -> None:
        """
        Initializes a new instance of the Client class.

        Args:
            url (str): The URL of the WebSocket server.
            interval (float, optional): The interval between requests in seconds. Defaults to 0.5.
            logger (logging.Logger, optional): The logger instance to use for logging. Defaults to None.
        """

        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            self._logger = logger
        else:
            self._logger = generate_logger(name='Client', path=Path.cwd() / "logs")

        self._logger.info("Initializing the client ...")
        
        self._url = url
        self._interval = interval

        # Initialize the JSON decoder
        self._decoder = json.JSONDecoder()
        self._socket = None

        self._logger.info("Client initialized")

    def connect(self) -> None:
        """
        Connects to the WebSocket server.

        Raises:
            Exception: If there is an error connecting to the server.
        """

        self._logger.info("Connecting to WebSocket ...")
        try:
            self._socket = websocket.create_connection(self._url, timeout=self._timeout)
            self._logger.info("WebSocket connection established")
        except Exception as e:
            self._logger.error(f"Failed to connect: {e}")
            raise Exception("Failed to connect to WebSocket server") from e

    def send(self, msg: str) -> None:
        """
        Sends a message over the WebSocket connection.

        Args:
            msg (str): The message to send.

        Raises:
            Exception: If there is an error sending the message.
        """

        self._logger.info("Sending message ...")

        try:
            msg = json.dumps(msg)
            self._socket.send(msg)
            # For request limitation
            time.sleep(self._interval)
            self._logger.info("Message sent")
        except json.JSONDecodeError as e:
            self._logger.error(f"Error dumping message: {e}")
            raise Exception("Error dumping message") from e
        except Exception as e:
            self._logger.error(f"Error sending message: {e}")
            raise Exception("Error sending message") from e

    def receive(self) -> str:
        """
        Receives a message from the WebSocket connection.

        Returns:
            str: The received message.

        Raises:
            Exception: If there is an error receiving the message.
        """
        
        self._logger.info("Receiving message ...")

        try:
            msg = self._socket.recv()
            self._logger.info("Message received")
            return msg
        except Exception as e:
            self._logger.error(f"Error receiving message: {e}")
            raise Exception("Error receiving message") from e

    def close(self) -> None:
        """
        Closes the WebSocket connection.

        """

        if self._socket:
            self._logger.info("Closing WebSocket connection ...")
            self._socket.close()
            self._logger.info("WebSocket connection closed")