import os, sys, logging, traceback
from flask import request
from util.shared import objToDict

# modified method from Python cookbook, #475186
def supportsColor(stream):
    """ Return True if terminal supports ASCII color codes  """
    if not hasattr(stream, "isatty") or not stream.isatty():
        # auto color only on TTYs
        return False
    try:
        import curses
        curses.setupterm()
        return curses.tigetnum("colors") > 2
    except:
        # guess false in case of error
        return False

class IO():
    """ Contains static methods for handling i/o operations """

    if supportsColor(sys.stdout):
        @staticmethod
        def printerr(message):
            print('\x1b[1;31m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def printinfo(message):
            print('\x1b[1;32m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def printwarn(message):
            print('\x1b[1;33m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def printdbg(message):
            print('\x1b[1;34m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def printbold(message):
            print('\x1b[1;37m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def logcrit(message):
            logging.getLogger().log(logging.CRITICAL, '\x1b[1;31m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def logerr(message):
            logging.getLogger().log(logging.ERROR, '\x1b[1;31m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def loginfo(message):
            logging.getLogger().log(logging.INFO, '\x1b[1;32m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def logwarn(message):
            logging.getLogger().log(logging.WARNING, '\x1b[1;33m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def logdbg(message):
            logging.getLogger().log(logging.DEBUG, '\x1b[1;34m' + str(message).strip() + '\x1b[0m')

        @staticmethod
        def lognolvl(message):
            logging.getLogger().log(logging.NOTSET, '\x1b[1;37m' + str(message).strip() + '\x1b[0m')

    else:
        @staticmethod
        def printerr(message):
            print(str(message).strip())

        @staticmethod
        def printinfo(message):
            print(str(message).strip())

        @staticmethod
        def printwarn(message):
            print(str(message).strip())

        @staticmethod
        def printdbg(message):
            print(str(message).strip())

        @staticmethod
        def printbold(message):
            print(str(message).strip())

        @staticmethod
        def logcrit(message):
            logging.getLogger().log(logging.CRITICAL, str(message).strip())

        @staticmethod
        def logerr(message):
            logging.getLogger().log(logging.ERROR, str(message).strip())

        @staticmethod
        def loginfo(message):
            logging.getLogger().log(logging.INFO, str(message).strip())

        @staticmethod
        def logwarn(message):
            logging.getLogger().log(logging.WARNING, str(message).strip())

        @staticmethod
        def logdbg(message):
            logging.getLogger().log(logging.DEBUG, str(message).strip())

        @staticmethod
        def lognolvl(message):
            logging.getLogger().log(logging.NOTSET, str(message).strip())


def debugException(ex=None, log_ex=True, print_ex=True, showstack=False):
    """
    Debugging of an exception: print and/or log frame and/or stacktrace
    :param ex:          The exception object
    :param log_ex:      True | False
    :param print_ex:    True | False
    :param showstack:   True | False
    """

    # get basic info and the stack
    exc_type, exc_value, exc_tb = sys.exc_info()

    text = "((( EXCEPTION )))\n[CLASS]: {}\n[VALUE]: {}\n".format(exc_type, exc_value)
    # get detailed exception info
    if ex is None:
        ex = exc_value
    for k,v in vars(ex).items():
        text += "[{}]: {}\n".format(k.upper(), str(v))

    # determine how far we trace it back
    tb_list = None
    if showstack:
        tb_list = traceback.extract_tb(exc_tb)
    else:
        tb_list = traceback.extract_tb(exc_tb, limit=1)

    # ensure a backtrace exists first
    if tb_list is not None and len(tb_list) > 0:
        text += "((( BACKTRACE )))\n"

        for tb_info in tb_list:
            filename, linenum, funcname, source = tb_info

            if funcname != '<module>':
                funcname = funcname + '()'
            text += "[FILE]: {}\n[LINE NUM]: {}\n[FUNCTION]: {}\n[SOURCE]: {}\n".format(filename, linenum, funcname,
                                                                                      source)
    if log_ex:
        IO.logerr(text)
    if print_ex:
        IO.printerr(text)


def debugEndpoint(log_out=True, print_out=True, **kwargs):
    """
    Debug an endpoint\n
    Must be run within request context

    :param log_out:       True | False
    :param print_out:     True | False
    :param kwargs:        Any args to print / log (<key=value> key word pairs)
    """

    calling_chain = []

    frame = sys._getframe().f_back if sys._getframe().f_back is not None else sys._getframe()
    # parent module
    if hasattr(frame.f_code, 'co_filename'):
        calling_chain.append(os.path.abspath(frame.f_code.co_filename))
    # parent class
    if 'self' in frame.f_locals:
        calling_chain.append(frame.f_locals["self"].__class__)
    else:
        for k, v in frame.f_globals.items():
            if not k.startswith('__') and frame.f_code.co_name in dir(v):
                calling_chain.append(k)
                break
    # parent func
    if frame.f_code.co_name != '<module>':
        calling_chain.append(frame.f_code.co_name)

    text = "((( [DEBUG ENDPOINT]: {} )))\n".format(' -> '.join(calling_chain))
    text += '\n'.join((
        '{}: {}'.format('accept_charsets', str(request.accept_charsets).strip()),
        '{}: {}'.format('accept_encodings', str(request.accept_encodings).strip()),
        '{}: {}'.format('accept_languages', str(request.accept_languages).strip()),
        '{}: {}'.format('accept_mimetypes', str(request.accept_mimetypes).strip()),
        '{}: {}'.format('access_control_request_headers', str(request.access_control_request_headers).strip()),
        '{}: {}'.format('access_control_request_method', str(request.access_control_request_method).strip()),
        '{}: {}'.format('access_route', str(request.access_route).strip()),
        '{}: {}'.format('args', str(request.args).strip()),
        '{}: {}'.format('authorization', str(request.authorization).strip()),
        '{}: {}'.format('base_url', str(request.base_url).strip()),
        '{}: {}'.format('blueprint', str(request.blueprint).strip()),
        '{}: {}'.format('cache_control', str(request.cache_control).strip()),
        '{}: {}'.format('charset', str(request.charset).strip()),
        '{}: {}'.format('content_encoding', str(request.content_encoding).strip()),
        '{}: {}'.format('content_length', str(request.content_length).strip()),
        '{}: {}'.format('content_md5', str(request.content_md5).strip()),
        '{}: {}'.format('content_type', str(request.content_type).strip()),
        '{}: {}'.format('cookies', str(request.cookies).strip()),
        '{}: {}'.format('files', str(request.files).strip()),
        '{}: {}'.format('form', str(request.form).strip()),
        '{}: {}'.format('headers', str(request.headers).strip()),
        '{}: {}'.format('json', str(request.get_json(force=True, silent=True)).strip()),
        '{}: {}'.format('method', str(request.method).strip()),
        '{}: {}'.format('query_string', str(request.query_string).strip()),
        '{}: {}'.format('referrer', str(request.referrer).strip()),
        '{}: {}'.format('remote_addr', str(request.remote_addr).strip()),
        '{}: {}'.format('remote_user', str(request.remote_user).strip()),
        '{}: {}'.format('url', str(request.url).strip()),
        '{}: {}'.format('user_agent', str(request.user_agent).strip()),
        '{}: {}'.format('values', str(request.values).strip()),
        '{}: {}'.format('view_args', str(request.view_args).strip()),
    ))

    if len(kwargs) > 0:
        for k, v in sorted(kwargs):
            text += "{}: {}\n".format(k, str(v).strip())

    if log_out:
        IO.logdbg(text)

    if print_out:
        IO.printdbg(text)