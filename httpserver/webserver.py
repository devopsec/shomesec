import os, sys, socket, subprocess, signal, logging, io
from copy import copy
from importlib import reload
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for, Response, send_from_directory
from flask_script import Manager, Server
import settings
from util.shared import *
from util.printing import IO, debugException, debugEndpoint
from util.decorator import async


# global variables
app = Flask(__name__, static_folder="./static", static_url_path="/static")
# db = loadSession()
video_resolution = (1280,720)  # resolution in pixels
video_fps = 30  # frames per second

buffsize = 4096
framesize = video_resolution[0] * video_resolution[1] * 3
# TODO: create protocol to automatically add pi cams (send id and host, etc..)
host = "192.168.1.2"
port = 10000

# socks = []
#
# @app.before_request
# def before_request():
#     print('disconnecting socks: {}'.format(str(socks)))
#     for sock in socks:
#         try:
#             sock.shutdown(socket.SHUT_RDWR)
#         except:
#             pass
#         sock.close()

# @async
def generateVideoFrames(sock):
    stream = sock.makefile('rb', framesize)
    # buff = io.BytesIO()

    while True:
        data = stream.read(framesize)
        # IO.printdbg('len(data): {}'.format(len(data)))

        if not data:
            stream.close()
            break

        # if data.startswith(b'\xff\xd8'):
        #     # Start of new frame
        #     size = buff.tell()
        #     if size > 0:
        #         buff.seek(0)
        #         yield (b'--frame\r\n'
        #                b'Content-Type: image/jpeg\r\n\r\n' + buff.read(size) + b'\r\n')
        #         buff.seek(0)
        # buff.write(data)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n')


# @app.before_first_request
# def before_first_request():
#     log_handler = initSyslogLogger()
#     # replace werkzeug and sqlalchemy loggers
#     replaceAppLoggers(log_handler)
#
# @app.before_request
# def before_request():
#     session.permanent = True
#     if not hasattr(settings,'GUI_INACTIVE_TIMEOUT'):
#         settings.GUI_INACTIVE_TIMEOUT = 20 #20 minutes
#     app.permanent_session_lifetime = datetime.timedelta(minutes=settings.GUI_INACTIVE_TIMEOUT)
#     session.modified = True

@app.route('/error')
def showError(type="", code=500, msg=None):
    return render_template('error.html', type=type, msg=msg), code

@app.route('/')
def index():
    try:
        if (settings.DEBUG):
            debugEndpoint()

        # if not session.get('logged_in'):
        #     checkDatabase()
        return render_template('index.html', version=settings.VERSION)

    # except sql_exceptions.SQLAlchemyError as ex:
    #     debugException(ex, log_ex=False, print_ex=True, showstack=False)
    #     error = "db"
    #     db.rollback()
    #     db.flush()
    #     db.close()
    #     return render_template('index.html', version=settings.VERSION)
    # except http_exceptions.HTTPException as ex:
    #     debugException(ex, log_ex=False, print_ex=True, showstack=False)
    #     error = "http"
    #     return showError(type=error)
    except Exception as ex:
        debugException(ex, log_ex=False, print_ex=True, showstack=False)
        error = "server"
        return showError(type=error)

@app.route('/video_feed')
def video_feed():
    # TODO: temp, need to create thread-safe queue for streams and maintain them
    # connect to raspi video server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.connect((host, port))
    # socks.append(sock)

    return Response(generateVideoFrames(sock),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


def sigHandler(signum=None, frame=None):
    if signum == signal.SIGHUP.value:
        IO.logwarn("Received SIGHUP.. ignoring signal")

def replaceAppLoggers(log_handler):
    """ Handle configuration of web server loggers """

    # close current log handlers
    for handler in copy(logging.getLogger('werkzeug').handlers):
        logging.getLogger('werkzeug').removeHandler(handler)
        handler.close()
    for handler in copy(logging.getLogger('sqlalchemy').handlers):
        logging.getLogger('sqlalchemy').removeHandler(handler)
        handler.close()

    # replace vanilla werkzeug and sqlalchemy log handler
    logging.getLogger('werkzeug').addHandler(log_handler)
    logging.getLogger('werkzeug').setLevel(settings.WEB_LOG_LEVEL)
    logging.getLogger('sqlalchemy.engine').addHandler(log_handler)
    logging.getLogger('sqlalchemy.engine').setLevel(settings.WEB_LOG_LEVEL)
    logging.getLogger('sqlalchemy.dialects').addHandler(log_handler)
    logging.getLogger('sqlalchemy.dialects').setLevel(settings.WEB_LOG_LEVEL)
    logging.getLogger('sqlalchemy.pool').addHandler(log_handler)
    logging.getLogger('sqlalchemy.pool').setLevel(settings.WEB_LOG_LEVEL)
    logging.getLogger('sqlalchemy.orm').addHandler(log_handler)
    logging.getLogger('sqlalchemy.orm').setLevel(settings.WEB_LOG_LEVEL)

def initApp(flask_app):
    # Setup the Flask session manager with a random secret key
    flask_app.secret_key = os.urandom(12)

    # # Add jinja2 filters
    # flask_app.jinja_env.filters["attrFilter"] = attrFilter
    # flask_app.jinja_env.filters["yesOrNoFilter"] = yesOrNoFilter
    # flask_app.jinja_env.filters["noneFilter"] = noneFilter
    # flask_app.jinja_env.filters["imgFilter"] = imgFilter
    # flask_app.jinja_env.filters["domainTypeFilter"] = domainTypeFilter

    # Add jinja2 functions
    flask_app.jinja_env.globals.update(zip=zip)

    # # Dynamically update settings
    # fields = {}
    # fields['TELEBLOCK_GW_ENABLED'] = 0
    # fields['TELEBLOCK_GW_IP'] = '62.34.24.22'
    # fields['INTERNAL_IP_ADDR'] = getInternalIP()
    # fields['INTERNAL_IP_NET'] = "{}.*".format(getInternalIP().rsplit(".", 1)[0])
    # fields['EXTERNAL_IP_ADDR'] = getExternalIP()
    # updateConfig(settings, fields)
    # reload(settings)

    # configs depending on updated settings go here
    flask_app.env = "development" if settings.DEBUG else "production"
    flask_app.debug = settings.DEBUG

    # Flask App Manager configs
    manager = Manager(app)
    manager.add_command('runserver', CustomServer())

    # trap signals here
    signal.signal(signal.SIGHUP, sigHandler)

    # start the server
    manager.run()

def teardown():
    pass
    # try:
    #     os.remove(pid_file)
    # except:
    #     pass

# def checkDatabase():
#    # Check database connection is still good
#     try:
#         db.execute('select 1')
#         db.flush()
#     except sql_exceptions.SQLAlchemyError as ex:
#     # If not, close DB connection so that the SQL engine can get another one from the pool
#         db.close()


class CustomServer(Server):
    """ Customize the Flask server with our settings """

    def __init__(self):
        super().__init__(
            host=settings.WEB_HOST,
            port=settings.WEB_PORT
        )

        if len(settings.WEB_SSL_CERT) > 0 and len(settings.WEB_SSL_KEY) > 0:
            self.ssl_crt = settings.WEB_SSL_CERT
            self.ssl_key = settings.WEB_SSL_KEY

        if settings.DEBUG == True:
            self.use_debugger = True
            self.use_reloader = True
        else:
            self.use_debugger = None
            self.use_reloader = None
            self.threaded = True
            self.processes = 1


# main loop
if __name__ == '__main__':
    initApp(app)
    exit(0)

