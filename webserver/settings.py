# Web Server Settings
WEB_PROTO = 'http'
WEB_HOST = '0.0.0.0'
WEB_PORT = 10000
WEB_USER = 'admin'
WEB_PASS = 'admin'
WEB_TIMEOUT = 10
WEB_SOCK = '/run/shomesec/pyserve.sock'

# Logging Settings
# syslog level and facility values based on:
# <http://www.nightmare.com/squirl/python-ext/misc/syslog.py>
WEB_LOG_LEVEL = 3
WEB_LOG_FACILITY = 18

# ssl key / cert paths
# email for re-certification (must match certs)
WEB_SSL_KEY = ''
WEB_SSL_CERT = ''
WEB_SSL_EMAIL = ''

# Database Settings
DB_HOST = 'localhost'
# Database Engine Driver to connect with (leave empty for default)
# supported drivers:    mysqldb | pymysql
# see sqlalchemy docs for more info: <https://docs.sqlalchemy.org/en/latest/core/engines.html>
DB_DRIVER = ''
DB_TYPE = 'mysql'
DB_PORT = '3306'
DB_NAME = 'shomesec'
DB_USER = 'shomesec'
DB_PASS = 'shomesec'

# SQLAlchemy Settings
# Will disable modification tracking
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_SQL_DEBUG = False

# Node Sync Server settings
NODESYNC_HOST = '0.0.0.0'
NODESYNC_PORT = 10001
NODESYNC_BUFFSIZE = 4096

# Shomesec App Settings
SHOMESEC_VERSION = 0.1
SHOMESEC_DEBUG = False
SHOMESEC_RUN_DIR = '/run/shomesec'
SHOMESEC_PID_FILE = '/run/shomesec/pyserve.pid'
VIDEO_RESOLUTION = (1640,1232)  # resolution in pixels
VIDEO_FPS = 40  # frames per second
VIDEO_BUFFSIZE = 16384
