#!/usr/bin/env python3

import os, socket, signal, logging, datetime, uuid, json, weakref, struct
from copy import copy
from flask import render_template, request, redirect, session, url_for, Response, send_from_directory
from flask_script import Manager
from util.printing import IO, debugException, debugEndpoint
from util.async import thread, proc
from util.flaskcustom import CustomFlask, CustomServer, CustomSessionInterface, cleanupSessionSocks, cleanupRequestSocks
import settings


#### constant definitions
# JPEG exif file headers
SOI = b'\xff\xd8'
EOI = b'\xff\xd9'

#### module variables
active_socks = {} # { session_id: { request_id: [ socks ] } }
active_pisensors = {} # { sensor_id: (host, port) }
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
        if (settings.SHOMESEC_DEBUG):
            debugEndpoint()

        # if not session.get('logged_in'):
        #     checkDatabase()
        return render_template('index.html', version=settings.SHOMESEC_VERSION, resolution=settings.VIDEO_RESOLUTION, sensors=active_pisensors.keys())

    # except sql_exceptions.SQLAlchemyError as ex:
    #     debugException(ex, log_ex=False, print_ex=True, showstack=False)
    #     error = "db"
    #     db.rollback()
    #     db.flush()
    #     db.close()
    #     return render_template('index.html', version=settings.SHOMESEC_VERSION)
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
    stream = sock.makefile('rb', settings.VIDEO_BUFFSIZE)
    buff = b''

    # IO.printdbg('active_socks: {}'.format(str(active_socks)))
    # IO.printwarn('sock: {}'.format(str(sock)))
    # IO.printwarn('stream: {}'.format(str(stream)))

    try:
        while True:
            data = stream.read(settings.VIDEO_BUFFSIZE)
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

    sensor_id = request.args.get('sensor_id', default='', type=str)

    # create entry in active_socks for session/request
    if session['id'] not in active_socks:
        active_socks[session['id']] = {}
    if not request.id in active_socks[session['id']]:
        active_socks[session['id']][request.id] = []



    # connect to raspi video server on each sensor
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.connect(active_pisensors[sensor_id])
    except (socket.error, TypeError) as ex:
        IO.printerr('Could not connection to sensor [{}]: {}'.format(str(active_pisensors[sensor_id]), str(ex)))
        if sensor_id in active_pisensors:
            del active_pisensors[sensor_id]
        return Response()

    # store sock locally
    active_socks[session['id']][request.id].append(sock)

    return Response(generateVideoFrames(sock, session['id'], request.id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/info')
def showInfo():
    info = {
        'active_sensors': active_pisensors
    }
    return json.dumps(info), 200

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app_manager.command
def version():
    """ Print current version """
    print(settings.SHOMESEC_VERSION)

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

class SocketServer(object):
    def __init__(self, host, port):
        """
        Server initialization and socket creation
        """

        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._finalizer = weakref.finalize(self, self.close)

    def close(self):
        """
        Close socket and cleanup
        """

        self.sock.close()

    @thread
    def start(self):
        """
        Start listening for connections
        """

        self.sock.bind((self.host, self.port))
        self.sock.listen()
        print("Listening on {}".format(str(self.sock.getsockname())))

        while True:
            conn, addr = self.sock.accept()
            self.connHandler(conn, addr)

    def connHandler(self, conn, addr):
        print("Connection from {} opened".format(addr))

        try:
            # handle node synchronization request
            sensor_info = struct.unpack('<64s16si', conn.recv(settings.NODESYNC_BUFFSIZE))
            id = sensor_info[0].decode('utf-8')
            host = sensor_info[1].decode('utf-8').rstrip('\x00')
            port = sensor_info[2]

            if not id in active_pisensors:
                active_pisensors[id] = (host, port)
                print('active sensors: ', end=''); print(active_pisensors)


        except (BrokenPipeError, OSError, struct.error) as ex:
            print("Problem handling request from [{}]: {}".format(addr, str(ex)))
            # inform client to properly close
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except:
                pass
        finally:
            print('Connection from {} closed'.format(addr))
            conn.close()

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
    flask_app.env = "development" if settings.SHOMESEC_DEBUG else "production"
    flask_app.debug = settings.SHOMESEC_DEBUG
    flask_app.permanent_session_lifetime = datetime.timedelta(minutes=settings.WEB_TIMEOUT)

    # Flask App Manager configs
    app_manager.help_args = ('-?', '--help')
    app_manager.add_command('runserver', CustomServer())

    # trap signals here
    signal.signal(signal.SIGHUP, sigHandler)

    # create pid file
    os.makedirs(settings.SHOMESEC_RUN_DIR, exist_ok=True)
    with open(settings.SHOMESEC_PID_FILE, 'w') as pidfd:
        pidfd.write(str(os.getpid()))

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
        os.remove(settings.SHOMESEC_PID_FILE)
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
        SocketServer(settings.NODESYNC_HOST, settings.NODESYNC_PORT).start()
        initApp(app)
    except KeyboardInterrupt:
        exit(0)
    except Exception as ex:
        debugException(ex)
        exit(1)
    finally:
        teardown()
