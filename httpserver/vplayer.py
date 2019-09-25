import socket, subprocess, signal

video_resolution = (1640,1232) # resolution in pixels
video_fps = 40 # frames per second

buffsize = 16384
host = "192.168.1.2"
port = 10000

# connect to raspi video server
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.connect((host, port))
stream = sock.makefile('rb', buffsize)

# main loop
if __name__ == '__main__':
    player = None

    try:
        # cmdline = ['vlc', '--demux', 'mjpeg', '-']
        cmdline = [
            'mplayer',
            '-x', str(video_resolution[0]), '-y', str(video_resolution[1]),
            '-fps', str(video_fps), '-cache', str(buffsize),
            '-demuxer', 'lavf', '-'
        ]
        player = subprocess.Popen(cmdline, stdin=subprocess.PIPE)
        while True:
            data = stream.read(buffsize)
            if not data:
                break
            player.stdin.write(data)
    finally:
        # in case early termination occurs
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        stream.close()
        sock.close()
        player.terminate()

    exit(0)

