import os

userid_real = os.getenv('XTB_USERNAME')
userid_demo = os.getenv('XTB_USERNAME_DEMO')
password = os.getenv('XTB_PASSWORD')

env_vars = [userid_real, userid_demo, password]

if None in env_vars or "" in env_vars:
    raise ValueError("Please set the environment variables XTB_USERNAME, XTB_USERNAME_DEMO and XTB_PASSWORD")