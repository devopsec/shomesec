import socket, subprocess, requests, json

video_resolution = (1640,1232) # resolution in pixels
video_fps = 40 # frames per second

buffsize = 16384
proto = 'http'
host = "127.0.0.1"
port = 10000

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def getVideoStream(host, port, sensor_id):
    """request video feed from web server"""

    stream = None

    try:
        # connect to web server
        sock.connect((host, port))

        stream_request = 'GET /video_feed?sensor_id={} HTTP/1.1\r\n'.format(sensor_id).encode('utf-8') + \
            'Host: {}:{}\r\n'.format(host,str(port)).encode('utf-8') + \
            b'Connection: keep-alive\r\n' + \
            b'DNT: 1\r\n' + \
            b'Accept: image/webp,image/apng,image/*,*/*;q=0.8\r\n\r\n'
        sock.send(stream_request)
        stream = sock.makefile('rb', buffsize)
    except Exception:
        print('Could not connect to web server')
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        exit(1)

    return stream


# main loop
if __name__ == '__main__':
    player = None
    stream = None

    try:
        sensor_info = json.loads(requests.get('{}://{}:{}/info'.format(proto, host, port)).text)
        sensors = sensor_info['active_sensors']

        i = 0
        sensor_key_mapping = []
        for key in sensors.keys():
            sensor_key_mapping.append(key)
            print('{}: {}'.format(str(i), key))
            i += 1

        sensor_id = None
        while True:
            print("Select a Video Camera: ", end='')
            try:
                choice = int(input())
                sensor_id = sensor_key_mapping[choice]
                break
            except:
                print('Invalid choice, try again..')

        stream = getVideoStream(host, port, sensor_id)
        print(stream)

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
        sock.close()
        if stream:
            stream.close()
        if player:
            player.terminate()

    exit(0)

