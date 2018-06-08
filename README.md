# Adhoc News Protocol
## AER-TP1


**adhoc_app.py**

This software runs as TCP/UDP server on port 9999 aiming to be a simulation of a adhoc routing protocol
To start the software run: **pyhton3 adhoc_app.py [nodename]**

When run it opens a UDP/9999 server that simulates the network layer of a network stack. It also opens a TCP/9999 server that simalates the application layer.

The application simulation expects a packet starting with GET in the TCP port. When it finds it, adds a MSG header and forward the packet to the UDP port.

The network stack (UDP part) tries to find the destination (news server) and when it finds, it get the news (now only a variable in memory), creates a NEWS packet and sends to the TCP layer again. The TCP layer adds the MSG header and forwards to the UDP layer.

Same procedure is followed until it reaches it final destination where the news are delivered to the client who request them in the first place.


To run the client: **python3 news_agent.py client**

Inside the client just type: get [nodename]

<br>

Colaborators:
- [Bruno Ferreira](https://github.com/brunobcfum)
- [João Miguel](https://github.com/CaptainJRoy)
- [Paulo Guedes](https://github.com/Oluap18)
