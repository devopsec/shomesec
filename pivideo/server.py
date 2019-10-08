#!/usr/bin/env python3

import socket, weakref, signal, picamera, os, select
from datetime import datetime
from time import sleep
from util.async import thread
from util.printing import debugException
import settings


# TODO: switch to udp for better performance

# TODO: move to a settings.py file
run_dir = '/var/run/shomesec'
pid_file = '/var/run/shomesec/pivid.pid'
video_dir = "/var/backups/videos" # video storage
video_current = os.path.join(video_dir, 'current.mjpeg')
video_resolution = (1640,1232) # resolution in pixels
video_fps = 40 # frames per second
video_timeout = 5 # timeout before recording dies (if no writes)

# capped at 4 because thats the max number of splitter ports
maxconns = 4
buffsize = 16384


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
    os.makedirs(video_dir, exist_ok=True)
    # create pid file
    os.makedirs(run_dir, exist_ok=True)
    with open(pid_file, 'w') as pidfd:
        pidfd.write(str(os.getpid()))


class StreamingOutput(object):
    """
    Streams output socket conditionally
    Automatically closes socket stream on early termination
    """

    _active_streams = 0

    def __init__(self, sock=None, streaming=True, buff=None):
        self.output_stream = None

        if buff and buff > 0:
            if sock is not None:
                self.output_stream = sock.makefile('wb', buffering=buff)
                StreamingOutput.setActiveStreams(StreamingOutput.getActiveStreams() + 1)
        else:
            if sock is not None:
                self.output_stream = sock.makefile('wb')
                StreamingOutput.setActiveStreams(StreamingOutput.getActiveStreams() + 1)

        self.streaming = streaming

    @classmethod
    def getActiveStreams(cls):
        super_class = cls.mro()[1]
        if not super_class.__name__ == 'object':
            return super_class.getActiveStreams()
        else:
            return cls._active_streams

    @classmethod
    def setActiveStreams(cls, value):
        super_class = cls.mro()[1]
        if not super_class.__name__ == 'object':
            super_class.setActiveStreams(value)
        else:
            cls._active_streams = value

    def setSock(self, sock, buff=None, streaming=True):
        if self.output_stream:
            self.output_stream.close()
        else:
            StreamingOutput.setActiveStreams(StreamingOutput.getActiveStreams() + 1)
        if buff and buff > 0:
            self.output_stream = sock.makefile('wb', buffering=buff)
        else:
            self.output_stream = sock.makefile('wb')
        self.streaming = streaming

    def write(self, buff):
        if self.output_stream and self.streaming:
            try:
                self.output_stream.write(buff)
            except BrokenPipeError:
                self.output_stream.close()
                self.streaming = False
                StreamingOutput.setActiveStreams(StreamingOutput.getActiveStreams() - 1)

    def flush(self):
        if self.output_stream and self.streaming:
            self.output_stream.flush()

    def close(self):
        if self.output_stream:
            self.output_stream.close()
            self.streaming = False
            StreamingOutput.setActiveStreams(StreamingOutput.getActiveStreams() - 1)

class SplitOutput(StreamingOutput):
    """
    Splits output to a file and a socket
    Automatically closes socket stream on early termination
    """

    def __init__(self, filename='', sock=None, recording=True, streaming=True, buff=None):
        self.output_file = None

        if buff and buff > 0:
            if len(filename) > 0:
                self.output_file = open(filename, 'wb', buffering=buff)
        else:
            if len(filename) > 0:
                self.output_file = open(filename, 'wb')

        self.recording = recording
        super().__init__(sock, streaming, buff)

    def setFile(self, filename, buff=None, recording=True):
        if buff and buff > 0:
            buffsiz = buff
        else:
            buffsiz = -1

        if self.output_file is not None:
            self.output_file.close()
        self.output_file = open(filename, 'wb', buffering=buffsiz)
        self.recording = recording

    def write(self, buff):
        if self.output_file and self.recording:
            try:
                self.output_file.write(buff)
            except ValueError:
                self.output_file = None
                self.recording = False
        super().write(buff)

    def flush(self):
        if self.output_file and self.recording:
            self.output_file.flush()
        super().flush()

    def close(self):
        if self.output_file:
            self.output_file.close()
            self.recording = False
        super().close()

class Server(object):
    def __init__(self, host, port):
        """
        Server initialization and socket creation
        """

        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.video_outputs = [
            SplitOutput(video_current, recording=False, streaming=False, buff=buffsize),
            StreamingOutput(streaming=False, buff=buffsize),
            StreamingOutput(streaming=False, buff=buffsize),
            StreamingOutput(streaming=False, buff=buffsize),
        ]
        self.camera = picamera.PiCamera(resolution=video_resolution, framerate=video_fps)
        self._finalizer = weakref.finalize(self, self.close)

    def close(self):
        """
        Close socket and cleanup
        """
 
        self.sock.close()
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

        # for i in range(len(self.video_outputs)):
        #     self.camera.start_recording(self.video_outputs[i], format='mjpeg', splitter_port=i)

        # the first camera output must always be recording in case we get a signal to output to file
        self.camera.start_recording(self.video_outputs[0], format='mjpeg', splitter_port=0)

        while True:
            conn, addr = self.sock.accept()
            self.connHandler(conn, addr)

    @thread
    def connHandler(self, conn, addr):
        print("Connection from {} opened".format(addr))

        active_streams = SplitOutput.getActiveStreams()
        print('active streams: {}'.format(active_streams))

        try:
            # if active streams is 0 use the tell the camera thread to handle it with split output
            if active_streams  == 0:
                self.video_outputs[0].setSock(conn, buff=buffsize)

            # otherwise we need to handle recording with this new thread
            else:
                self.video_outputs[active_streams].setSock(conn, buff=buffsize)
                self.camera.start_recording(self.video_outputs[active_streams], format='mjpeg', splitter_port=active_streams)
                while True:
                    sleep(video_timeout)
                    if not self.video_outputs[active_streams].streaming:
                        self.camera.stop_recording(splitter_port=active_streams)
                        break

        except (BrokenPipeError, OSError, IndexError) as ex:
            print("Problem handling request from [{}]: {}".format(addr, str(ex)))
            # inform client to properly close
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except:
                pass
        finally:
            print('Connection from {} closed'.format(addr))
            conn.close()

            # readable, writable, exceptional = select.select((conn,), (conn,), (), 0)
            # # SHOMESEC_DEBUG:
            # print('readable: ', end='');print(readable);print('writeable: ', end='');print(writable)
            #
            # if writable[0].getpeername():
            #     pass

        # except (BrokenPipeError,OSError,select.error,IndexError) as ex:
        #     print('Disconnect from [{}]: {}'.format(addr, str(ex)))
        # except Exception as ex:
        #     print("Problem handling request from [{}]: {}".format(addr, str(ex)))
        # finally:
        #     print('Connection from {} closed'.format(addr))
        #     # inform client to properly close
        #     try:
        #         conn.shutdown(socket.SHUT_RDWR)
        #     except:
        #         pass
        #     conn.close()


if __name__ == "__main__":
    try:
        setup()
        server = Server(settings.VIDEO_HOST, settings.VIDEO_PORT)
        signal.signal(signal.SIGUSR1, sigHandler)
        signal.signal(signal.SIGUSR2, sigHandler)
        server.start()
    except KeyboardInterrupt:
        exit(0)
    except Exception as ex:
        debugException(ex)
        exit(1)
    finally:
        teardown()
