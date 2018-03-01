#!/usr/bin/env python
#
# Send/receive UDP multicast packets.
# Requires that your OS kernel supports IP multicast.
#
# Usage:
#   mcast -s (sender, IPv4)
#   mcast -s -6 (sender, IPv6)
#   mcast    (receivers, IPv4)
#   mcast  -6  (receivers, IPv6)

MYPORT = 9999
MYGROUP_6 = 'ff02::1'
MYTTL = 1 # Increase to reach other networks

import time
import struct
import socket
import sys
import thread

PROBE_TIME = 1
DICT = []



def sender_udp():
    global MYGROUP_6, PROBE_TIME
    addrinfo = socket.getaddrinfo(MYGROUP_6, None)[0]
    s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

    # Set Time-to-live (optional)
    ttl_bin = struct.pack('@i', MYTTL)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)

    packet_no = 0
    while True:
        s.sendto(str(packet_no) + '\0', (addrinfo[4][0], MYPORT))
        print('Sent: ' + str(packet_no))
        packet_no += 1
        time.sleep(PROBE_TIME)



def sender_tcp():
    global MYGROUP_6, PROBE_TIME

    #STREAM - TCP
    s = socket.socket(addrinfo[0], socket.SOCK_STREAM)
    ttl_bin = struct.pack('@i', MYTTL)
    #verificar IPv6 target
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
    while True:
        data = repr(time.time())
        s.sendto(data + '\0', (addrinfo[4][0], MYPORT))
        time.sleep(PROBE_TIME)



def receiver():
    global MYGROUP_6
    addrinfo = socket.getaddrinfo(MYGROUP_6, None)[0]
    s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

    # Allow multiple copies of this program on one machine
    # (not strictly needed)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind it to the port
    s.bind(('', MYPORT))

    group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
    # Join MYGROUP_6

    mreq = group_bin + struct.pack('@I', 0)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

    # Loop, printing any data we receive
    while True:
        data, sender = s.recvfrom(1500)
        while data[-1:] == '\0': data = data[:-1] # Strip trailing \0's
        print ('Received: ' + str(sender) + ' -> ' + repr(data))



if __name__ == '__main__':
    try:
        t1 = thread.start_new_thread(sender_udp, ())
        receiver()
    except KeyboardInterrupt:
        print('Exiting!')
