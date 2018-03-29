import time, struct, socket, sys, json
import _thread, math, random, datetime, subprocess
"""
Dicionario hello guarda a lista dos IPs dos vizinhos e o timestamp do ultimo refresh
Cada no recebera hellos de seus vizinhos, que por sua vez tera a lista dos vizinhos dos vizinhos.
A tabela tera portanto dois niveis.
Caso seja necessario enviar algo para alguem fora da lista,  no tera que enviar um route_request para os vizinhos e receber um route_reply com a devida rota.
Uma funcao tem que varrer a estrutura hello e remover os IPs mais antigos que dead_interval
A funcao que recebe os hellos via UDP adiciona os novos IPs na estrutura hello
"""


ROUTING_TABLE = {}



class Hello:
    #Iniciar a classe Hello
    def __init__(self, probing=10, group='ff02::1', deadint=600, port=9999):
        """
            @self.hello_int - intervalo de tempo entre envio de pacotes hello
            @self.dead_interval - intervalo de tempo ate considerar um no desconectado
            @self.ipv6_group - grupo ipv6 do equipamento que executa o programa
            @self.hello - dicionario de vizinhos, sendo a key o seu nome, contendo o ip e o rtt desde o nodo até ao vizinho como value
            @self.port - porta para comunicar o protocolo hello
            @self.name - nome do nodo
        """
        self.hello_int = probing+random.randint(0, probing*0.1)
        self.dead_interval  = deadint
        self.ipv6_group = group
        self.hello = {}
        self.table = {}
        self.port = port
        self.name = sys.argv[1]
    """
        Corre as threads que enviam mensagens hello, contendo o seu dicionario,
        que escutam por mensagens hello, que contem o dicionario dos vizinhos,
        que removem os vizinhos que ja nao respondem
    """
    def run_probe(self):
        try:
            _thread.start_new_thread(self.udp, ())
            self.run_removedead()
        except:
            print("Error in thread!")

    def udp(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        sender = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        listener = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        _thread.start_new_thread(self.run_sender, (sender,addrinfo,))
        _thread.start_new_thread(self.run_listener, (listener,addrinfo,))
        _thread.start_new_thread(self.recv_input, ())

    """
    """
    def route_reply(self, stamp, nameViz,  path,  nameNode, timeout):
        if((int(time.time())-stamp <= timeout)):
            addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
            s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
            ttl_bin = struct.pack('@i', 1) #ttl=1
            s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
            bytes_to_send = json.dumps([2, nameNode, path, stamp, timeout]).encode()
            ip = self.table[nameViz][1]
            s.sendto(bytes_to_send, (ip, self.port)) #Enviar os vizinhos diretos
        else:
            print(str(int(time.time())-stamp))



    """
    """
    def route_request(self, stamp, name, ttl, path, timeout):
        if((int(time.time())-stamp) <= timeout):
            if name not in self.table:
                if(path == None):
                    path = [self.name]
                else:
                    path.append(self.name)
                addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
                s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
                ttl_bin = struct.pack('@i', ttl) #ttl=1
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
                bytes_to_send = json.dumps([1, stamp, name, ttl-1, path, timeout]).encode()
                s.sendto(bytes_to_send, (addrinfo[4][0], self.port)) #Enviar os vizinhos diretos
            else:
                nameViz = path.pop()
                path.append(self.name)
                self.route_reply(stamp ,nameViz, path, name, timeout)
        else:
            print(str(int(time.time())-stamp))




    """
    """
    def recv_input(self):
        try:
            while True:
                inp = input()
                array = inp.split()
                if array[0] == "ROUTE" and array[1] == "REQUEST":
                    self.route_request(int(time.time()), array[2], int(array[3]), [], int(array[4]))

        except EOFError:
            pass

    """
        Thread que envia a mensagem hello, enviando o seu dicionario, contendo
        os seus vizinhos diretos, enviando para o grupo IPv6 (self.ipv6_group)
        atraves de UDP (socket.SOCK_DGRAM), com apenas TTL=1 (ttl_bin)
    """
    def run_sender(self, s, addrinfo):
        ttl_bin = struct.pack('@i', 1) #ttl=1
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        #_thread.start_new_thread(self.recv_input, s, addrinfo[4][0])
        while True:
            self.hello = {}
            for nameViz in self.table:
                if nameViz == self.table[nameViz][0]:
                    self.hello[nameViz] = self.table[nameViz][3]
            #primeiro valor a 0 significa que é um Hello
            bytes_to_send = json.dumps([0, int(time.time()), self.name, self.hello]).encode()
            s.sendto(bytes_to_send, (addrinfo[4][0], self.port)) #Enviar os vizinhos diretos
            time_add = random.randrange(-math.floor(self.hello_int * 0.1),
                                         math.floor(self.hello_int * 0.1))
            time.sleep(self.hello_int + time_add)  #tempo de probe entre hello_int +- variaçao tempo

    """
        Atualiza a self.table com as informações do vizinho em questão, atualizando o valor na tabela caso:
        1. O nome do vizinho que enviou for igual, atualizando as informações, caso a rede tenha mudado
        2. O rtt for menor
        3. Não exista registo na tabela desse vizinho
        @senderName - Nome do vizinho que enviou o hello
        @senderIP - IP do vizinho que envou o hello
        @vizName - Nome de um dos vizinhos contidos no hello
        @vizInfo - Array que contêm o ip do vizinho contido no hello, e o rtt da ligação
        @timeStamp - Tempo de quando recebeu o pacote hello
        @rtt - RTT desde este nodo até ao vizinho que enviou o hello
    """
    def updateTable(self, senderName, senderIP, vizName, vizRTT, timeStamp, rtt):
        if vizName in self.table:
            data = self.table[vizName]
            if(data[0] == senderName or data[4] >= (rtt+vizRTT) or (timeStamp - data[3] < 20000)):
                self.table[vizName] = [senderName, senderIP, timeStamp, rtt+int(vizRTT)]
        else:
            self.table[vizName] = [senderName, senderIP, timeStamp, rtt+int(vizRTT)]



    def run_listener(self, s, addrinfo):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', self.port))
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
        mreq = group_bin + struct.pack('@I', 0)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        # Loop, printing any data we receive
        while True:
            data, sender = s.recvfrom(1500)
            #while data[-1:] == '\0': data = data[:-1] # Strip trailing \0's
            array = json.loads(data.decode())
            tipo = array[0]
            if tipo == 0:
                timeStamp = array[1]
                rtt = int(time.time())-timeStamp
                senderName = array[2]
                vizinhos = array[3]
                senderIP = (str(sender).rsplit('%', 1)[0])[2:] #Retirar apenas o IPv6
                #print ("Recebido de "+ senderIP + ' -> ' + str(array) + " com roundtrip de: " + str(int(time.time())-int(timeStamp)))
                if senderName != self.name:
                    self.updateTable(senderName, senderIP, senderName, 0, timeStamp, rtt)
                    for vizName in vizinhos:
                        if vizName != self.name:
                            self.updateTable(senderName, senderIP, vizName, vizinhos.get(vizName), timeStamp, rtt)
                    #print(self.table)
            if tipo == 1:
                path = array[4]
                if self.name not in path:
                    timeStamp = array[1]
                    name = array[2]
                    ttl = array[3]
                    timeout = array[5]
                    self.route_request(timeStamp, name, ttl, path, timeout)
            if tipo == 2:
                senderIP = (str(sender).rsplit('%', 1)[0])[2:] #Retirar apenas o IPv6
                nameNode = array[1]
                path = array[2]
                stamp = array[3]
                timeout = array[4]
                nameViz = path.pop()
                self.updateTable(nameViz, senderIP, nameNode, 0, int(time.time()), 0)
                if len(path) != 0:
                    nameSend = path.pop()
                    path.append(self.name)
                    self.route_reply(stamp, nameSend, path, nameNode, timeout)
                print(self.table)






    def run_removedead(self):
        while True:
            time.sleep(10)
            #for ip in self.hello:
                #if((int(time.time())-self.hello[ip])>10):
                    #del self.hello[ip]
                    #print('IP: ', ip, 'timestamp: ', self.hello[ip])
                #remove se datetime.datetime.now() - self.hello[ip] > 2*self.hello_int


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
        print('Exiting')

#Por a enviar o array hello, com os vizinhos diretos, enviar um timestamp no inicio do pacote hello
#Guardar o rtt na tabela de reencaminhamento, timestamp, e ips
