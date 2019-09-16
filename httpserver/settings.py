# Web Server Settings
WEB_PROTO = 'http'
WEB_HOST = '0.0.0.0'
WEB_PORT = 10000
WEB_USER = 'admin'
WEB_PASS = 'admin'

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

# dSIPRouter internal settings
VERSION = 0.1
DEBUG = True

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

# upload folder for files
UPLOAD_FOLDER = '/tmp'

# Email Server Settings
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
MAIL_ASCII_ATTACHMENTS = False
MAIL_DEFAULT_SENDER = 'dSIPRouter {}'.format(MAIL_USERNAME)
MAIL_DEFAULT_SUBJECT = "dSIPRouter System Notification"
