import socket, re, binascii, struct

# constants
RTF_UP = 0x0001          # route usable
RTF_GATEWAY = 0x0002     # destination is a gateway
RTF_HOST = 0x0004        # host entry (net otherwise)

def ipToStr(ip_int):
    """
    Convert integer IP to string

    :param ip_int:          integer value for ip
    :type ip_int:           int
    :return:                ipv4 address
    :rtype:                 str
    :raises ValueError:     on invalid IP conversion
    """

    try:
        return socket.inet_ntop(socket.AF_INET, struct.pack('>I', ip_int))
    except:
        pass
    raise ValueError("invalid IP address")

def ipToInt(ip_str):
    """
    Convert IP string to integer

    :param ip_str:          ipv4 address
    :type ip_str:           str
    :return:                integer value for ip
    :rtype:                 int
    :raises ValueError:     on invalid IP conversion
    """

    try:
        return int(binascii.hexlify(socket.inet_pton(socket.AF_INET, ip_str)), 16)
    except:
        pass
    raise ValueError("invalid IP address")

def getRoutingTableIPv4():
    """
    Get IPv4 routing table entries

    The addresses are stored as byte-reversed hex and must be converted by flipping byte-order

    :return:    routing table entries
    :rtype:     list
    """

    rt_entries = []

    try:
        with open('/proc/net/route', 'r') as fp:
            _ = next(fp)
            for line in fp:
                fields = line.strip().split()
                rt_entries.append({
                    'iface': fields[0],                                                         # interface name
                    'dst_addr': struct.unpack('<I', struct.pack('>I', int(fields[1], 16)))[0],  # destination network/host address
                    'gw_addr': struct.unpack('<I', struct.pack('>I', int(fields[2], 16)))[0],   # gateway address
                    'flags': int(fields[3], 16),                                                # routing flags
                    'use': int(fields[5]),                                                      # number of lookups for this route
                    'metric': int(fields[6]),                                                   # hops to target address
                    'mask': struct.unpack('<I', struct.pack('>I', int(fields[7], 16)))[0],      # network mask for destination
                    'mtu': int(fields[8])                                                       # max packet size for this route
                })
    except:
        pass
    return rt_entries

def getHostAddressesIPv4():
    """
    Get host addresses on system

    :return:    host addresses
    :rtype:     list of str
    """
    addresses = []
    try:
        with open('/proc/net/fib_trie', 'r') as fp:
            addresses = re.findall(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+/32 host', fp.read())
    except:
        pass
    return addresses


def getInternalIP():
    rt_entries = getRoutingTableIPv4()
    if len(rt_entries) == 0:
        raise Exception("could not retrieve routing table entries")
    host_addrs = getHostAddressesIPv4()
    if len(host_addrs) == 0:
        raise Exception("could not retrieve host address entries")

    def_iface_name = next(x for x in rt_entries \
                     if x['dst_addr'] == 0 and
                     x['mask'] == 0 and
                     x['flags'] & (RTF_UP | RTF_GATEWAY))['iface']
    def_iface_info = next(x for x in rt_entries \
                     if x['iface'] == def_iface_name and not
                     x['flags'] & RTF_GATEWAY)

    for addr in host_addrs:
        if ipToInt(addr) & def_iface_info['mask'] == def_iface_info['dst_addr']:
            return addr

    raise Exception("could not determine internal ip address")