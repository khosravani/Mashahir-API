import inspect
import os
import sys
import logging
import configparser


# from sqlalchemy import create_engine, MetaData, Table

CONFIG_FILE = "config.ini"
wdir = os.getcwd()
Config = configparser.ConfigParser()

Config.read("config.ini")

# set up logging to file - see previous section for more details
log_level = eval('logging.' + Config.get('Logger', 'Level'))
logging.basicConfig(level=log_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%y-%m-%d %H:%M',
                    filename='log_file.log',
                    filemode='a')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(log_level)
# set a format which is simpler for console use
formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s \n %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

class Property(object):
    pass


general = Property()
general.enable_tornado = Config.getboolean('General', 'enable_tornado')
general.server_ip = Config.get('General','server_ip')
general.port = Config.get('General','port')
general.voiceprint_port = Config.get('General','voiceprint_port')

general.request_expiration = Config.get('General','request_expiration')
general.token_expiration = Config.get('General','token_expiration')
general.word_count = Config.get('General','word_count')
general.log_age = Config.get('General','log_age')
general.auth_threshold = Config.get('General','auth_threshold')
general.auth_add_model = Config.get('General','auth_add_model')
general.auth_add_count = Config.get('General', 'auth_add_count')
general.wer = Config.get('General','wer')
general.identify_theshold = Config.get('General','identify_theshold')
general.identify_maxcount = Config.get('General','identify_maxcount')
general.identify_a = Config.get('General','identify_a')
general.identify_b = Config.get('General','identify_b')

database = Property()
database.type = Config.get('Database', 'type').strip()
database.dbname = Config.get('Database', 'dbname').strip()
database.address = Config.get('Database', 'address').strip()
database.password = Config.get('Database', 'pass').strip()
database.reset = Config.get('Database', 'reset').strip()
