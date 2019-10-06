import os, sys, socket, signal, logging, datetime, uuid, json
from copy import copy
from importlib import reload
from flask import render_template, request, redirect, session, url_for, Response, send_from_directory
from flask_script import Manager
from util.shared import *
from util.printing import IO, debugException, debugEndpoint
from util.async import thread, proc
from util.flaskcustom import CustomFlask, CustomServer, CustomSessionInterface, cleanupSessionSocks, cleanupRequestSocks
import settings


#### constant definitions
# JPEG exif file headers
SOI = b'\xff\xd8'
EOI = b'\xff\xd9'

#### server settings
# TODO: move to settings.py
pid_file = '/var/run/shomesec/piserve.pid'
video_resolution = (1640,1232)  # resolution in pixels
video_fps = 40  # frames per second
buffsize = 16384
# TODO: create protocol to automatically add pi cams (host, port)
pisensors_port = 10001 # port to listen for additional sensors


#### module variables
active_socks = {} # { session_id: { request_id: [ socks ] } }
active_pisensors = [("192.168.1.2", 10000)] # [ (host, port) ]
app = CustomFlask(__name__, static_folder="./static", static_url_path="/static",
                  session_interface=CustomSessionInterface(cleanupSessionSocks, active_socks=active_socks))
app_manager = Manager(app, with_default_commands=False)
# db = loadSession()

#### routing and app logic
# @app.before_first_request
# def before_first_request():
#     log_handler = initSyslogLogger()
#     # replace werkzeug and sqlalchemy loggers
#     replaceAppLoggers(log_handler)
#
@app.before_request
def before_request():
    session['id'] = session.get('id', uuid.uuid4().hex)
    session.permanent = True
    session.modified = True

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
        return render_template('index.html', version=settings.VERSION, resolution=video_resolution, numsensors=len(active_pisensors))

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

# this functions will continue to stream after the request context is gone
def generateVideoFrames(sock, session_id, request_id):
    stream = sock.makefile('rb', buffsize)
    buff = b''

    # IO.printdbg('active_socks: {}'.format(str(active_socks)))
    # IO.printwarn('sock: {}'.format(str(sock)))
    # IO.printwarn('stream: {}'.format(str(stream)))

    try:
        while True:
            data = stream.read(buffsize)
            # IO.printdbg('len(data): {}'.format(len(buff)))

            if len(data) == 0:
                stream.close()
                break
            buff += data

            start = buff.find(SOI)
            end = buff.find(EOI)

            # we have the full jpeg
            if start != -1 and end != -1:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buff[start:end+2] + b'\r\n')
                buff = buff[end+2:]
    finally:
        cleanupRequestSocks(active_socks, session_id, request_id)

@app.route('/video_feed')
def video_feed():
    # IO.printdbg('session id: {}'.format(session['id']))
    # IO.printdbg('request id: {}'.format(request.id))

    sensor_number = request.args.get('sensor_number', default=0, type=int)

    # create entry in active_socks for session/request
    if session['id'] not in active_socks:
        active_socks[session['id']] = {}
    if not request.id in active_socks[session['id']]:
        active_socks[session['id']][request.id] = []

    # connect to raspi video server on each sensor
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.connect(active_pisensors[sensor_number])
    except (socket.error, TypeError) as ex:
        IO.printerr('Could not connection to sensor [{}]: {}'.format(str(active_pisensors[sensor_number]), str(ex)))
        return Response()

    # store sock locally
    active_socks[session['id']][request.id].append(sock)

    return Response(generateVideoFrames(sock, session['id'], request.id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/info')
def showError():
    info = {'active_sensors': active_pisensors}
    return json.dumps(info), 200

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app_manager.command
def version():
    """ Print current version """
    print(settings.VERSION)

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
    # fields['INTERNAL_IP_ADDR'] = getInternalIP()
    # fields['INTERNAL_IP_NET'] = "{}.*".format(getInternalIP().rsplit(".", 1)[0])
    # fields['EXTERNAL_IP_ADDR'] = getExternalIP()
    # updateConfig(settings, fields)
    # reload(settings)

    # configs depending on updated settings go here
    flask_app.env = "development" if settings.DEBUG else "production"
    flask_app.debug = settings.DEBUG
    flask_app.permanent_session_lifetime = datetime.timedelta(minutes=settings.WEB_TIMEOUT)

    # Flask App Manager configs
    app_manager.help_args = ('-?', '--help')
    app_manager.add_command('runserver', CustomServer())

    # trap signals here
    signal.signal(signal.SIGHUP, sigHandler)

    # start the app server
    app_manager.run()

def teardown():
    for session_id, session_data in active_socks.items():
        for request_id, request_socks in session_data.items():
            for sock in request_socks:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                sock.close()
    try:
        os.remove(pid_file)
    except:
        pass

# def checkDatabase():
#    # Check database connection is still good
#     try:
#         db.execute('select 1')
#         db.flush()
#     except sql_exceptions.SQLAlchemyError as ex:
#     # If not, close DB connection so that the SQL engine can get another one from the pool
#         db.close()


# main loop
if __name__ == '__main__':
    try:
        with open(pid_file, 'w') as pidfd:
            pidfd.write(str(os.getpid()))
        initApp(app)
    except Exception as ex:
        print("Server Error: {}".format(str(ex)))
        raise
    finally:
        teardown()
