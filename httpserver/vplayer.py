import socket, subprocess, signal

video_resolution = (1640,1232) # resolution in pixels
video_fps = 40 # frames per second

buffsize = 16384
host = "192.168.1.2"
port = 10000

# video cam to connect to
video_sensor = 0

# http request to video server
request = b'GET /video_feed?sensor_number=0 HTTP/1.1\r\n' + \
    'Host: {}:{}\r\n'.format(host,str(port)).encode() + \
    b'Connection: keep-alive\r\n' + \
    b'DNT: 1\r\n' + \
    b'Accept: image/webp,image/apng,image/*,*/*;q=0.8\r\n\r\n'


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

        sock.send(request)

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

