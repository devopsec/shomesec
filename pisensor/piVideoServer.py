#!/usr/bin/env python3

import socket, weakref, signal, picamera, os, select
from datetime import datetime
from time import sleep
from util.decorator import async_thread


# TODO: move to a settings.py file
pid_file = '/var/run/shomesec/pivid.pid'
video_dir = "/var/backups/videos" # video storage
video_current = os.path.join(video_dir, 'current.mjpeg')
video_resolution = (1640,1232) # resolution in pixels
video_fps = 40 # frames per second
video_timeout = 5 # timeout before recording dies (if no writes)

# capped at 4 because thats the max number of splitter ports
maxconns = 4
buffsize = 16384
host = "0.0.0.0"
port = 10000


# function definitions
def sigHandler(signum=None, frame=None):
    # note: we are only recording to file on output 0
    # start recording
    if signum == signal.SIGUSR1.value:
        server.video_outputs[0].recording = True
    # stop recording
    elif signum == signal.SIGUSR2.value:
        # only process request if previously recording
        if server.video_outputs[0].recording == True:
            filename = datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S.mjpeg')
            video_file = os.path.join(video_dir, filename)
            if os.path.exists(video_current):
                os.rename(video_current, video_file)
            server.video_outputs[0].setFile(video_current, buff=buffsize, recording=False)

def teardown():
    try:
        os.remove(pid_file)
    except:
        pass

def setup():
    # make sure video backup dir exists
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)
    # create pid file
    with open(pid_file, 'w') as pidfd:
        pidfd.write(str(os.getpid()))

# class definitions
class SplitOutput(object):
    """
    Splits output to a file and a socket
    Automatically closes socket stream on early termination
    """

    active_streams = 0

    def __init__(self, filename='', sock=None, recording=True, streaming=True, buff=None):
        self.output_file = None
        self.output_stream = None

        if buff and buff > 0:
            if len(filename) > 0:
                self.output_file = open(filename, 'wb', buffering=buff)
            if sock is not None:
                self.output_stream = sock.makefile('wb', buffering=buff)
                SplitOutput.active_streams += 1
        else:
            if len(filename) > 0:
                self.output_file = open(filename, 'wb')
            if sock is not None:
                self.output_stream = sock.makefile('wb')
                SplitOutput.active_streams += 1

        self.recording = recording
        self.streaming = streaming

    def setFile(self, filename, buff=None, recording=True):
        if buff and buff > 0:
            buffsiz = buff
        else:
            buffsiz = -1

        if self.output_file is not None:
            self.output_file.close()
        self.output_file = open(filename, 'wb', buffering=buffsiz)
        self.recording = recording

    def setSock(self, sock, buff=None, streaming=True):
        if self.output_stream:
            self.output_stream.close()
        else:
            SplitOutput.active_streams += 1
        if buff and buff > 0:
            self.output_stream = sock.makefile('wb', buffering=buff)
        else:
            self.output_stream = sock.makefile('wb')
        self.streaming = streaming

    def write(self, buff):
        if self.output_file and self.recording:
            try:
                self.output_file.write(buff)
            except ValueError:
                self.output_file = None
                self.recording = False
        if self.output_stream and self.streaming:
            try:
                self.output_stream.write(buff)
            except BrokenPipeError:
                self.output_stream.close()
                self.streaming = False
                SplitOutput.active_streams -= 1

    def flush(self):
        if self.output_file and self.recording:
            self.output_file.flush()
        if self.output_stream and self.streaming:
            self.output_stream.flush()

    def close(self):
        if self.output_file:
            self.output_file.close()
            self.recording = False
        if self.output_stream:
            self.output_stream.close()
            self.streaming = False
            SplitOutput.active_streams -= 1

class Server(object):
    def __init__(self, host, port):
        """
        Server initialization and socket creation
        """

        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.video_output = SplitOutput(video_current, recording=False, streaming=False, buff=buffsize)
        self.video_outputs = [
            SplitOutput(video_current, recording=False, streaming=False, buff=buffsize),
            SplitOutput(recording=False, streaming=False, buff=buffsize),
            SplitOutput(recording=False, streaming=False, buff=buffsize),
            SplitOutput(recording=False, streaming=False, buff=buffsize)
        ]
        self.camera = picamera.PiCamera(resolution=video_resolution, framerate=video_fps)
        self._finalizer = weakref.finalize(self, self.close)

    def close(self):
        """
        Close socket and cleanup
        """
 
        self.sock.close()
        # self.video_output.close()
        for i in range(len(self.video_outputs)):
            self.video_outputs[i].close()

        try:
            self.camera.stop_recording()
        except:
            pass
        self.camera.close()

    def start(self):
        """
        Start listening for connections
        """

        self.sock.bind((self.host, self.port))
        self.sock.listen(maxconns)
        print("Listening on {}".format(str(self.sock.getsockname())))

        for i in range(len(self.video_outputs)):
            self.camera.start_recording(self.video_outputs[i], format='mjpeg', splitter_port=i)

        while True:
            conn, addr = self.sock.accept()
            self.connHandler(conn, addr)

    @async_thread
    def connHandler(self, conn, addr):
        try:
            print("Connection from {} opened".format(addr))

            # TODO: need to keep track of available socks and split output to all of them
            # self.video_output.addSock(conn, buff=buffsize)
            self.video_outputs[SplitOutput.active_streams].setSock(conn, buff=buffsize)
            
            # while True:
            #     print("Camera is recording: {}".format(self.camera.recording))
            #     sleep(video_timeout)
            #     readable, writable, exceptional = select.select((conn,), (conn,), (), 0)
            #     # DEBUG:
            #     print('readable: ', end='');print(readable);print('writeable: ', end='');print(writable)
            #
            #     if writable[0].getpeername():
            #         pass

        except (BrokenPipeError,OSError,select.error,IndexError) as ex:
            print('Disconnect from [{}]: {}'.format(addr, str(ex)))
        except Exception as ex:
            print("Problem handling request from [{}]: {}".format(addr, str(ex)))
            # inform client and properly close on error
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except:
                pass
        finally:
            conn.close()


if __name__ == "__main__":
    signal.signal(signal.SIGUSR1, sigHandler)
    signal.signal(signal.SIGUSR2, sigHandler)

    try:
        setup()
        server = Server(host, port)
        server.start()
    except Exception as ex:
        print("Server Error: {}".format(str(ex)))
    finally:
        teardown()
