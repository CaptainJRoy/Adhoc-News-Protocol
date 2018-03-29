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
        Corre as threads que enviam mensagens de protocolo hello,
        que escutam por mensagens UDP,, e que escutam por input do utilizador,
        que removem os vizinhos que ja nao respondem
    """
    def run_probe(self):
        try:
            addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
            sender = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
            listener = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
            _thread.start_new_thread(self.run_sender, (sender,addrinfo,))
            _thread.start_new_thread(self.run_listener, (listener,addrinfo,))
            _thread.start_new_thread(self.recv_input, ())
            self.run_removedead()
        except:
            print("Error in thread!")





    """
        Pacote enviado para informar o caminho até ao nodo pretendido, verificando inicialmente se o nodo que
        originou o ROUTE REQUEST já não está à espera da resposta, devido a timeout.
        Caso ainda esteja, é verificado na sua tabela de reencaminhamento, o ip do nodo para o qual irá enviar
        o reply (nodo que está na última posição no array que contêm o caminho), de modo a chegar ao nodo origem.
        É enviado o nodo com o tipo 2 (tipo Route Reply, explicado na função run_listener)
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



    """
        Pacote enviado para conhecer um caminho até um nodo que não esteja na tabela de reencaminhamento.
        É verificado inicialmente se o nodo que originou o ROUTE REQUEST já não está à espera da resposta, devido a timeout.
        Caso ainda esteja à espera da resposta, é adicionado o seu nome ao caminho desde o nodo de origem, até ao nodo que deseja saber a rota.
        É enviado um pacote contendo o tipo 1 (tipo ROUTE REQUEST, explicado na função run_listener), juntamente com o timeStamp de quando originou
        o Route Request, o nome do nodo que deseja saber a rota, é decrementado o número de saltos que poderá dar, é enviado também o
        caminho já percorrido, e o tempo de timeout.
        Caso este conheça o nodo em questão, é retirado o último nodo do caminho, de modo a enviar para esse mesmo nodo retirado, um REQUEST REPLY
        informando que este conheçe o nodo. É acrescentado o seu nome, para atualizar a tabela de reencaminhamento do nodo para o qual enviará o reply.
    """
    def route_request(self, stamp, nameNode, ttl, path, timeout):
        if((int(time.time())-stamp) <= timeout):
            if nameNode not in self.table:
                if(path == None):
                    path = [self.name]
                else:
                    path.append(self.name)
                addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
                s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
                ttl_bin = struct.pack('@i', ttl) #ttl=1
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
                bytes_to_send = json.dumps([1, stamp, nameNode, ttl-1, path, timeout]).encode()
                s.sendto(bytes_to_send, (addrinfo[4][0], self.port)) #Enviar os vizinhos diretos
            else:
                nameViz = path.pop()
                path.append(self.name)
                self.route_reply(stamp ,nameViz, path, nameNode, timeout)



    """
        Thread que irá receber os pedidos do utilizador, podendo este pedir por um ROUTE REQUEST, tendo que fornecer
        o nome do nodo que desejará conhecer, o número máximo de saltos, e o tempo que estará à espera de resposta até dar timeout.
        Ex: ROUTE REQUEST <nome_nodo> <ttl> <timeout>
    """
    def recv_input(self):
        try:
            while True:
                inp = input(self.name+ "#>")
                command = inp.split()
                if len(command) > 0:
                    if command[0] == 'route' and command[1] == 'request':
                        if(command[2] not in self.table):
                            self.route_request(int(time.time()), command[2], int(command[3]), [], int(command[4]))
                        else:
                            print(self.table)
                    elif command[0] == 'help':
                        self.printhelp()
                    elif len(command)==1 and command[0] == 'route':
                        print("Current routing table:")
                        print("Node Name    | IPV6 address          | Next hop              | Next hop RTT    | Timestamp     | RTT")
                        print(self.table)
                    elif len(command)==1 and command[0] == 'hello':
                        print("Current hello table:")
                        print(self.hello)
                    else:
                        print("Invalid command!")
                    


        except EOFError:
            pass

    """
        Thread que envia a mensagem hello, enviando o seu dicionario, contendo
        os seus vizinhos diretos, enviando para o grupo IPv6 (self.ipv6_group)
        atraves de UDP (socket.SOCK_DGRAM), com apenas TTL=1 (ttl_bin)
        Caso o tamanho do pacote UDP seja maior 65500, divide-se o número de itens no dicionário
        até meio, até que o pacote seja menor que 65500
    """
    def run_sender(self, s, addrinfo):
        ttl_bin = struct.pack('@i', 1) #ttl=1
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        limit = 65500
        n = 0
        while True:
            self.hello = {}
            for nameViz in self.table:
                if nameViz == self.table[nameViz][0]:
                    if(n<=limit):
                        self.hello[nameViz] = self.table[nameViz][3]
                    else:
                        bytes_to_send = json.dumps([0, int(time.time()), self.name, self.hello]).encode()
                        self.hello = {}
                        n = 0
            bytes_to_send = json.dumps([0, int(time.time()), self.name, self.hello]).encode()
            if(len((bytes_to_send, (addrinfo[4][0], self.port)))<= 65500):
                s.sendto(bytes_to_send, (addrinfo[4][0], self.port)) #Enviar os vizinhos diretos
                time_add = random.randrange(-math.floor(self.hello_int * 0.1),
                                         math.floor(self.hello_int * 0.1))
                time.sleep(self.hello_int + time_add)  #tempo de probe entre hello_int +- variaçao tempo
                limit = 65500
                n = 0
            else:
                limit = limit/2
                n=0

    """
        Atualiza a self.table com as informações do vizinho em questão, atualizando o valor na tabela caso:
        1. O nome do vizinho que enviou for igual, atualizando as informações, caso a rede tenha mudado
        2. O rtt for menor ou igual
        3. Não exista registo na tabela desse vizinho
        @senderName - Nome do vizinho que enviou o hello
        @senderIP - IP do vizinho que envou o hello
        @vizName - Nome de um dos vizinhos contidos no hello
        @vizRTT - Rtt da ligação do nodo vizinho que enviou o pacote hello, com o vizinho a uma distância de 2 saltos deste
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


    """
        Thread que está à escuta por pacotes UDP. Assim que os recebe, realiza o parse dependendo do tipo do pacote:
        0. Pacote hello- Contêm o timeStamp de quando foi enviado o pacote, de modo a calcular o rtt da conexão, contêm
        o nome de quem enviou, e os seus vizinhos diretos. É retirado o ip de quem enviou o pacote, e caso o pacote não tenha
        sido enviado por ele mesmo, será atualizada a tabela de routing, inicialmente com os dados de quem enviou o pacote, sendo
        de seguida atualizado com os vizinhos diretos de quem enviou o pacote hello.
        1. Pacote Route Request- Pacote enviado por quem deseja conhecer alguém que não esteja na sua tabela de routing. É recebido
        o caminho que o pacote já percorreu, o timeStamp de quando o Route Request foi enviado, de modo a verificar se já deu timeout,
        o nome do nodo para o qual deseja saber a rota, o número de saltos máximos que o pacote poderá dar, e o tempo limite que o nodo
        de qual originou o request estará à espera de resposta.
        2. Pacote Request Reply- Pacote enviado por quem conhece o nodo de um pacote Route Request. É retirado o ip de quem enviou
        o reply, juntamente com o nodo que o route request deseja conhecer, o timeStamp de quando o Route Request foi enviado, para verificar
        se já deu timeout, o tempo máximo até dar timeout, e é retirado do caminho, obtido através do route request, o último nodo, de modo a atualizar
        a tabela de reencaminhamento, adicionando o nodo que o route request deseja conhecer, o nodo vizinho que deverá aceder de modo a aceder a esse mesmo
        nodo, e o seu ip.
    """
    def run_listener(self, s, addrinfo):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', self.port))
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
        mreq = group_bin + struct.pack('@I', 0)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        # Loop, printing any data we receive
        while True:
            data, sender = s.recvfrom(65535)
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
                    print(self.table)
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
                else:
                    print(self.table)


    def run_removedead(self):
        while True:
            time.sleep(10)
            #for ip in self.hello:
                #if((int(time.time())-self.hello[ip])>10):
                    #del self.hello[ip]
                    #print('IP: ', ip, 'timestamp: ', self.hello[ip])
                #remove se datetime.datetime.now() - self.hello[ip] > 2*self.hello_int
    



    def printhelp(self):
        print()
        print("AER TP1 - Adhoc Route 0.1")
        print()
        print("Following commands are available:")
        print("route - prints the current routing table")
        print("route request [computer_name] - request the route to computer")
        print("hello - prints the current hello table")
        print("ping [computer_name] - sends a small package to teste the routing table")
        print()


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
