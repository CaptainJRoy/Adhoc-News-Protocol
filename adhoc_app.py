import time, struct, thread, socket, sys, json, random


"""
O dicionario HELLO guarda a lista dos IPs dos vizinhos e o timestamp do ultimo refresh
Uma funcao tem que varrer a estrutura HELLO e remover os IPs mais antigos que dead_interval
A funcao que recebe os HELLOs via UDP adiciona os novos IPs na estrutura HELLO
"""


# s=json.dumps(variables)
# variables2=json.loads(s)

for i in dict_:


class Hello:
    def __init__(self, probing=10, group='ff02::1', ttl=1, deadint=600, port=9999):
        self.hello_int = probing+random.randint(0, probing*0.1)
        self.dead_interval  = deadint
        self.ipv6_group = group
        self.hellomsg = {}
        self.ttl = ttl
        self.port = port

    def run_probe(self):
        thread.start_new_thread(self.run_sender, ())
        thread.start_new_thread(self.run_listener, ())
        thread.start_new_thread(self.run_removedead, ())

    def run_sender(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        ttl_bin = struct.pack('@i', self.ttl)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        while True:
            s.sendto(self.hellomsg + '\0', (addrinfo[4][0], self.port))
            print('Hello sent!\n')
            time.sleep(self.hello_int)

    def run_listener(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', self.port))
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])

        mreq = group_bin + struct.pack('@I', 0)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        # Loop, printing any data we receive
        while True:
            data, sender = s.recvfrom(1500)
            while data[-1:] == '\0': data = data[:-1] # Strip trailing \0's
            print ('Received: ' + (str(sender).rsplit('%', 1)[0])[2:] + ' -> ' + repr(data))

    def run_removedead(self):
        for ip in self.hellomsg:
            print 'IP: 'ip, 'timestamp: ', self.hellomsg[ip];


def sender_tcp():
    global MYGROUP_6, PROBE_TIME

    #STREAM - TCP
    s = socket.socket(addrinfo[0], socket.SOCK_STREAM)
    ttl_bin = struct.pack('@i', MYTTL)
    #verificar IPv6 target
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
    while True:
        data = repr(time.time())
        s.sendto(data + '\0', (addrinfo[4][0], self.port))
        time.sleep(PROBE_TIME)




if __name__ == '__main__':
    try:
        prob = Hello()
        prob.run_probe()
    except KeyboardInterrupt:
        print('Exiting!')
