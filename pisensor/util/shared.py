import re, inspect, string, random

def objToDict(obj):
    """
    converts an arbitrary object to dict
    """
    return dict((attr, getattr(obj, attr)) for attr in dir(obj) if
                not attr.startswith('__') and not inspect.ismethod(getattr(obj, attr)))


def rowToDict(row):
    """
    converts sqlalchemy row object to python dict
    does not recurse through relationships
    tries table data, then _asdict() method, then objToDict()
    """
    d = {}

    if hasattr(row, '__table__'):
        for column in row.__table__.columns:
            d[column.name] = str(getattr(row, column.name))
    elif hasattr(row, '_asdict'):
        d = row._asdict()
    elif hasattr(row, '__dict__'):
        d = row.__dict__
        d.pop('_sa_instance_state', None)
    else:
        d = objToDict(row)

    return d


def strFieldsToDict(fields_str):
    return dict(field.split(':') for field in fields_str.split(','))


def dictToStrFields(fields_dict):
    return ','.join("{}:{}".format(k, v) for k, v in fields_dict.items())


def updateConfig(config_obj, field_dict):
    config_file = "<no filepath available>"
    try:
        config_file = config_obj.__file__

        with open(config_file, 'r+') as config:
            config_str = config.read()
            for key, val in field_dict.items():
                regex = r"^(?!#)(?:" + re.escape(key) + \
                        r")[ \t]*=[ \t]*(?:\w+\(.*\)[ \t\v]*$|[\w\d\.]+[ \t]*$|\{.*\}|\[.*\][ \t]*$|\(.*\)[ \t]*$|\"\"\".*\"\"\"[ \t]*$|'''.*'''[ \v]*$|\".*\"[ \t]*$|'.*')"
                replace_str = "{} = {}".format(key, repr(val))
                config_str = re.sub(regex, replace_str, config_str, flags=re.MULTILINE)
            config.seek(0)
            config.write(config_str)
            config.truncate()
    except:
        print('Problem updating the {0} configuration file').format(config_file)


def stripDictVals(d):
    for key, val in d.items():
        if isinstance(val, str):
            d[key] = val.strip()
        elif isinstance(val, int):
            d[key] = int(str(val).strip())
    return d

def generateID(size=10, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def generatePassword(size=10, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))