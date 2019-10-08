# Sensor Settings
ALARM_NOTIFY_EMAILS = []
ALARM_NOTIFY_NUMBERS = []

# Email Server Settings
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
MAIL_ASCII_ATTACHMENTS = False
MAIL_DEFAULT_SENDER = '{}@{}'.format(MAIL_USERNAME, MAIL_SERVER)
MAIL_DEFAULT_SUBJECT = "Simple Home Security System Notification"
SMS_DEFAULT_CARRIER = 'verizon'

# settings for node sync server
NODESYNC_HOST = '192.168.1.69'
NODESYNC_PORT = 10001
NODESYNC_DELAY = 60

# settings for video server
VIDEO_PORT = 10000