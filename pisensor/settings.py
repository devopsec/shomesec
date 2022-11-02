# Sensor Settings
ALARM_NOTIFY_EMAILS = []
ALARM_NOTIFY_NUMBERS = []

# Email Server Settings
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'dev.testing.1234567@gmail.com'
MAIL_PASSWORD = '9sRGCkVgYFxtfdn'
MAIL_ASCII_ATTACHMENTS = False
MAIL_DEFAULT_SENDER = 'Simple Home Security <{}>'.format(MAIL_USERNAME)
MAIL_DEFAULT_SUBJECT = "Simple Home Security System Notification"
SMS_NUMBER_LOOKUP_URL = 'https://api.telnyx.com/v1/phone_number/'

# settings for node sync server
NODESYNC_HOST = '192.168.1.131'
NODESYNC_PORT = 10001
NODESYNC_DELAY = 60

# settings for video server
VIDEO_PORT = 10000
