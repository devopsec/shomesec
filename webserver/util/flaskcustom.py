import uuid, socket
from flask import Flask, Request, session, request
from flask.sessions import SecureCookieSessionInterface
from itsdangerous import BadSignature, SignatureExpired
from util.printing import IO
from util.shared import totalSeconds


class CustomRequest(Request):
    """ Customize Flask Request to create unique id per request """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = uuid.uuid4().hex

class CustomSessionInterface(SecureCookieSessionInterface):
    """ Customize Flask Session to support callbacks on session timeout """

    @staticmethod
    def noop(*args, **kwargs):
        return None

    def __init__(self, session_timeout_callback=noop, **callback_kwargs):
        self.session_timeout_callback = session_timeout_callback
        self.callback_kwargs = callback_kwargs

    def open_session(self, app, request):
        s = self.get_signing_serializer(app)
        if s is None:
            return None
        val = request.cookies.get(app.session_cookie_name)
        if not val:
            return self.session_class()
        max_age = totalSeconds(app.permanent_session_lifetime)
        try:
            data = s.loads(val, max_age=max_age)
            return self.session_class(data)
        except SignatureExpired:
            self.session_timeout_callback(**self.callback_kwargs)
        except BadSignature:
            return self.session_class()


class CustomFlask(Flask):
    """ Customize Flask app to use custom methods / classes """
    request_class = CustomRequest

    def __init__(self, *args, **kwargs):
        """ if session_interface is given it should be an instance of the class """
        if 'session_interface' in kwargs:
            CustomFlask.session_interface = kwargs.pop('session_interface')
        else:
            CustomFlask.session_interface = CustomSessionInterface()
        super().__init__(*args, **kwargs)

def cleanupSessionSocks(active_socks, session_id=None):
    if not session:
        session_id = session_id
    else:
        session_id = session['id']
        
    # SHOMESEC_DEBUG:
    IO.printwarn('[session] disconnecting socks: {}'.format(str(active_socks[session_id])))

    if session_id in active_socks:
        for request_id, request_socks in active_socks[session_id].items():
            for sock in request_socks:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                sock.close()
        del active_socks[session_id]

def cleanupRequestSocks(active_socks, session_id=None, request_id=None):
    if not session:
        session_id = session_id
    else:
        session_id = session['id']
    if not request:
        request_id = request_id
    else:
        request_id = request.id
    
    if session_id in active_socks:
        if request_id in active_socks[session_id]:
            # SHOMESEC_DEBUG:
            IO.printwarn('[request] disconnecting socks: {}'.format(str(active_socks[session_id][request_id])))

            for sock in active_socks[session_id][request_id]:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                sock.close()
