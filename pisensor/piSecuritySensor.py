from time import sleep
from datetime import datetime, time
import os, sys, socket, signal
import RPi.GPIO as GPIO

# app settings
rpi_id = 0
debug = True
pid_file = '/var/run/shomesec/pisense.pid'
pivid_pid_file = '/var/run/shomesec/pivid.pid'
alarm_enabled = False
alarm_active = False
motion_sensor_enabled = True
infrared_sensor_enabled = True
door_sensor_enabled = True
window_sensor_enabled = False
record_timeout = 3 # seconds to record until checking motion sensor
loop_delay = 1 # time between full sensor checks

# network settings
server_host = '192.168.1.64'
server_port = 10000 + rpi_id

# GPIO pin settings
motion = 17 # BCM 17 (pin 11)
infrared = 23 # BCM 23 (pin 16)
door = 27 # BCM 27 (pin 13)
window = 22 # BCM 22 (pin 15)

# pin setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(infrared, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(motion, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(door, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(window, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# function definitions
def sigHandler(signum=None, frame=None):
    if signum == signal.SIGALRM.value:
        pass

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

def teardown():
    GPIO.cleanup()
    try:
        os.remove(pid_file)
    except:
        pass

# main loop
if __name__ == '__main__':
    try:
        setup()

        print("stabalizing sensors")
        sleep(3)

        while True:
            # door opening checks for alarm
            if not GPIO.input(door):
                print("door opened")
                if alarm_enabled:
                    alarm_active = True
                    print("alarm triggered")

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

    finally:
        teardown()
