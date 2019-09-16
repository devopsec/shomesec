#!/usr/bin/env python3

from datetime import datetime
import socket, weakref, signal, picamera, os, select
from time import sleep

# server settings
pid_file = '/var/run/shomesec/pivid.pid'
video_dir = "/var/backups/videos" # video storage
video_current = os.path.join(video_dir, 'current.mjpeg')
video_resolution = (1280,720) # resolution in pixels
video_fps = 30 # frames per second
video_timeout = 5 # timeout before recording dies (if no writes)

maxconns = 1
buffsize = 4096
host = "0.0.0.0"
port = 10000
server = None
framesize = video_resolution[0] * video_resolution[1] * 3


# function definitions
def sigHandler(signum=None, frame=None):
    # start recording
    if signum == signal.SIGUSR1.value:
        server.video_output.recording = True
    # stop recording
    elif signum == signal.SIGUSR2.value:
        # only process request if previously recording
        if server.video_output.recording == True:
            filename = datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S.mjpeg')
            video_file = os.path.join(video_dir, filename)
            if os.path.exists(video_current):
                os.rename(video_current, video_file)
            server.video_output.setFile(video_current, buff=framesize, recording=False)

def teardown():
    if server:
        del server
    os.remove(pid_file)


# class definitions
class SplitOutput(object):
    """
    Splits output to a file and a socket
    Automatically closes socket stream on early termination
    """
    def __init__(self, filename=None, sock=None, recording=True, streaming=True, buff=None):
        self.output_file = None
        self.output_stream = None

        if buff and buff > 0:
            if filename:
                self.output_file = open(filename, 'wb', buffering=buff)
            if sock:
                self.output_stream = sock.makefile('wb', buffering=buff)
        else:
            if filename:
                self.output_file = open(filename, 'wb')
            if sock:
                self.output_stream = sock.makefile('wb')

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
                self.output_stream = None
                self.streaming = False

    def flush(self):
        if self.output_file and self.recording:
            self.output_file.flush()
        if self.output_stream and self.streaming:
            self.output_stream.flush()

    def close(self):
        if self.output_file:
            self.output_file.close()
        if self.output_stream:
            self.output_stream.close()

class Server(object):
    def __init__(self, host, port):
        """
        Server initialization and socket creation
        """

        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.video_output = SplitOutput(video_current, recording=False, streaming=False, buff=buffsize)
        self.camera = picamera.PiCamera(resolution=video_resolution, framerate=video_fps)
        self._finalizer = weakref.finalize(self, self.close)

    def close(self):
        """
        Close socket and cleanup
        """
 
        self.sock.close()
        self.video_output.close()

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

        self.camera.start_recording(self.video_output, format='mjpeg')

        while True:
            conn, addr = self.sock.accept()
            self.connHandler(conn, addr)

    def connHandler(self, conn, addr):
        try:
            print("Connection from {} opened".format(addr))

            self.video_output.setSock(conn, buff=buffsize)
            
            while True:
                print("Camera is recording: {}".format(self.camera.recording))
                sleep(video_timeout)
                readable, writable, exceptional = select.select((conn,), (conn,), (), 0)
                if writable[0].getpeername():
                    pass

        except (BrokenPipeError,OSError,select.error,IndexError) as ex:
            print('Disconnect reason: {}'.format(str(ex)))
            pass
        except Exception as ex:
            print("Problem handling request: {}".format(str(ex)))
            # inform client and properly close on error
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except:
                pass
        finally:
            print("Connection from {} closed".format(addr))
            conn.close()


if __name__ == "__main__":
    signal.signal(signal.SIGUSR1, sigHandler)
    signal.signal(signal.SIGUSR2, sigHandler)

    try:
        with open(pid_file, 'w') as pidfd:
            pidfd.write(str(os.getpid()))
        server = Server(host, port)
        server.start()
    except Exception as ex:
        print("Server Error: {}".format(str(ex)))
        raise
    finally:
        teardown()
