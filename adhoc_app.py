import time, struct, socket, sys, json
import _thread, math, random, subprocess
"""
Dicionario hello guarda a lista dos IPs dos vizinhos e o timestamp do ultimo refresh
Cada no recebera hellos de seus vizinhos, que por sua vez tera a lista dos vizinhos dos vizinhos.
A tabela tera portanto dois niveis.
Caso seja necessario enviar algo para alguem fora da lista,  no tera que enviar um route_request para os vizinhos e receber um route_reply com a devida rota.
Uma funcao tem que varrer a estrutura hello e remover os IPs mais antigos que dead_interval
A funcao que recebe os hellos via UDP adiciona os novos IPs na estrutura hello
"""

class AdhocRoute:
    #Iniciar a classe Hello
    def __init__(self, probing=10, group='ff02::1', deadint=60, port=9999):
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
        self.news = []
        self.on = True
    """
        Corre as threads que enviam mensagens de protocolo hello,
        que escutam por mensagens UDP,, e que escutam por input do utilizador,
        que removem os vizinhos que ja nao respondem
    """
    def run_probe(self):
        try:
            _thread.start_new_thread(self.udp_listener, ())
            _thread.start_new_thread(self.tcp_listener, ())
            _thread.start_new_thread(self.recv_input, ())
            self.run_sender()
        except:
            print("Error in thread!")

    """
        Pacote enviado para informar o caminho até ao nodo pretendido, verificando inicialmente se o nodo que
        originou o ROUTE REQUEST já não está à espera da resposta, devido a timeout.
        Caso ainda esteja, é verificado na sua tabela de reencaminhamento, o ip do nodo para o qual irá enviar
        o reply (nodo que está na última posição no array que contêm o caminho), de modo a chegar ao nodo origem.
        É enviado o nodo com o tipo 2 (tipo Route Reply, explicado na função run_listener)
    """
    def route_reply(self, stamp, nameNode, path, timeout):
        if((int(time.time())-stamp <= timeout)):
            s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            nameViz = path.pop()
            ip = self.table[nameViz][1]
            bytes_to_send = json.dumps([2, stamp, self.name, nameNode, path, timeout]).encode()
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

                self.route_reply(stamp, nameNode, path, timeout)



    """
        Thread que irá receber os pedidos do utilizador, podendo este pedir por um ROUTE REQUEST, tendo que fornecer
        o nome do nodo que desejará conhecer, o número máximo de saltos, e o tempo que estará à espera de resposta até dar timeout.
        Ex: ROUTE REQUEST <nome_nodo> <ttl> <timeout>
    """
    def recv_input(self):
        try:
            while self.on:
                inp = input(self.name+ "#>")
                command = inp.split()
                if len(command) > 0:
                    if len(command)>1 and command[0] == 'route' and command[1] == 'request':
                        if(len(command) < 5):
                            print("route request <node_name> <ttl> <timeout>")
                        elif(command[2] not in self.table):
                            self.route_request(int(time.time()), command[2], int(command[3]), [], int(command[4]))
                        else:
                            print(self.table)
                    elif command[0] == 'help':
                        self.printhelp()
                    elif len(command)==1 and command[0] == 'route':
                        print("Current routing table:")
                        print("Node Name\t| Next hop\t| IPV6 address\t\t| Timestamp\t| RTT")
                        for name in self.table:
                            data = self.table[name]
                            print(name+ "\t\t| " + data[0] + "\t\t| " + data[1] + "\t| " + str(data[2]) + "\t| " + str(data[3]))
                    elif len(command)==1 and command[0] == 'hello':
                        print("Current hello table:")
                        print(self.hello)
                    elif len(command)==1 and command[0] == 'clear':
                        print("\033c")
                    elif command[0] == 'set':
                        self.news.append(" ".join(command[1:]))
                    elif command[0] == 'news':
                        print(self.news)
                    elif command[0] == 'quit':
                        self.on = False
                        print("Shutting Down")
                    else:
                        print("Invalid command!")


        except EOFError:
            self.on = False
            print("Shutting Down")

    """
        Remove todos os vizinhos antigos dos registos de reencaminhamento, retirando todos os registos
        que não sejam atualizados entre dois protocolos hello. Remove também todas as conexões que passem por
        esse mesmo vizinho.
    """
    def remove_dead(self):
        arrayDead = []
        for name in self.table:
            if((int(time.time())-self.table[name][2])>(2*self.hello_int) or (name in arrayDead)):
                arrayDead.append(name)
        for name in arrayDead:
            del self.table[name]

    """
        Thread que envia a mensagem hello, enviando o seu dicionario, contendo
        os seus vizinhos diretos, enviando para o grupo IPv6 (self.ipv6_group)
        atraves de UDP (socket.SOCK_DGRAM), com apenas TTL=1 (ttl_bin)
        Caso o tamanho do pacote UDP seja maior 65500, divide-se o número de itens no dicionário
        até meio, até que o pacote seja menor que 65500.
        Antes de criar a mensagem hello, remove todos os registos antigos da tabela de reencaminhamento.
    """
    def run_sender(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        ttl_bin = struct.pack('@i', 1) #ttl=1
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        limit = 65500
        n = 0
        while self.on:
            self.remove_dead()
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
            if(data[0] == senderName or data[3] >= (rtt+vizRTT)):
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
        2. Pacote Route Reply- Pacote enviado por quem conhece o nodo de um pacote Route Request. É retirado o ip de quem enviou
        o reply, juntamente com o nodo que o route request deseja conhecer, o timeStamp de quando o Route Request foi enviado, para verificar
        se já deu timeout, o tempo máximo até dar timeout, e é retirado também o nome do nodo que enviou o route reply,
        obtido através do pdu do route request, de modo a atualizar a tabela de reencaminhamento, adicionando o nodo que o route request
        deseja conhecer, o nodo vizinho que deverá aceder de modo a aceder a esse mesmo nodo, e o seu ip.
        3. Pacote News applicatios - O processamento ocorre de duas formas:
            Caso o pacote tenha chegado ao utilizador final, é verificado se o cabeçalho TCP começa com GET ou NEWS. Caso começe com GET, é
            modificado o cabeçalho, colocando como NEWS, colocado o utilizador atual como utilizador de começo do pacote route reply, e colocando o nome
            do utilizador que enviou o route request, como destino do pacote. As noticias do utilizador atual, são concatenadas no final do pacote. Caso o
            cabeçalho TCP seja NEWS, é enviado o pacote TCP para o cliente.
            Caso o pacote não tenha chegado ao utilizador final, é verificado se na tabela de encaminhamento existe um caminho até ao utilizador final.
            Caso exista, é reenviado o pacote para esse utilizador. Caso não exista, é efetuado um route request para esse utilizador, e criada uma thread
            que espera pelo tempo de timeout, verificando se encontrou o nodo ou não.
    """
    def udp_listener(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', self.port))
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
        mreq = group_bin + struct.pack('@I', 0)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        # Loop
        while self.on:
            data, sender = s.recvfrom(65535)
            #while data[-1:] == '\0': data = data[:-1] # Strip trailing \0's
            array = json.loads(data.decode())
            tipo = array[0]
            senderIP = (str(sender).rsplit('%', 1)[0])[2:] #Retirar apenas o IPv6

            if tipo == 0:
                timeStamp = array[1]
                rtt = int(time.time())-timeStamp
                senderName = array[2]
                vizinhos = array[3]

                if senderName != self.name:
                    self.updateTable(senderName, senderIP, senderName, 0, timeStamp, rtt)
                    for vizName in vizinhos:
                        if vizName != self.name:
                            try:
                                destino=self.table[vizName]
                                if vizName!=destino[0]:
                                    self.updateTable(senderName, senderIP, vizName, vizinhos.get(vizName), timeStamp, rtt)

                            except:
                                self.updateTable(senderName, senderIP, vizName, vizinhos.get(vizName), timeStamp, rtt)
            if tipo == 1:
                path = array[4]
                if self.name not in path:
                    timeStamp = array[1]
                    name = array[2]
                    ttl = array[3]
                    timeout = array[5]
                    self.route_request(timeStamp, name, ttl, path, timeout)
            if tipo == 2:
                stamp = array[1]
                nameNode = array[2]
                nameDest = array[3]
                path = array[4]
                timeout = array[5]
                if len(path) != 0 and (int(time.time()) - stamp) < timeout:
                    self.updateTable(nameNode, senderIP, nameDest, 0, int(time.time()), 0)
                    self.route_reply(stamp, nameDest, path, timeout)
                else:
                    if (int(time.time()) - stamp) < timeout:
                        #Descartar todos os route replys após o primeiro a chegar
                        if nameDest in self.table:
                            rtt = int(time.time()) - stamp
                            if (int(time.time()) - self.table[nameNode][2]) > timeout:
                                self.updateTable(nameNode, senderIP, nameDest, 0, int(time.time()), 0)
                        else:
                            self.updateTable(nameNode, senderIP, nameDest, 0, int(time.time()), 0)
            if tipo == 3:
                header = array[1]
                sender_name = array[2]
                msg_dest = array[3]
                request = array[4]
                if header == "MSG": # got a message
                    if msg_dest == self.name: #if message is for us, open
                        if request[0] == "GET":
                            udp_router = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                            udp_router.connect(('::1', self.port))
                            data = ["NEWS",msg_dest,sender_name,self.news]
                            bytes_to_send = json.dumps([3, "MSG", msg_dest, sender_name, data]).encode()
                            udp_router.send(bytes_to_send)
                            udp_router.close()
                        elif request[0] == "NEWS":
                            tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                            tcp_sendnews.connect(('::1', self.port))
                            bytes_to_send = json.dumps(request).encode()
                            tcp_sendnews.send(bytes_to_send)
                            tcp_sendnews.close()

                        else:
                            print("Got a malformed message. Discarding.")
                    else:
                        if(msg_dest in self.table):
                            fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                            table=self.table[msg_dest]
                            fwd_s.sendto(data, (table[1], self.port)) #Enviar ao nexthop verificado na tabela de roteamento
                        else:
                            self.route_request(int(time.time()), msg_dest, 10, [], 10)
                            _thread.start_new_thread(self.get_news, (data, msg_dest, 10))

                else:
                    print("Got a malformed message. Discarding.")

    """
        Usado apenas quando o utilizador que necessita buscar as noticias não está
        na tabela de encaminhamento. Inicialmente é efetuado um compasso de espera
        do tempo do timeout do route request (que foi efetuado em udp_listener), de modo
        a que consiga procurar pelo nodo.
        Caso o encontre, é enviado para si de novo o pacote com os mesmos dados,
        de modo a que o parse em udp_listener possa o processar de novo.
        Caso não encontre, é enviado para o cliente 0 bytes, de modo a que possa informar
        que o nodo não foi encontrado.
    """
    def get_news(self, data, msg_dest, timeout=0):
            time.sleep(timeout/100)
            if(msg_dest in self.table):
                fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                fwd_s.sendto(data, (self.table[msg_dest][1], self.port))
            else:
                tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                tcp_sendnews.connect(('::1', self.port))
                tcp_sendnews.send(json.dumps('').encode())
                tcp_sendnews.close()



    def printhelp(self):
        print()
        print("AER TP1 - Adhoc Route 0.1")
        print()
        print("Following commands are available:")
        print("route - prints the current routing table")
        print("route request [computer_name] - request the route to computer")
        print("hello - prints the current hello table")
        print("clear - clears the screen")
        print("quit - Leave the program")
        print()



    def tcp_listener(self):
        tcp_r = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        udp_router = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        try:
            tcp_r.bind(('', self.port))
        except:
            print ('Problem binding TCP listener. You killed an open tcp socket, wait until you restart again.')
            sys.exit()
        tcp_r.listen(1)

        while self.on:
            conn, sender = tcp_r.accept() #locks until we get something
            data = json.loads(conn.recv(1024).decode())
            if(len(data) == 0):
                client_conn.send(json.dumps(data).encode())
                client_conn.close()
            else:
                Verb= data[0] #GET OR NEWS
                Object= data[1] #DESTINATION
                if Verb == "GET":
                    #Gets the request and connects to the UDP server (the router) in localhost machine
                    client_conn = conn
                    udp_router.connect(('::1', self.port))
                    bytes_to_send = json.dumps([3, "MSG", self.name, Object, [Verb, self.name, Object]]).encode() #ADD MSG header
                    udp_router.send(bytes_to_send)
                elif Verb == "NEWS":
                    news=data[3]
                    client_conn.send(json.dumps(data).encode())
                    client_conn.close()


if __name__ == '__main__':
    try:
        prob = AdhocRoute()
        prob.run_probe()
    except KeyboardInterrupt:
        print('Exiting')

#Por a enviar o array hello, com os vizinhos diretos, enviar um timestamp no inicio do pacote hello
#Guardar o rtt na tabela de reencaminhamento, timestamp, e ips
