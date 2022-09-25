# shared across modules in same process

def initialize():
    global number_info
    global alarm_active
    globals()['number_info'] = {}
    globals()['alarm_active'] = False

# allow references in code before initialize is called
number_info = globals()['number_info'] if 'number_info' in globals() else {}
alarm_active = globals()['alarm_active'] if 'alarm_active' in globals() else False
