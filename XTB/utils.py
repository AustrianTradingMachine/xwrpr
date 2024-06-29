import logging

def set_logger(name: str=None):
    """
    Sets up and returns a logger object with the specified name.

    Args:
        name (str, optional): The name of the logger. Defaults to None.

    Returns:
        logger: The logger object.

    """
    logger = logging.getLogger(name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler('/home/philipp/Trading/ATM_alpha/XTB/Data_logger/handler.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG)
    console_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)

    return logger