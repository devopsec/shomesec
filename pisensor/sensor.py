#!/usr/bin/env python3

import os, sys, socket, signal, struct, hashlib, binascii, re, tzlocal
import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime
if sys.version_info.major == 3 and sys.version_info.minor < 9:
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo
from iso6709 import Location
from suntime import Sun
import settings, globals
from util.pyasync import proc
from util.notifications import sendEmail, sendSMS
from util.networking import getInternalIP
from util.printing import debugException


# TODO: move to settings.py
#### app settings
debug = True
run_dir = '/run/shomesec'
pid_file = os.path.join(run_dir, 'pisense.pid')
pivid_pid_file = os.path.join(run_dir, 'pivid.pid')
alarm_enabled = False
motion_sensor_enabled = True
door_sensor_enabled = True
window_sensor_enabled = False
camera_infrared_enabled = True
record_timeout = 3 # seconds to record until checking motion sensor
loop_delay = 1 # time between full sensor checks

#### GPIO pin settings
motion = 17 # GPIO 17 (pin 11)
infrared = 23 # GPIO 23 (pin 16)
door = 27 # GPIO 27 (pin 13)
window = 22 # GPIO 22 (pin 15)

#### timezone variables
tz_name = ""
tz_sun_info = object()

#### function definitions
def setTimezoneInfo():
    global tz_name, tz_to_coords, tz_sun_info

    tz_name = tzlocal.get_localzone_name()

    with open('/usr/share/zoneinfo/zone1970.tab', 'r') as f:
        for line in f:
            if line[0] == '#':
                continue

            fields = line.split('\t')
            fields[2] = fields[2].strip()
            if fields[2] != tz_name:
                continue

            loc = Location(re.search(r'((?:\+|-)[0-9]+(?:\+|-)[0-9]+)', fields[1]).groups()[0])
            #tz_to_coords = {}
            #tz_to_coords[fields[2].strip()] = [int(x) for x in re.search(r'((?:\+|-)[0-9]+)((?:\+|-)[0-9]+)', fields[1]).groups()]

    tz_sun_info = Sun(float(loc.lat.decimal), float(loc.lng.decimal))

def sigHandler(signum=None, frame=None):
    if signum == signal.SIGALRM.value:
        globals.alarm_active = True
        print("alarm triggered")

        text_msg = 'Your Alarm was Triggered at {}'.format(str(datetime.now()))
        html_msg = ('<html><head><style>.error{{border: 1px solid; margin: 10px 0px; padding: 15px 10px 15px 50px; background-color: #FF5555;}}</style></head>'
                    '<body><div class="error"><strong>{}</strong></div></body>').format(text_msg)
        sendEmail(settings.ALARM_NOTIFY_EMAILS, text_msg, html_msg)
        sendSMS(settings.ALARM_NOTIFY_NUMBERS, text_msg, html_msg)

def record():
    try:
        with open(pivid_pid_file, 'r') as f:
            pivid_pid = f.read()

        if len(pivid_pid) > 0:
            pivid_pid = int(pivid_pid)
            # tell the pivid proc to record to file

            os.kill(pivid_pid, signal.SIGUSR1)
            print("recording to file")
    except (FileNotFoundError, ProcessLookupError):
        print("pivid process is dead")

def norecord():
    try:
        with open(pivid_pid_file, 'r') as f:
            pivid_pid = f.read()

        if len(pivid_pid) > 0:
            pivid_pid = int(pivid_pid)
            # tell the pivid proc to stop recording to file

            os.kill(pivid_pid, signal.SIGUSR2)
            print("not recording to file")
    except (FileNotFoundError, ProcessLookupError):
        print("pivid process is dead")

def setIR():
    if not camera_infrared_enabled:
        GPIO.output(infrared, GPIO.HIGH)
        print("Camera IR Disabled")
    else:
        now = datetime.now(tz=ZoneInfo(tz_name))
        datenow = now.date()
        sunrise = tz_sun_info.get_local_sunrise_time(datenow)
        sunset = tz_sun_info.get_local_sunset_time(datenow)
        if now < sunrise or now > sunset:
            GPIO.output(infrared, GPIO.LOW)
            print("Camera IR Active")
        else:
            GPIO.output(infrared, GPIO.HIGH)
            print("Camera IR Inactive")

def syncCurrentNode(ip):
    """send node info to web server"""
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.connect((settings.NODESYNC_HOST, settings.NODESYNC_PORT))
        nodeid = binascii.hexlify(hashlib.sha256(bytes(ip+str(settings.VIDEO_PORT), 'utf-8')).digest())
        host = ip.encode('utf-8')
        port = settings.VIDEO_PORT
        req = struct.pack('<64s16si',nodeid,host,port)
        sock.send(req)
    except Exception:
        print('Could not connect to web server')
    finally:
        sock.close()

@proc
def runSyncManager(delay):
    """Run in the background constantly updating web server"""

    internal_ip = getInternalIP()

    while True:
        syncCurrentNode(internal_ip)
        sleep(delay)


def setup():
    # setup GPIO pins
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(infrared, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(motion, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(door, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(window, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    # initialize globals
    globals.initialize()

    # set variables for all processes to use
    setTimezoneInfo()

    # create pid file
    os.makedirs(run_dir, exist_ok=True)
    with open(pid_file, 'w') as pidfd:
        pidfd.write(str(os.getpid()))

    # catch signals
    signal.signal(signal.SIGALRM, sigHandler)

    # send data to the webserver in a separate process
    runSyncManager(settings.NODESYNC_DELAY)

def teardown():
    GPIO.cleanup()
    try:
        os.remove(pid_file)
    except:
        pass

def main():
    print("stabalizing sensors")
    sleep(3)

    while True:
        # door opening checks for alarm
        if not GPIO.input(door):
            print("door opened")
            if alarm_enabled:
                # trigger alarm once until disarmed
                if not globals.alarm_active:
                    os.kill(os.getpid(), signal.SIGALRM)

        # motion activates video recording to file
        if GPIO.input(motion):
            print("detected movement")
            setIR()
            record()
        else:
            print("no movement")
            norecord()

        # delay between checks
        sleep(loop_delay)

#### main loop
if __name__ == '__main__':
    try:
        setup()
        main()
    except KeyboardInterrupt:
        exit(0)
    except Exception as ex:
        debugException(ex, showstack=True)
        exit(1)
    finally:
        teardown()
