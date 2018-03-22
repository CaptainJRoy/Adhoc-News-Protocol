import time, struct, socket, sys, json
import _thread, math, random, datetime
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
            @self.hello - dicionario de vizinhos
            @self.port - porta para comunicar o protocolo hello
        """
        self.hello_int = probing+random.randint(0, probing*0.1)
        self.dead_interval  = deadint
        self.ipv6_group = group
        self.hello = {}
        self.tabela = {}
        self.port = port

    """
        Corre as threads que enviam mensagens hello, contendo o seu dicionario,
        que escutam por mensagens hello, que contem o dicionario dos vizinhos,
        que removem os vizinhos que ja nao respondem
    """
    def run_probe(self):
        try:
            _thread.start_new_thread(self.run_listener, ())
            _thread.start_new_thread(self.run_sender, ())
            self.run_removedead()
        except:
            print("Error in thread!")

    """
        Thread que envia a mensagem hello, enviando o seu dicionario, contendo
        os seus vizinhos diretos, enviando para o grupo IPv6 (self.ipv6_group)
        atraves de UDP (socket.SOCK_DGRAM), com apenas TTL=1 (ttl_bin)
    """
    def run_sender(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        ttl_bin = struct.pack('@i', 1) #ttl=1
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        while True:
            #s.sendto((time.time().encode(),json.dumps(self.hello) + '\0').encode()), (addrinfo[4][0], self.port)) #Enviar os vizinhos diretos
            #bytes_to_send = str(int(time.time())).encode()+";".encode()+(str(self.hello) + '\0').encode()
            bytes_to_send = (str(int(time.time()))+", "+(str(self.hello) + '\0')).encode()
            print(bytes_to_send.decode())
            s.sendto(bytes_to_send, (addrinfo[4][0], self.port))
            time_add = random.randrange(-math.floor(self.hello_int * 0.1),
                                         math.floor(self.hello_int * 0.1))
            time.sleep(self.hello_int + time_add)  #tempo de probe entre hello_int +- variaçao tempo


    def run_listener(self):
        global ROUTING_TABLE
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
            #while data[-1:] == '\0': data = data[:-1] # Strip trailing \0's
            timerec, array = data.decode().split(",")
            ipViz = (str(sender).rsplit('%', 1)[0])[2:] #Retirar apenas o IPv6
            print ("Recebido de "+ ipViz + ' -> ' + array + " com roundtrip de: " + str(int(time.time())-int(timerec)))
            self.hello[ipViz] = int(time.time())
            #tabRecebida = json.loads(data.decode())
            #value = []
            #value[0]=ipViz
            #value[1]=datetime.datetime.now();
            #self.hello[ipViz] = time.time(); #UNIX TIME!


    def run_removedead(self):
        while True:
            for ip in self.hello:
                if((self.hello[ip]-int(time.time()))>1000):

                    print('IP: ', ip, 'timestamp: ', self.hello[ip])
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
