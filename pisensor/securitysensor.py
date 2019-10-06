from time import sleep
from datetime import datetime, time
import os, sys, socket, signal
import RPi.GPIO as GPIO
import settings
from util.notifications import sendEmail, sendSMS

#### app settings
debug = True
pid_file = '/var/run/shomesec/pisense.pid'
pivid_pid_file = '/var/run/shomesec/pivid.pid'
alarm_enabled = False
alarm_active = False
motion_sensor_enabled = True
infrared_sensor_enabled = True
door_sensor_enabled = True
window_sensor_enabled = False
camera_infrared_disabled = True
record_timeout = 3 # seconds to record until checking motion sensor
loop_delay = 1 # time between full sensor checks

#### network settings
# TODO: create protocol to automatically add pi cams (host, port)
webserver_host = '192.168.1.64'
pisensors_port = 10001

#### GPIO pin settings
motion = 17 # BCM 17 (pin 11)
infrared = 23 # BCM 23 (pin 16)
door = 27 # BCM 27 (pin 13)
window = 22 # BCM 22 (pin 15)

#### pin setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(infrared, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(motion, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(door, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(window, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#### function definitions
def sigHandler(signum=None, frame=None):
    global alarm_active

    if signum == signal.SIGALRM.value:
        alarm_active = True
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
    if camera_infrared_disabled:
        GPIO.output(infrared, GPIO.HIGH)
        print("Camera IR Disabled")
    else:
        timenow = datetime.now().time()
        approx_sunrise = time(7,0)
        approx_sunset = time(18,0)
        if timenow < approx_sunrise or timenow > approx_sunset:
            GPIO.output(infrared, GPIO.LOW)
            print("Camera IR Active")
        else:
            GPIO.output(infrared, GPIO.HIGH)
            print("Camera IR Inactive")

def setup():
    # create pid file
    with open(pid_file, 'w') as pidfd:
        pidfd.write(str(os.getpid()))
    # catch signals
    signal.signal(signal.SIGALRM, sigHandler)

def teardown():
    GPIO.cleanup()
    try:
        os.remove(pid_file)
    except:
        pass

def main():
    global alarm_active

    print("stabalizing sensors")
    sleep(3)

    while True:
        # door opening checks for alarm
        if not GPIO.input(door):
            print("door opened")
            if alarm_enabled:
                # trigger alarm once until disarmed
                if not alarm_active:
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
    finally:
        teardown()
