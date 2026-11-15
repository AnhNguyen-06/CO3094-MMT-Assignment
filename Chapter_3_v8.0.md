# Chapter 3 - Transport Layer

**Nguồn:** `Chapter_3_v8.0.pdf` (Computer Networking: A Top-Down Approach, 8th edition).

**Ghi chú chuyển đổi:** Nội dung văn bản được trích xuất theo thứ tự slide. Các sơ đồ/đồ họa không thể biểu diễn bằng văn bản được đính kèm ảnh xem trước ở những slide có ít văn bản trích xuất.

## Slide 1 - Chapter 3 Transport Layer

Computer Networking: A  
Top-Down Approach  
8th edition  
Jim Kurose, Keith Ross  
Pearson, 2020  

![Slide 1 preview](Chapter_3_v8.0_assets/slide-001.png)

## Slide 2 - Transport layer: overview

Our goal:  

- understand principles

behind transport layer  
services:  

- multiplexing,

demultiplexing  
- reliable data transfer
- flow control
- congestion control

- learn about Internet transport

layer protocols:  
- UDP: connectionless transport
- TCP: connection-oriented reliable

transport  

- TCP congestion control

## Slide 3 - Transport layer: roadmap

- Transport-layer services
- Multiplexing and demultiplexing
- Connectionless transport: UDP
- Principles of reliable data transfer
- Connection-oriented transport: TCP
- Principles of congestion control
- TCP congestion control
- Evolution of transport-layer functionality

## Slide 4 - Transport services and protocols

- provide logical communication

between application processes  
running on different hosts  

- transport protocols actions in end

systems:  

- sender: breaks application messages

into segments, passes to network layer  
- receiver: reassembles segments into

messages, passes to application layer  

- two transport protocols available to

Internet applications  

- TCP, UDP

application  

transport  

network  
data link  

mobile network  

physical  

national or global ISP  

local or  
regional ISP  

home network  

content  
provider  
network  

datacenter  
network  

application  

transport  

network  
data link  

physical  

enterprise  

network  

## Slide 5 - Transport vs. network layer services and protocols

household analogy:  
12 kids in Ann’s house sending  

letters to 12 kids in Bill’s  
house:  
- hosts = houses
- processes = kids
- app messages = letters in

envelopes  
- transport protocol = Ann and Bill

who demux to in-house siblings  
- network-layer protocol = postal

service  

## Slide 6 - Transport vs. network layer services and protocols

- network layer: logical

communication between  
hosts  
- transport layer: logical

communication between  
processes  

- relies on, enhances, network

layer services  

household analogy:  
12 kids in Ann’s house sending  

letters to 12 kids in Bill’s  
house:  
- hosts = houses
- processes = kids
- app messages = letters in

envelopes  
- transport protocol = Ann and Bill

who demux to in-house siblings  
- network-layer protocol = postal

service  

## Slide 7 - Transport Layer Actions

Sender:  

app. msg  
- is passed an application-

application  

layer message  
- determines segment

transport  
ThTh  
app. msg  

header fields values  
- creates segment
- passes segment to IP

network (IP)  

link  

physical  

application  

transport  

network (IP)  

link  

physical  

## Slide 8 - Transport Layer Actions

Receiver:  

- checks header values
- receives segment from IP

application  

transport  

app. msg  
- extracts application-layer

message  

network (IP)  

- demultiplexes message up

to application via socket  

link  

physical  

Th  
app. msg  

application  

transport  

network (IP)  

link  

physical  

## Slide 9 - Two principal Internet transport protocols

physical  
- TCP: Transmission Control Protocol

- reliable, in-order delivery
- congestion control
- flow control
- connection setup
- UDP: User Datagram Protocol

- unreliable, unordered delivery
- no-frills extension of “best-effort” IP
- services not available:

- delay guarantees
- bandwidth guarantees

application  

transport  

network  
data link  

mobile network  

national or global ISP  

local or  
regional ISP  

home network  

content  
provider  
network  

datacenter  
network  

application  

transport  

network  
data link  

physical  

enterprise  

network  

## Slide 10 - Chapter 3: roadmap

- Transport-layer services
- Multiplexing and demultiplexing
- Connectionless transport: UDP
- Principles of reliable data transfer
- Connection-oriented transport: TCP
- Principles of congestion control
- TCP congestion control
- Evolution of transport-layer

functionality  

## Slide 11 - Slide 11

HTTP server  

client  

application  

HTTP msg  

transport  

network  
transport  

transport  

link  

network  

physical  

link  

physical  

application  

network  

link  

physical  

![Slide 11 preview](Chapter_3_v8.0_assets/slide-011.png)

## Slide 12 - Slide 12

HTTP server  

client  

application  

HTTP msg  

transport  

HTTP msg  
Ht  

network  
transport  

transport  

link  

network  

physical  

link  

physical  

application  

network  

link  

physical  

![Slide 12 preview](Chapter_3_v8.0_assets/slide-012.png)

## Slide 13 - Slide 13

HTTP server  

client  

application  

HTTP msg  

transport  

HTTP msg  
Ht  

network  
transport  

HTTP msg  
Ht  
Hn  

transport  

link  

network  

physical  

link  

physical  

application  

network  

link  

physical  

![Slide 13 preview](Chapter_3_v8.0_assets/slide-013.png)

## Slide 14 - Slide 14

HTTP server  

client  

application  

transport  

network  
transport  

transport  

link  

network  

physical  

link  

physical  

HTTP msg  
Ht  
Hn  

application  

network  

link  

physical  

![Slide 14 preview](Chapter_3_v8.0_assets/slide-014.png)

## Slide 15 - Slide 15

HTTP server  

client1  

application  

P-client1  
P-client2  

transport  

network  
transport  

transport  

link  

network  

physical  

link  

physical  

client2  

application  

network  

link  

physical  

![Slide 15 preview](Chapter_3_v8.0_assets/slide-015.png)

## Slide 16 - Multiplexing/demultiplexing

multiplexing at sender:  

demultiplexing at receiver:  

handle data from multiple  
sockets, add transport header  
(later used for demultiplexing)  

use header info to deliver  
received segments to correct  
socket  

application  

P2  
P1  

application  

application  

socket  

P4  

P3  

transport  

process  

network  

transport  

transport  

link  

network  

network  

physical  

link  

link  

physical  

physical  

## Slide 17 - How demultiplexing works

- host receives IP datagrams

- each datagram has source IP

address, destination IP address  
- each datagram carries one

transport-layer segment  
- each segment has source,

destination port number  
- host uses IP addresses & port

numbers to direct segment to  
appropriate socket  

32 bits  

source port #  
dest port #  

other header fields  

application  

data  
(payload)  

TCP/UDP segment format  

## Slide 18 - Connectionless demultiplexing

Recall:  
- when creating socket, host

must specify host-local port #:  

DatagramSocket mySocket1  

= new DatagramSocket(12534);  

socket with that port #  
- when creating datagram to

send into UDP socket, host  
must specify  

- destination IP address
- destination port #

when receiving, host receives  
UDP segment:  

- checks destination port # in

segment  
- directs UDP segment to

IP/UDP datagrams with same dest.  

port #, but different source IP  
addresses and/or source port  
numbers will be directed to same  

socket at receiving host  

## Slide 19 - Connectionless demultiplexing: an example

DatagramSocket  

serverSocket = new  
DatagramSocket  
(6428);  

new DatagramSocket (5775);  
DatagramSocket mySocket2 =  

DatagramSocket mySocket1 =  

new DatagramSocket  

same  
socket  

application  

(9157);  

application  

application  

P1  

P3  

P4  

transport  

transport  

transport  

network  

network  

network  

link  

link  

link  

physical  

physical  

physical  

source port: 6428  
dest port: 9157  

source port: ?  

dest port: ?  

source port: ?  
dest port: ?  

source port: 9157  

dest port: 6428  

## Slide 20 - Connection-oriented demultiplexing

- TCP socket identified by

4-tuple:  

- source IP address
- source port number
- dest. IP address
- dest. port number

- demux: receiver uses all

four values (4-tuple) to  
direct segment to  
appropriate socket  

- server may support many

simultaneous TCP sockets:  
- each socket identified by its

own 4-tuple  
- each socket associated with

a different connecting client  

## Slide 21 - Connection-oriented demultiplexing: example

different  

socket  

application  

application  

application  

P4  

P6  
P5  

P3  

P1  

P2  

transport  

transport  

transport  

network  

network  

network  

link  

link  

link  

physical  

physical  

physical  

server: IP  
address B  

host: IP  
address C  

source IP,port: B,80  
dest IP,port: A,9157  
source IP,port: C,5775  
dest IP,port: B,80  

host: IP  
address A  

source IP,port: A,9157  

dest IP, port: B,80  

source IP,port: C,9157  
dest IP,port: B,80  

Three segments, all destined to IP address: B,  

dest. port: 80 are demultiplexed to different sockets  

## Slide 22 - Summary

- Multiplexing, demultiplexing: based on segment, datagram

header field values  
- UDP: demultiplexing using destination port number (only)
- TCP: demultiplexing using 4-tuple: source and destination IP

addresses, and port numbers  
- Multiplexing/demultiplexing happen at all layers

## Slide 23 - Chapter 3: roadmap

- Transport-layer services
- Multiplexing and demultiplexing
- Connectionless transport: UDP
- Principles of reliable data transfer
- Connection-oriented transport: TCP
- Principles of congestion control
- TCP congestion control
- Evolution of transport-layer

functionality  

## Slide 24 - UDP: User Datagram Protocol

- “no frills,” “bare bones”

Internet transport protocol  
- “best effort” service, UDP

segments may be:  

- lost
- delivered out-of-order to app

- connectionless:

- no handshaking between UDP

sender, receiver  
- each UDP segment handled

independently of others  

Why is there a UDP?  

- no connection

establishment (which can  
add RTT delay)  
- simple: no connection state

at sender, receiver  
- overhead: small header size
- no congestion control

- UDP can blast away as fast as

desired!  
- can function in the face of

congestion  

## Slide 25 - UDP: User Datagram Protocol

- UDP used for:

- streaming multimedia apps (loss tolerant, rate sensitive)
- DNS
- SNMP
- HTTP/3
- if reliable transfer needed over UDP (e.g., HTTP/3):

- add needed reliability at application layer
- add congestion control at application layer

## Slide 26 - UDP: User Datagram Protocol [RFC 768]

_Không có văn bản có thể trích xuất từ slide này._

![Slide 26 preview](Chapter_3_v8.0_assets/slide-026.png)

## Slide 27 - UDP: Transport Layer Actions

SNMP server  
SNMP client  

application  

transport  

(UDP)  

network (IP)  

link  

physical  

application  

transport  

(UDP)  

network (IP)  

link  

physical  

![Slide 27 preview](Chapter_3_v8.0_assets/slide-027.png)

## Slide 28 - UDP: Transport Layer Actions

SNMP server  
SNMP client  

UDP sender actions:  

SNMP msg  
- is passed an application-

application  

layer message  
- determines UDP segment

transport  

(UDP)  

header fields values  
- creates UDP segment
- passes segment to IP

network (IP)  

link  

physical  

application  

transport  

UDPh  
UDPh SNMP msg  

(UDP)  

network (IP)  

link  

physical  

## Slide 29 - UDP: Transport Layer Actions

SNMP server  
SNMP client  

UDP receiver actions:  

- receives segment from IP

application  

- checks UDP checksum

transport  

header value  

SNMP msg  

(UDP)  

- extracts application-layer

message  

network (IP)  

UDPh SNMP msg  
- demultiplexes message up

link  

to application via socket  

physical  

application  

transport  

(UDP)  

network (IP)  

link  

physical  

## Slide 30 - UDP segment header

32 bits  

source port #  
dest port #  

length  
checksum  

application  

data  
(payload)  

UDP segment format  

length, in bytes of  

UDP segment,  
including header  

data to/from  
application layer  

![Slide 30 preview](Chapter_3_v8.0_assets/slide-030.png)

## Slide 31 - UDP checksum

Goal: detect errors (i.e., flipped bits) in transmitted segment  

1st number  
2nd number  
sum  

Transmitted: 5  
6 11  

Received: 4  
6 11  

sender-computed  
checksum (as received)  

receiver-computed  

=  

checksum  

## Slide 32 - Internet checksum

Goal: detect errors (i.e., flipped bits) in transmitted segment  

sender:  

- treat contents of UDP

segment (including UDP header  
fields and IP addresses) as  
sequence of 16-bit integers  
- checksum: addition (one’s

complement sum) of segment  
content  
- checksum value put into

UDP checksum field  

receiver:  

- compute checksum of received

segment  
- check if computed checksum equals

checksum field value:  

- not equal - error detected
- equal - no error detected. But maybe

errors, nonetheless? More later ….  

## Slide 33 - Internet checksum: an example

example: add two 16-bit integers  

1 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0  
1 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1  

1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1  
wraparound  

1 0 1 1 1 0 1 1 1 0 1 1 1 1 0 0  

sum  

0 1 0 0 0 1 0 0 0 1 0 0 0 0 1 1  

checksum  

Note: when adding numbers, a carryout from the most significant bit needs to be  
added to the result  

* Check out the online interactive exercises for more examples: http://gaia.cs.umass.edu/kurose_ross/interactive/  

## Slide 34 - Internet checksum: weak protection!

example: add two 16-bit integers  

1 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0  
1 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1  

1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1  
wraparound  

1 0 1 1 1 0 1 1 1 0 1 1 1 1 0 0  
0 1 0 0 0 1 0 0 0 1 0 0 0 0 1 1  

sum  

checksum  

0 1  

1 0  

Even though  
numbers have  
changed (bit  
flips), no change  
in checksum!  

## Slide 35 - Summary: UDP

- “no frills” protocol:

- segments may be lost, delivered out of order
- best effort service: “send and hope for the best”
- UDP has its plusses:

- no setup/handshaking needed (no RTT incurred)
- can function when network service is compromised
- helps with reliability (checksum)
- build additional functionality on top of UDP in application layer

(e.g., HTTP/3)  

## Slide 36 - Chapter 3: roadmap

- Transport-layer services
- Multiplexing and demultiplexing
- Connectionless transport: UDP
- Principles of reliable data transfer
- Connection-oriented transport: TCP
- Principles of congestion control
- TCP congestion control
- Evolution of transport-layer

functionality  

## Slide 37 - Principles of reliable data transfer

receiving  

sending  

process  
data  

process  

data  

application  

transport  

reliable channel  

reliable service abstraction  

![Slide 37 preview](Chapter_3_v8.0_assets/slide-037.png)

## Slide 38 - Principles of reliable data transfer

receiving  

sending  

sending  

process  
data  

process  

process  

data  

data  

application  

application  

transport  

transport  

reliable channel  

sender-side of  

reliable service abstraction  

reliable data  
transfer protocol  

unreliable channel  
network  
transport  

reliable service implementation  

receiving  

process  
data  

receiver-side  
of reliable data  
transfer protocol  

## Slide 39 - Principles of reliable data transfer

receiver-side  
of reliable data  
transfer protocol  
Complexity of reliable data  
transfer protocol will depend  
(strongly) on characteristics of  

unreliable channel (lose,  

corrupt, reorder data?)  

receiving  

sending  

process  
data  

process  

data  

application  

transport  

sender-side of  

reliable data  
transfer protocol  

unreliable channel  
network  
transport  

reliable service implementation  

## Slide 40 - Principles of reliable data transfer

receiving  

sending  

process  
data  

process  

data  

application  

transport  

sender-side of  

receiver-side  
of reliable data  
transfer protocol  
Sender, receiver do not know  
the “state” of each other, e.g.,  
was a message received?  
-  
unless communicated via a  
message  

reliable data  
transfer protocol  

unreliable channel  
network  
transport  

reliable service implementation  

## Slide 41 - Reliable data transfer protocol (rdt): interfaces

rdt_send(): called from above,  
(e.g., by app.). Passed data to  
deliver to receiver upper layer  

deliver_data(): called by rdt  
to deliver data to upper layer  

receiving  

sending  

process  
data  

process  

rdt_send()  

data  

deliver_data()  

data  

sender-side  
implementation of  

receiver-side  
implementation of  

rdt reliable data  

rdt reliable data  

packet  

transfer protocol  

transfer protocol  

udt_send()  
rdt_rcv()  

data  
Header  
data  
Header  

unreliable channel  

udt_send(): called by rdt  
to transfer packet over  
unreliable channel to receiver  

rdt_rcv(): called when packet  
arrives on receiver side of  
channel  

Bi-directional communication over  

unreliable channel  

## Slide 42 - Reliable data transfer: getting started

protocol (rdt)  
- consider only unidirectional data transfer

- but control info will flow in both directions!

- use finite state machines (FSM) to specify sender, receiver

event causing state transition  
actions taken on state transition  
state: when in this “state”  

state  

state  

next state uniquely  
determined by next  

event  
actions  

1  

2  

event  

## Slide 43 - rdt1.0: reliable transfer over a reliable channel

- underlying channel perfectly reliable

- no bit errors
- no loss of packets

- separate FSMs for sender, receiver:

- sender sends data into underlying channel
- receiver reads data from underlying channel

rdt_send(data)  

Wait for  
call from  

sender  

packet = make_pkt(data)  
udt_send(packet)  

above  

rdt_rcv(packet)  
Wait for  
call from  

below  
receiver  

extract (packet,data)  
deliver_data(data)  

## Slide 44 - rdt2.0: channel with bit errors

- underlying channel may flip bits in packet

- checksum (e.g., Internet checksum) to detect bit errors
- the question: how to recover from errors?

How do humans recover from “errors” during conversation?  

## Slide 45 - rdt2.0: channel with bit errors

- checksum to detect bit errors
- the question: how to recover from errors?

- acknowledgements (ACKs): receiver explicitly tells sender that pkt

received OK  
- negative acknowledgements (NAKs): receiver explicitly tells sender

that pkt had errors  
- sender retransmits pkt on receipt of NAK

stop and wait  
sender sends one packet, then waits for receiver response  

## Slide 46 - rdt2.0: FSM specifications

rdt_send(data)  

snkpkt = make_pkt(data, checksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) &&  

isNAK(rcvpkt)  

Wait for  
call from  

udt_send(sndpkt)  
Wait for  

sender  

ACK or  

above  

NAK  

rdt_rcv(rcvpkt) && isACK(rcvpkt)  

L  

rdt_rcv(rcvpkt) && corrupt(rcvpkt)  

udt_send(NAK)  

Wait for  
call from  

receiver  

below  

rdt_rcv(rcvpkt) && notcorrupt(rcvpkt)  

extract(rcvpkt,data)  
deliver_data(data)  
udt_send(ACK)  

## Slide 47 - rdt2.0: FSM specification

rdt_send(data)  

snkpkt = make_pkt(data, checksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) &&  

isNAK(rcvpkt)  

isNAK(rcvpkt)  

Wait for  
call from  

udt_send(sndpkt)  
Wait for  

sender  

ACK or  

above  

NAK  

rdt_rcv(rcvpkt) && isACK(rcvpkt)  

isACK(rcvpkt)  

L  

Note: “state” of receiver (did the receiver get my  
message correctly?) isn’t known to sender unless  
somehow communicated from receiver to sender  

- that’s why we need a protocol!

rdt_rcv(rcvpkt) && corrupt(rcvpkt)  

udt_send(NAK)  

Wait for  
call from  

receiver  

below  

rdt_rcv(rcvpkt) && notcorrupt(rcvpkt)  

extract(rcvpkt,data)  
deliver_data(data)  
udt_send(ACK)  

## Slide 48 - rdt2.0: operation with no errors

rdt_send(data)  

snkpkt = make_pkt(data, checksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) &&  

isNAK(rcvpkt)  

Wait for  
call from  

Wait for  

sender  

ACK or  

udt_send(sndpkt)  

above  

NAK  

rdt_rcv(rcvpkt) && isACK(rcvpkt)  

L  

rdt_rcv(rcvpkt) && corrupt(rcvpkt)  

udt_send(NAK)  

Wait for  
call from  

receiver  

below  

rdt_rcv(rcvpkt) && notcorrupt(rcvpkt)  

extract(rcvpkt,data)  
deliver_data(data)  
udt_send(ACK)  

## Slide 49 - rdt2.0: corrupted packet scenario

rdt_send(data)  

snkpkt = make_pkt(data, checksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) &&  

isNAK(rcvpkt)  
Wait for  

Wait for  
call from  

sender  

ACK or  

udt_send(sndpkt)  

above  

NAK  

rdt_rcv(rcvpkt) && isACK(rcvpkt)  

L  

rdt_rcv(rcvpkt) && corrupt(rcvpkt)  

udt_send(NAK)  

Wait for  
call from  

receiver  

below  

rdt_rcv(rcvpkt) && notcorrupt(rcvpkt)  

extract(rcvpkt,data)  
deliver_data(data)  
udt_send(ACK)  

## Slide 50 - rdt2.0 has a fatal flaw!

what happens if ACK/NAK  

corrupted?  
- sender doesn’t know what

happened at receiver!  
- can’t just retransmit: possible

duplicate  

stop and wait  
sender sends one packet, then  
waits for receiver response  

handling duplicates:  

- sender retransmits current pkt

if ACK/NAK corrupted  
- sender adds sequence number

to each pkt  
- receiver discards (doesn’t

deliver up) duplicate pkt  

## Slide 51 - rdt2.1: sender, handling garbled ACK/NAKs

rdt_send(data)  

sndpkt = make_pkt(0, data, checksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) &&  
(corrupt(rcvpkt) ||  
isNAK(rcvpkt) )  

Wait for  

Wait for  
call 0 from  

ACK or  

udt_send(sndpkt)  

NAK 0  

above  

rdt_rcv(rcvpkt)  
&& notcorrupt(rcvpkt) &&  

rdt_rcv(rcvpkt)  
&& notcorrupt(rcvpkt)  
&& isACK(rcvpkt)  

isACK(rcvpkt)  

L  

L  

Wait for  

Wait for  
call 1 from  

ACK or  

rdt_rcv(rcvpkt)  
&& (corrupt(rcvpkt) ||  

NAK 1  

above  

rdt_send(data)  

isNAK(rcvpkt) )  

sndpkt = make_pkt(1, data, checksum)  
udt_send(sndpkt)  

udt_send(sndpkt)  

## Slide 52 - rdt2.1: receiver, handling garbled ACK/NAKs

rdt_rcv(rcvpkt) && (corrupt(rcvpkt)  

sndpkt = make_pkt(NAK, chksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) &&  

not corrupt(rcvpkt) &&  
has_seq1(rcvpkt)  

sndpkt = make_pkt(ACK, chksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) && notcorrupt(rcvpkt)  

&& has_seq0(rcvpkt)  

extract(rcvpkt,data)  
deliver_data(data)  
sndpkt = make_pkt(ACK, chksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) && (corrupt(rcvpkt)  

sndpkt = make_pkt(NAK, chksum)  
udt_send(sndpkt)  

Wait for  

Wait for  

0 from  

1 from  

rdt_rcv(rcvpkt) &&  

below  

below  

not corrupt(rcvpkt) &&  
has_seq0(rcvpkt)  

sndpkt = make_pkt(ACK, chksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) && notcorrupt(rcvpkt)  

&& has_seq1(rcvpkt)  

extract(rcvpkt,data)  
deliver_data(data)  
sndpkt = make_pkt(ACK, chksum)  
udt_send(sndpkt)  

## Slide 53 - rdt2.1: discussion

sender:  

- seq # added to pkt
- two seq. #s (0,1) will suffice.

Why?  
- must check if received ACK/NAK

corrupted  
- twice as many states

- state must “remember” whether

“expected” pkt should have seq #  
of 0 or 1  

receiver:  

- must check if received packet

is duplicate  

- state indicates whether 0 or 1 is

expected pkt seq #  
- note: receiver can not know if

its last ACK/NAK received OK  
at sender  

## Slide 54 - rdt2.2: a NAK-free protocol

- same functionality as rdt2.1, using ACKs only
- instead of NAK, receiver sends ACK for last pkt received OK

- receiver must explicitly include seq # of pkt being ACKed
- duplicate ACK at sender results in same action as NAK:

retransmit current pkt  

As we will see, TCP uses this approach to be NAK-free  

## Slide 55 - rdt2.2: sender, receiver fragments

rdt_send(data)  

sndpkt = make_pkt(0, data, checksum)  
udt_send(sndpkt)  

rdt_rcv(rcvpkt) &&  
( corrupt(rcvpkt) ||  

Wait for  

Wait for  
call 0 from  

isACK(rcvpkt,1) )  

ACK  

udt_send(sndpkt)  

0  
sender FSM  

above  

fragment  

rdt_rcv(rcvpkt)  
&& notcorrupt(rcvpkt)  
&& isACK(rcvpkt,0)  

rdt_rcv(rcvpkt) &&  

(corrupt(rcvpkt) ||  

L  

receiver FSM  

Wait for  

has_seq1(rcvpkt))  

0 from  

fragment  

udt_send(sndpkt)  

below  

rdt_rcv(rcvpkt) && notcorrupt(rcvpkt)  

&& has_seq1(rcvpkt)  

extract(rcvpkt,data)  
deliver_data(data)  
sndpkt = make_pkt(ACK1, chksum)  
udt_send(sndpkt)  

## Slide 56 - rdt3.0: channels with errors and loss

New channel assumption: underlying channel can also lose  

packets (data, ACKs)  

- checksum, sequence #s, ACKs, retransmissions will be of help …

but not quite enough  

Q: How do humans handle lost sender-to-  

receiver words in conversation?  

## Slide 57 - rdt3.0: channels with errors and loss

Approach: sender waits “reasonable” amount of time for ACK  

- retransmits if no ACK received in this time
- if pkt (or ACK) just delayed (not lost):

- retransmission will be duplicate, but seq #s already handle this!

- receiver must specify seq # of packet being ACKed

- use countdown timer to interrupt after “reasonable” amount

of time  

timeout  

## Slide 58 - rdt3.0 sender

rdt_send(data)  

sndpkt = make_pkt(0, data, checksum)  
udt_send(sndpkt)  
start_timer  

Wait  

Wait for  
call 0 from  

for  
ACK0  

above  

rdt_rcv(rcvpkt)  
&& notcorrupt(rcvpkt)  
&& isACK(rcvpkt,1)  

rdt_rcv(rcvpkt)  
&& notcorrupt(rcvpkt)  
&& isACK(rcvpkt,0)  

stop_timer  

stop_timer  

Wait  

Wait for  
call 1 from  

for  
ACK1  

above  

rdt_send(data)  

sndpkt = make_pkt(1, data, checksum)  
udt_send(sndpkt)  
start_timer  

## Slide 59 - rdt3.0 sender

rdt_send(data)  

rdt_rcv(rcvpkt) &&  
( corrupt(rcvpkt) ||  
isACK(rcvpkt,1) )  

sndpkt = make_pkt(0, data, checksum)  
udt_send(sndpkt)  
start_timer  

L  
rdt_rcv(rcvpkt)  

L  

Wait  

timeout  
Wait for  
call 0 from  

for  
ACK0  

udt_send(sndpkt)  
start_timer  

above  

rdt_rcv(rcvpkt)  
&& notcorrupt(rcvpkt)  
&& isACK(rcvpkt,1)  

rdt_rcv(rcvpkt)  
&& notcorrupt(rcvpkt)  
&& isACK(rcvpkt,0)  

stop_timer  

stop_timer  

Wait  

Wait for  
call 1 from  

timeout  

for  
ACK1  

udt_send(sndpkt)  
start_timer  

above  

rdt_rcv(rcvpkt)  

L  

rdt_send(data)  

rdt_rcv(rcvpkt) &&  
( corrupt(rcvpkt) ||  
isACK(rcvpkt,0) )  

sndpkt = make_pkt(1, data, checksum)  
udt_send(sndpkt)  
start_timer  

L  

## Slide 60 - rdt3.0 in action

sender  
receiver  

send pkt0  

rcv pkt0  
pkt0  

send ack0  

ack0  

rcv ack0  

pkt1  

send pkt1  

rcv pkt1  

send ack1  

ack1  

rcv ack1  

pkt0  

send pkt0  

rcv pkt0  

send ack0  

ack0  

(a) no loss  

stop and wait  
sender sends one packet, then  
waits for receiver response  

sender  
receiver  

send pkt0  

rcv pkt0  
pkt0  

send ack0  

ack0  

rcv ack0  

pkt1  

send pkt1  

X  
loss  

timeout  
resend pkt1  

pkt1  

rcv pkt1  

send ack1  

ack1  

rcv ack1  

pkt0  

send pkt0  

rcv pkt0  

send ack0  

ack0  

(b) packet loss  

## Slide 61 - rdt3.0 in action

sender  
receiver  

send pkt0  

rcv pkt0  
pkt0  

send ack0  

ack0  

rcv ack0  

pkt1  

send pkt1  

rcv pkt1  
send ack1  

ack1  
X  
loss  

timeout  
resend pkt1  

pkt1  

rcv pkt1  

(detect duplicate)  

ack1  

send ack1  

rcv ack1  

pkt0  

send pkt0  

rcv pkt0  

send ack0  

ack0  

(c) ACK loss  

sender  
receiver  

send pkt0  

rcv pkt0  
pkt0  

send ack0  
rcv ack0  
send pkt1  

ack0  

pkt1  

rcv pkt1  
send ack1  

ack1  

timeout  
resend pkt1  

pkt1  

rcv pkt1  

rcv ack1  

(detect duplicate)  

send ack1  
send pkt0  

pkt0  

rcv pkt0  

ack1  

(ignore)  
rcv ack1  

send ack0  
ack0  

pkt1  

(d) premature timeout/ delayed ACK  

## Slide 62 - Performance of rdt3.0 (stop-and-wait)

- U sender: utilization – fraction of time sender busy sending

- example: 1 Gbps link, 15 ms prop. delay, 8000-bit packet

8000 bits  
109 bits/sec  
=  
= 8 microsecs  
-  
time to transmit packet into channel:  

Dtrans =  
L  
R  

## Slide 63 - rdt3.0: stop-and-wait operation

sender  
receiver  

first packet bit transmitted, t = 0  

first packet bit arrives  
last packet bit arrives, send ACK  

RTT  

ACK arrives, send next  

packet, t = RTT + L / R  

![Slide 63 preview](Chapter_3_v8.0_assets/slide-063.png)

## Slide 64 - rdt3.0: stop-and-wait operation

sender  
receiver  

Usender=  
L / R  

L/R  
+ L / R  

RTT  

RTT  

=  
.008  
30.008  

= 0.00027  

- rdt 3.0 protocol performance stinks!
- Protocol limits performance of underlying infrastructure (channel)

![Slide 64 preview](Chapter_3_v8.0_assets/slide-064.png)

## Slide 65 - rdt3.0: pipelined protocols operation

pipelining: sender allows multiple, “in-flight”, yet-to-be-acknowledged  

packets  

- range of sequence numbers must be increased
- buffering at sender and/or receiver

![Slide 65 preview](Chapter_3_v8.0_assets/slide-065.png)

## Slide 66 - Pipelining: increased utilization

sender  
receiver  

first packet bit transmitted, t = 0  

last bit transmitted, t = L / R  

first packet bit arrives  
last packet bit arrives, send ACK  

RTT  

last bit of 2nd packet arrives, send ACK  
last bit of 3rd packet arrives, send ACK  

ACK arrives, send next  

packet, t = RTT + L / R  

3-packet pipelining increases  

utilization by a factor of 3!  

30.008  
= 0.00081  
3L / R  

U sender =  
.0024  

=  

RTT + L / R  

## Slide 67 - Go-Back-N: sender

- sender: “window” of up to N, consecutive transmitted but unACKed pkts

- k-bit seq # in pkt header

- cumulative ACK: ACK(n): ACKs all packets up to, including seq # n

-  
on receiving ACK(n): move window forward to begin at n+1  
- timer for oldest in-flight packet
- timeout(n): retransmit packet n and all higher seq # packets in window

## Slide 68 - Go-Back-N: receiver

- ACK-only: always send ACK for correctly-received packet so far, with

highest in-order seq #  

- may generate duplicate ACKs
- need only remember rcv_base
- on receipt of out-of-order packet:

- can discard (don’t buffer) or buffer: an implementation decision
- re-ACK pkt with highest in-order seq #

Receiver view of sequence number space:  

received and ACKed  

…  
…  

Out-of-order: received but not ACKed  

rcv_base  

Not received  

## Slide 69 - Go-Back-N in action

sender  
receiver  

sender window (N=4)  

send pkt0  
send pkt1  
send pkt2  
send pkt3  

0 1 2 3 4 5 6 7 8  

0 1 2 3 4 5 6 7 8  

receive pkt0, send ack0  
receive pkt1, send ack1  

0 1 2 3 4 5 6 7 8  

Xloss  

0 1 2 3 4 5 6 7 8  

(wait)  

receive pkt3, discard,  

(re)send ack1  

rcv ack0, send pkt4  
0 1 2 3 4 5 6 7 8  

0 1 2 3 4 5 6 7 8  
rcv ack1, send pkt5  

receive pkt4, discard,  

(re)send ack1  
receive pkt5, discard,  

ignore duplicate ACK  

(re)send ack1  

pkt 2 timeout  

send pkt2  
send pkt3  
send pkt4  
send pkt5  

0 1 2 3 4 5 6 7 8  

0 1 2 3 4 5 6 7 8  
0 1 2 3 4 5 6 7 8  
0 1 2 3 4 5 6 7 8  

rcv pkt2, deliver, send ack2  
rcv pkt3, deliver, send ack3  
rcv pkt4, deliver, send ack4  
rcv pkt5, deliver, send ack5  

## Slide 70 - Selective repeat

- receiver individually acknowledges all correctly received packets

- buffers packets, as needed, for eventual in-order delivery to upper

layer  
- sender times-out/retransmits individually for unACKed packets

- sender maintains timer for each unACKed pkt
- sender window

- N consecutive seq #s
- limits seq #s of sent, unACKed packets

## Slide 71 - Selective repeat: sender, receiver windows

_Không có văn bản có thể trích xuất từ slide này._

![Slide 71 preview](Chapter_3_v8.0_assets/slide-071.png)

## Slide 72 - Selective repeat: sender and receiver

sender  

data from above:  

- if next available seq # in

window, send packet  
timeout(n):  

- resend packet n, restart timer

ACK(n) in [sendbase,sendbase+N]:  

- mark packet n as received
- if n smallest unACKed packet,

advance window base to next  
unACKed seq #  

receiver  

packet n in [rcvbase, rcvbase+N-1]  

- send ACK(n)
- out-of-order: buffer
- in-order: deliver (also deliver

buffered, in-order packets),  
advance window to next not-yet-  
received packet  
packet n in [rcvbase-N,rcvbase-1]  

- ACK(n)
otherwise:  

- ignore

## Slide 73 - Selective Repeat in action

sender  
receiver  

sender window (N=4)  

send pkt0  
send pkt1  
send pkt2  
send pkt3  

0 1 2 3 4 5 6 7 8  

0 1 2 3 4 5 6 7 8  

receive pkt0, send ack0  
receive pkt1, send ack1  

0 1 2 3 4 5 6 7 8  

Xloss  

0 1 2 3 4 5 6 7 8  

(wait)  

receive pkt3, buffer,  

send ack3  

rcv ack0, send pkt4  
0 1 2 3 4 5 6 7 8  

0 1 2 3 4 5 6 7 8  
rcv ack1, send pkt5  

receive pkt4, buffer,  

send ack4  
receive pkt5, buffer,  

record ack3 arrived  

send ack5  

pkt 2 timeout  

send pkt2  
(but not 3,4,5)  

0 1 2 3 4 5 6 7 8  

0 1 2 3 4 5 6 7 8  
0 1 2 3 4 5 6 7 8  
0 1 2 3 4 5 6 7 8  

rcv pkt2; deliver pkt2,  
pkt3, pkt4, pkt5; send ack2  

Q: what happens when ack2 arrives?  

## Slide 74 - Selective repeat: a dilemma!

example:  

- seq #s: 0, 1, 2, 3 (base 4 counting)
- window size=3

receiver window  
(after receipt)  
sender window  
(after receipt)  

pkt0  

0 1 2 3 0 1 2  

pkt1  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

pkt2  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  
pkt3  

X  

0 1 2 3 0 1 2  

pkt0  

will accept packet  
with seq number 0  

(a) no problem  

pkt0  

0 1 2 3 0 1 2  

pkt1  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

pkt2  

0 1 2 3 0 1 2  
X  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

X  

X  

timeout  
retransmit pkt0  

0 1 2 3 0 1 2  
pkt0  

will accept packet  
with seq number 0  
(b) oops!  

## Slide 75 - Selective repeat: a dilemma!

example:  

- seq #s: 0, 1, 2, 3 (base 4 counting)
- window size=3

Q: what relationship is needed  

between sequence # size and  
window size to avoid problem  
in scenario (b)?  

receiver window  
(after receipt)  
sender window  
(after receipt)  

pkt0  

0 1 2 3 0 1 2  

pkt1  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

pkt2  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  
pkt3  

X  

0 1 2 3 0 1 2  

- receiver can’t

pkt0  

will accept packet  
with seq number 0  

see sender side  
- receiver

(a) no problem  

behavior  
identical in both  
cases!  
- something’s

pkt0  

0 1 2 3 0 1 2  

(very) wrong!  

pkt1  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

pkt2  

0 1 2 3 0 1 2  
X  

0 1 2 3 0 1 2  

0 1 2 3 0 1 2  

X  

X  

timeout  
retransmit pkt0  

0 1 2 3 0 1 2  
pkt0  

will accept packet  
with seq number 0  
(b) oops!  

## Slide 76 - Chapter 3: roadmap

- segment structure
- reliable data transfer
- flow control
- connection management
- Principles of congestion control
- TCP congestion control

![Slide 76 preview](Chapter_3_v8.0_assets/slide-076.png)

## Slide 77 - TCP: overview RFCs: 793,1122, 2018, 5681, 7323

- point-to-point:

- one sender, one receiver
- reliable, in-order byte

stream:  

- no “message boundaries"
- full duplex data:

- bi-directional data flow in

same connection  
- MSS: maximum segment size

- cumulative ACKs
- pipelining:

- TCP congestion and flow control

set window size  
- connection-oriented:

- handshaking (exchange of control

messages) initializes sender,  
receiver state before data exchange  
- flow controlled:

- sender will not overwhelm receiver

## Slide 78 - TCP segment structure

32 bits  

source port #  
dest port #  

segment seq #: counting  
bytes of data into bytestream  
(not segments!)  

ACK: seq # of next expected  

sequence number  

byte; A bit: this is an ACK  

A  
acknowledgement number  

not  
used  
receive window  
flow control: # bytes  
receiver willing to accept  

head  

len  
length (of TCP header)  

P  
U  
C E  

F  
S  
R  

checksum  
Internet checksum  

Urg data pointer  

options (variable length)  

C, E: congestion notification  

TCP options  

application  

data sent by  
application into  
TCP socket  

RST, SYN, FIN: connection  

data  
(variable length)  

management  

## Slide 79 - TCP sequence numbers, ACKs

Sequence numbers:  

- byte stream “number” of

first byte in segment’s data  

Acknowledgements:  

- seq # of next byte expected

from other side  
- cumulative ACK

Q: how receiver handles out-of-  

order segments  

- A: TCP spec doesn’t say, - up

to implementor  

outgoing segment from sender  

source port #  
dest port #  

sequence number  
acknowledgement number  

rwnd  

checksum  

urg pointer  

window size  

N  

sender sequence number space  

sent  
ACKed  

usable  
but not  
yet sent  

sent, not-  
yet ACKed  
(“in-flight”)  

not  
usable  

outgoing segment from receiver  

source port #  
dest port #  

sequence number  
acknowledgement number  

A  

rwnd  

checksum  

urg pointer  

## Slide 80 - TCP sequence numbers, ACKs

Host B  
Host A  

User types‘C’  

Seq=42, ACK=79, data = ‘C’  

host ACKs receipt  
of‘C’, echoes back ‘C’  

Seq=79, ACK=43, data = ‘C’  

host ACKs receipt  

of echoed ‘C’  

Seq=43, ACK=80  

simple telnet scenario  

![Slide 80 preview](Chapter_3_v8.0_assets/slide-080.png)

## Slide 81 - TCP round trip time, timeout

Q: how to set TCP timeout  

value?  
- longer than RTT, but RTT varies!
- too short: premature timeout,

unnecessary retransmissions  
- too long: slow reaction to

segment loss  

Q: how to estimate RTT?  
- SampleRTT:measured time

from segment transmission until  
ACK receipt  

- ignore retransmissions
- SampleRTT will vary, want

estimated RTT “smoother”  

- average several recent

measurements, not just current  
SampleRTT  

## Slide 82 - TCP round trip time, timeout

EstimatedRTT = (1- )*EstimatedRTT + *SampleRTT  

- exponential weighted moving average (EWMA)
- influence of past sample decreases exponentially fast
- typical value: = 0.125

RTT: gaia.cs.umass.edu to fantasia.eurecom.fr  

350  

RTT: gaia.cs.umass.edu to fantasia.eurecom.fr  

RTT (milliseconds)  

300  

250  

RTT (milliseconds)  

200  

sampleRTT  

150  

EstimatedRTT  

100  

1  
8  
15  
22  
29  
36  
43  
50  
57  
64  
71  
78  
85  
92  
99  
106  

time (seconnds)  

time (seconds)  

## Slide 83 - TCP round trip time, timeout

- timeout interval: EstimatedRTT plus “safety margin”

- large variation in EstimatedRTT: want a larger safety margin

TimeOutInterval = EstimatedRTT + 4*DevRTT  

- DevRTT: EWMA of SampleRTT deviation from EstimatedRTT:

DevRTT = (1-)*DevRTT + *|SampleRTT-EstimatedRTT|  

* Check out the online interactive exercises for more examples: http://gaia.cs.umass.edu/kurose_ross/interactive/  

estimated RTT  
“safety margin”  

(typically, = 0.25)  

## Slide 84 - TCP Sender (simplified)

event: data received from  
application  

- create segment with seq #

- seq # is byte-stream number of

first data byte in segment  
- start timer if not already

running  

- think of timer as for oldest

unACKed segment  
- expiration interval:

TimeOutInterval  

event: timeout  

- retransmit segment that

caused timeout  
- restart timer

event: ACK received  

- if ACK acknowledges

previously unACKed segments  

- update what is known to be

ACKed  
- start timer if there are still

unACKed segments  

## Slide 85 - TCP Receiver: ACK generation [RFC 5681]

TCP receiver action  

Event at receiver  

delayed ACK. Wait up to 500ms  
for next segment. If no next segment,  
send ACK  

arrival of in-order segment with  
expected seq #. All data up to  
expected seq # already ACKed  

immediately send single cumulative  
ACK, ACKing both in-order segments  

arrival of in-order segment with  
expected seq #. One other  
segment has ACK pending  

immediately send duplicate ACK,  
indicating seq. # of next expected byte  

arrival of out-of-order segment  
higher-than-expect seq. # .  
Gap detected  

immediate send ACK, provided that  
segment starts at lower end of gap  

arrival of segment that  
partially or completely fills gap  

## Slide 86 - TCP: retransmission scenarios

Host B  
Host A  

Seq=92, 8 bytes of data  

timeout  

ACK=100  
X  

Seq=92, 8 bytes of data  

ACK=100  

lost ACK scenario  

Host B  
Host A  

SendBase=92  

Seq=92, 8 bytes of data  

Seq=100, 20 bytes of data  

timeout  

ACK=100  

ACK=120  

Seq=92, 8  
bytes of data  

SendBase=100  

send cumulative  
ACK for 120  

SendBase=120  

ACK=120  

SendBase=120  

premature timeout  

## Slide 87 - TCP: retransmission scenarios

Host B  
Host A  

Seq=92, 8 bytes of data  

Seq=100, 20 bytes of data  

ACK=100  

X  

ACK=120  

Seq=120, 15 bytes of data  

cumulative ACK covers  

for earlier lost ACK  

![Slide 87 preview](Chapter_3_v8.0_assets/slide-087.png)

## Slide 88 - TCP fast retransmit

TCP fast retransmit  

if sender receives 3 additional  
ACKs for same data (“triple  
duplicate ACKs”), resend unACKed  
segment with smallest seq #  

- likely that unACKed segment lost,

so don’t wait for timeout  

Receipt of three duplicate ACKs  
indicates 3 segments received  
after a missing segment – lost  
segment is likely. So, retransmit!  

Host B  
Host A  

X  

timeout  

Seq=100, 20 bytes of data  

## Slide 89 - Chapter 3: roadmap

- segment structure
- reliable data transfer
- flow control
- connection management
- Principles of congestion control
- TCP congestion control

![Slide 89 preview](Chapter_3_v8.0_assets/slide-089.png)

## Slide 90 - TCP flow control

application  

Q: What happens if network  
layer delivers data faster  
than application layer  
removes data from socket  
buffers?  

process  

Application removing  

data from TCP socket  

buffers  

TCP socket  
receiver buffers  

TCP  
code  

Network layer  
delivering IP datagram  

payload into TCP  

IP  
code  

socket buffers  

from sender  

receiver protocol stack  

## Slide 91 - TCP flow control

application  

Q: What happens if network  
layer delivers data faster than  
application layer removes  
data from socket buffers?  

process  

Application removing  

data from TCP socket  

buffers  

TCP socket  
receiver buffers  

TCP  
code  

Network layer  
delivering IP datagram  

payload into TCP  

IP  
code  

socket buffers  

from sender  

receiver protocol stack  

## Slide 92 - TCP flow control

application  

Q: What happens if network  
layer delivers data faster than  
application layer removes  
data from socket buffers?  

process  

Application removing  

data from TCP socket  

buffers  

TCP socket  
receiver buffers  

TCP  
code  

receive window  
flow control: # bytes  
receiver willing to accept  

IP  
code  

from sender  

receiver protocol stack  

## Slide 93 - TCP flow control

Q: What happens if network  
layer delivers data faster than  
application layer removes  
data from socket buffers?  

flow control  

receiver controls sender, so  
sender won’t overflow  
receiver’s buffer by  
transmitting too much, too fast  

application  

process  

Application removing  

data from TCP socket  

buffers  

TCP socket  
receiver buffers  

TCP  
code  

IP  
code  

from sender  

receiver protocol stack  

## Slide 94 - TCP flow control

- TCP receiver “advertises” free buffer

space in rwnd field in TCP header  

- RcvBuffer size set via socket

options (typical default is 4096 bytes)  
- many operating systems auto-adjust

RcvBuffer  

- sender limits amount of unACKed

(“in-flight”) data to received rwnd  

- guarantees receive buffer will not

overflow  

to application process  

buffered data  

RcvBuffer  

free buffer space  
rwnd  

TCP segment payloads  

TCP receiver-side buffering  

## Slide 95 - TCP flow control

- TCP receiver “advertises” free buffer

space in rwnd field in TCP header  

- RcvBuffer size set via socket

options (typical default is 4096 bytes)  
- many operating systems autoadjust

RcvBuffer  

- sender limits amount of unACKed

(“in-flight”) data to received rwnd  

- guarantees receive buffer will not

overflow  

flow control: # bytes receiver willing to accept  

receive window  

TCP segment format  

## Slide 96 - TCP connection management

before exchanging data, sender/receiver “handshake”:  

- agree to establish connection (each knowing the other willing to establish connection)
- agree on connection parameters (e.g., starting seq #s)

application  

connection state: ESTAB  
connection variables:  

seq # client-to-server  

server-to-client  
rcvBuffer size  

at server,client  

network  

Socket clientSocket =  

newSocket("hostname","port number");  

application  

connection state: ESTAB  
connection Variables:  

seq # client-to-server  

server-to-client  
rcvBuffer size  

at server,client  

network  

Socket connectionSocket =  

welcomeSocket.accept();  

## Slide 97 - Agreeing to establish a connection

2-way handshake:  

Let’s talk  

OK  
ESTAB  
ESTAB  

choose x  
req_conn(x)  

ESTAB  
ESTAB  
acc_conn(x)  

Q: will 2-way handshake always  

work in network?  
- variable delays
- retransmitted messages (e.g.,

req_conn(x)) due to message  
loss  
- message reordering
- can’t “see” other side

## Slide 98 - 2-way handshake scenarios

choose x  
req_conn(x)  

ESTAB  

acc_conn(x)  

ESTAB  

data(x+1)  
accept  
data(x+1)  
ACK(x+1)  

connection  
x completes  

No problem!  

![Slide 98 preview](Chapter_3_v8.0_assets/slide-098.png)

## Slide 99 - 2-way handshake scenarios

choose x  
req_conn(x)  

ESTAB  

retransmit  
req_conn(x)  

acc_conn(x)  

ESTAB  

req_conn(x)  

connection  
x completes  

client  
terminates  

server  
forgets x  

ESTAB  

acc_conn(x)  
Problem: half open  
connection! (no client)  

## Slide 100 - 2-way handshake scenarios

choose x  
req_conn(x)  

ESTAB  

retransmit  
req_conn(x)  

acc_conn(x)  

ESTAB  

data(x+1)  
accept  
data(x+1)  

retransmit  
data(x+1)  

connection  
x completes  
server  
forgets x  

client  
terminates  

req_conn(x)  

ESTAB  

data(x+1)  

accept  
data(x+1)  

Problem: dup data  
accepted!  

## Slide 101 - TCP 3-way handshake

Server state  

serverSocket = socket(AF_INET,SOCK_STREAM)  
serverSocket.bind((‘’,serverPort))  
serverSocket.listen(1)  
connectionSocket, addr = serverSocket.accept()  

Client state  

clientSocket = socket(AF_INET, SOCK_STREAM)  

LISTEN  

LISTEN  

clientSocket.connect((serverName,serverPort))  

choose init seq num, x  

send TCP SYN msg  

SYNSENT  

SYNbit=1, Seq=x  

choose init seq num, y  
send TCP SYNACK  
msg, acking SYN  

SYN RCVD  

SYNbit=1, Seq=y  
ACKbit=1; ACKnum=x+1  

received SYNACK(x)  
indicates server is live;  

ESTAB  

send ACK for SYNACK;  
this segment may contain  

ACKbit=1, ACKnum=y+1  

client-to-server data  
received ACK(y)  
indicates client is live  

ESTAB  

## Slide 102 - A human 3-way handshake protocol

1. On belay?  

2. Belay on.  

3. Climbing.  

![Slide 102 preview](Chapter_3_v8.0_assets/slide-102.png)

## Slide 103 - Closing a TCP connection

- client, server each closes their side of connection

- send TCP segment with FIN bit = 1
- respond to received FIN with ACK

- on receiving FIN, ACK can be combined with own FIN
- simultaneous FIN exchanges can be handled

## Slide 104 - Closing a TCP connection

client state  
server state  

ESTAB  
ESTAB  

clientSocket.close()  

FIN_WAIT_1  
FINbit=1, seq=x  
can no longer  

send but can  

CLOSE_WAIT  

receive data  

ACKbit=1; ACKnum=x+1  
wait for server  

can still  
send data  

FIN_WAIT_2  

close  

LAST_ACK  

FINbit=1, seq=y  

can no longer  
send data  

TIMED_WAIT  

ACKbit=1; ACKnum=y+1  

timed wait  

for 2*max  
segment lifetime  

CLOSED  

CLOSED  

## Slide 105 - Chapter 3: roadmap

- Transport-layer services
- Multiplexing and demultiplexing
- Connectionless transport: UDP
- Principles of reliable data transfer
- Connection-oriented transport: TCP
- Principles of congestion control
- TCP congestion control
- Evolution of transport-layer

functionality  

## Slide 106 - Principles of congestion control

Congestion:  

- informally: “too many sources sending too much data too fast for

network to handle”  
- manifestations:

- long delays (queueing in router buffers)
- packet loss (buffer overflow at routers)

- different from flow control!

- a top-10 problem!

congestion control:  

too many senders,  

sending too fast  

flow control: one sender  
too fast for one receiver  

## Slide 107 - Causes/costs of congestion: scenario 1

Simplest scenario:  

- one router, infinite buffers

- no retransmissions needed

R  
- input, output link capacity: R

- two flows: fairly, R/2

Q: What happens as  

arrival rate lin  
approaches R/2?  

original data: lin  

throughput: lout  

Host A  

infinite shared  
output link buffers  

R  

Host B  

R/2  

lout  

delay  

throughput:  

lin  

lin  

R/2  

R/2  

maximum per-connection  
throughput: R/2  

large delays as arrival rate  
lin approaches capacity  

## Slide 108 - Causes/costs of congestion: scenario 2

- one router, finite buffers

- sender retransmits lost, timed-out packet

- application-layer input = application-layer output: lin = lout
- transport-layer input includes retransmissions : l’in
lin  

lin : original data  

Host A  

lout  

l'in: original data, plus  

retransmitted data  

R  
R  

finite shared output  

Host B  

link buffers  

## Slide 109 - Causes/costs of congestion: scenario 2

Idealization: perfect knowledge  

- sender sends only when router buffers available

lin : original data  

Host A  

copy  

l'in: original data, plus  

retransmitted data  

free buffer space!  

R  
R  

finite shared output  

Host B  

link buffers  

R/2  

lout  
throughput:  

R/2  
lin  

lout  

## Slide 110 - Causes/costs of congestion: scenario 2

Idealization: some perfect knowledge  

- packets can be lost (dropped at router) due to

full buffers  

- sender knows when packet has been dropped:

only resends if packet known to be lost  

lin : original data  

Host A  

l'in: original data, plus  

copy  

retransmitted data  

no buffer space!  

R  
R  

finite shared output  

Host B  

link buffers  

## Slide 111 - Causes/costs of congestion: scenario 2

Idealization: some perfect knowledge  

- packets can be lost (dropped at router) due to

full buffers  

- sender knows when packet has been dropped:

only resends if packet known to be lost  

lin : original data  

Host A  

l'in: original data, plus  

retransmitted data  

free buffer space!  

R  
R  

finite shared output  

Host B  

link buffers  

R/2  

“wasted” capacity due  
to retransmissions  

lout  
throughput:  

when sending at  
R/2, some packets  
are needed  
retransmissions  

lin  

R/2  

## Slide 112 - Causes/costs of congestion: scenario 2

Realistic scenario: un-needed duplicates  

- packets can be lost, dropped at router due to

full buffers – requiring retransmissions  
- but sender timer can time out prematurely,

sending two copies, both of which are delivered  

lin : original data  

Host A  

l'in: original data, plus  

timeout  

copy  

retransmitted data  

free buffer space!  

R  
R  

finite shared output  

Host B  

link buffers  

R/2  

“wasted” capacity due  
to un-needed  
retransmissions  

lout  
throughput:  

when sending at  
R/2, some packets  
are retransmissions,  
including needed  
and un-needed  
duplicates, that are  
delivered!  

lin  

R/2  

## Slide 113 - Causes/costs of congestion: scenario 2

Realistic scenario: un-needed duplicates  

- packets can be lost, dropped at router due to

full buffers – requiring retransmissions  
- but sender timer can time out prematurely,

sending two copies, both of which are delivered  
when sending at  
R/2, some packets  
are retransmissions,  
including needed  
and un-needed  
duplicates, that are  
delivered!  

“costs” of congestion:  
- more work (retransmission) for given receiver throughput
- unneeded retransmissions: link carries multiple copies of a packet

- decreasing maximum achievable throughput

R/2  

“wasted” capacity due  
to un-needed  
retransmissions  

lout  
throughput:  

lin  

R/2  

## Slide 114 - Causes/costs of congestion: scenario 3

’ increase ?  
A: as red lin  

Q: what happens as lin and lin  

- four senders
- multi-hop paths
- timeout/retransmit

’ increases, all arriving blue pkts at upper  
queue are dropped, blue throughput g 0  

lin : original data  

Host A  

Host B  

l'in: original data, plus  

retransmitted data  

finite shared  
output link buffers  

Host C  
Host D  

lout  

## Slide 115 - Causes/costs of congestion: scenario 3

R/2  

lout  

lin  

’  

R/2  

another “cost” of congestion:  
- when packet dropped, any upstream transmission capacity and

buffering used for that packet was wasted!  

![Slide 115 preview](Chapter_3_v8.0_assets/slide-115.png)

## Slide 116 - Causes/costs of congestion: insights

- throughput can never exceed capacity

- delay increases as capacity approached

- loss/retransmission decreases effective

throughput  

- un-needed duplicates further decreases

effective throughput  

- upstream transmission capacity/buffering

wasted for packets lost downstream  

R/2  

lout  
throughput:  

R/2  
lin  

delay  

R/2  

lin  

R/2  

lout  
throughput:  

lin  

R/2  

R/2  

lout  
throughput:  

R/2  

lin  

R/2  

lout  

lin’  

R/2  

## Slide 117 - Approaches towards congestion control

End-end congestion control:  
- no explicit feedback from

network  
- congestion inferred from

data  
data  
ACKs  
ACKs  

observed loss, delay  

- approach taken by TCP

![Slide 117 preview](Chapter_3_v8.0_assets/slide-117.png)

## Slide 118 - Approaches towards congestion control

explicit congestion info  
Network-assisted congestion  

control:  
- routers provide direct feedback

to sending/receiving hosts with  
flows passing through congested  
router  
- may indicate congestion level or

data  
data  
ACKs  
ACKs  

explicitly set sending rate  

- e.g., TCP ECN, ATM, DECbit protocols

## Slide 119 - Chapter 3: roadmap

- Transport-layer services
- Multiplexing and demultiplexing
- Connectionless transport: UDP
- Principles of reliable data transfer
- Connection-oriented transport: TCP
- Principles of congestion control
- TCP congestion control
- Evolution of transport-layer

functionality  

## Slide 120 - TCP congestion control: AIMD

- approach: senders can increase sending rate until packet loss

(congestion) occurs, then decrease sending rate on loss event  

Additive Increase  

increase sending rate by 1  
maximum segment size (MSS)  
every RTT until loss detected  

TCP sender Sending rate  

Multiplicative Decrease  

cut sending rate in half at  
each loss event  

AIMD sawtooth  
behavior: probing  

for bandwidth  

## Slide 121 - TCP AIMD: more

Multiplicative decrease detail: 2 events, sending rate is  

- Cut in half on loss detected by triple duplicate ACK (TCP Reno)
- Cut to 1 MSS (maximum segment size) when loss detected by

timeout (TCP Tahoe)  

Why AIMD?  

- AIMD – a distributed, asynchronous algorithm – has been

shown to:  
- optimize congested flow rates network wide!
- have desirable stability properties

## Slide 122 - TCP congestion control: details

cwnd  
sender sequence number space  

TCP sending behavior:  
- roughly: send cwnd bytes,

wait RTT for ACKs, then  
send more bytes  

last byte  
ACKed  

TCP rate ~~ cwnd  

available but  
not used  

bytes/sec  
sent, but not-  
yet ACKed  
(“in-flight”)  

RTT  

last byte sent  

- TCP sender limits transmission:
- cwnd is dynamically adjusted in response to observed

LastByteSent - LastByteAcked < cwnd  

network congestion (implementing TCP congestion control)  

## Slide 123 - TCP slow start

- when connection begins,

increase rate exponentially  
until first loss event:  

- initially cwnd = 1 MSS
- double cwnd every RTT
- done by incrementing cwnd

for every ACK received  

- summary: initial rate is

slow, but ramps up  
exponentially fast  

Host A  
Host B  

RTT  

time  

## Slide 124 - TCP: from slow start to congestion avoidance

Q: when should the exponential  

increase switch to linear?  
A: when cwnd gets to 1/2 of its  

X  

value before timeout.  

Implementation:  

- variable ssthresh
- on loss event, ssthresh is set to

1/2 of cwnd just before loss event  

* Check out the online interactive exercises for more examples: http://gaia.cs.umass.edu/kurose_ross/interactive/  

## Slide 125 - Summary: TCP congestion control

New  
ACK!  

New  
ACK!  

new ACK.  

duplicate ACK  

cwnd = cwnd + MSS (MSS/cwnd)  

new ACK  
dupACKcount++  

dupACKcount = 0  
transmit new segment(s), as allowed  

cwnd = cwnd+MSS  
dupACKcount = 0  
transmit new segment(s), as allowed  

L  
cwnd = 1 MSS  
ssthresh = 64 KB  
dupACKcount = 0  

L  
cwnd > ssthresh  
congestion  
avoidance  

slow  

start  

timeout  
ssthresh = cwnd/2  

duplicate ACK  

cwnd = 1 MSS  
dupACKcount = 0  
retransmit missing segment  

timeout  
ssthresh = cwnd/2  

dupACKcount++  

cwnd = 1 MSS  
dupACKcount = 0  
retransmit missing segment  

New  
ACK!  

timeout  
ssthresh = cwnd/2  
cwnd = 1  
dupACKcount = 0  
retransmit missing segment  

New ACK  

dupACKcount == 3  
cwnd = ssthresh  
dupACKcount = 0  

dupACKcount == 3  

ssthresh= cwnd/2  
cwnd = ssthresh + 3  
retransmit missing segment  

ssthresh= cwnd/2  
cwnd = ssthresh + 3  
retransmit missing segment  

fast  
recovery  

duplicate ACK  

cwnd = cwnd + MSS  
transmit new segment(s), as allowed  

## Slide 126 - TCP CUBIC

- Is there a better way than AIMD to “probe” for usable bandwidth?

- Insight/intuition:

- Wmax: sending rate at which congestion loss was detected

- congestion state of bottleneck link probably (?) hasn’t changed much
- after cutting rate/window in half on loss, initially ramp to to Wmax faster, but then

approach Wmaxmore slowly  

Wmax  

classic TCP  

TCP CUBIC - higher  
throughput in this  
example  

Wmax/2  

## Slide 127 - TCP CUBIC

- K: point in time when TCP window size will reach Wmax

- K itself is tunable

- increase W as a function of the cube of the distance between current

time and K  

- larger increases when further away from K
- smaller increases (cautious) when nearer K

- TCP CUBIC default

in Linux, most  
popular TCP for  
popular Web  
servers  

Wmax  

TCP Reno  
TCP CUBIC  

TCP  
sending  

rate  

time  

t0  
t1  
t2  
t3  
t4  

## Slide 128 - TCP and the congested “bottleneck link”

- TCP (classic, CUBIC) increase TCP’s sending rate until packet loss occurs

at some router’s output: the bottleneck link  

source  

application  

TCP  
network  

link  
physical  

packet queue almost  
never empty, sometimes  

overflows packet (loss)  

bottleneck link (almost always busy)  

destination  

application  

TCP  
network  

link  
physical  

## Slide 129 - TCP and the congested “bottleneck link”

- TCP (classic, CUBIC) increase TCP’s sending rate until packet loss occurs

at some router’s output: the bottleneck link  

- understanding congestion: useful to focus on congested bottleneck link

insight: increasing TCP sending rate will  

not increase end-end throughout  
with congested bottleneck  

source  

application  

TCP  
network  

link  
physical  

insight: increasing TCP  

sending rate will  
increase measured RTT  

RTT  
Goal: “keep the end-end pipe just full, but not fuller”  

destination  

application  

TCP  
network  

link  
physical  

## Slide 130 - Delay-based TCP congestion control

Keeping sender-to-receiver pipe “just full enough, but no fuller”: keep  
bottleneck link busy transmitting, but avoid high delays/buffering  

RTTmeasured  

Delay-based approach:  

- RTTmin - minimum observed RTT (uncongested path)
- uncongested throughput with congestion window cwnd is cwnd/RTTmin

if measured throughput “very close” to uncongested throughput  

increase cwnd linearly /* since path not congested */  
else if measured throughput “far below” uncongested throughout  

decrease cwnd linearly  
/* since path is congested */  

# bytes sent in  
last RTT interval  

measured  
throughput =  

RTTmeasured  

## Slide 131 - Delay-based TCP congestion control

- congestion control without inducing/forcing loss
- maximizing throughput (“keeping the just pipe full… ”) while keeping

delay low (“…but not fuller”)  
- a number of deployed TCPs take a delay-based approach

- e.g., Bottleneck Bandwidth and Round-trip propagation time (BBR) deployed on

Google’s (internal) backbone network  

## Slide 132 - Explicit congestion notification (ECN)

TCP deployments often implement network-assisted congestion control:  

- two bits in IP header (ToS field) marked by network router to indicate congestion

- policy to determine marking chosen by network operator
- congestion indication carried to destination
- destination sets ECE bit on ACK segment to notify sender of congestion
- involves both IP (IP header ECN bit marking) and TCP (TCP header C,E bit marking)

TCP ACK segment  

source  

destination  

application  

application  

ECE=1  

TCP  
network  

TCP  
network  

link  
physical  

link  
physical  

ECN=10  
ECN=11  

IP datagram  

## Slide 133 - TCP fairness

Fairness goal: if K TCP sessions share same bottleneck link of  
bandwidth R, each should have average rate of R/K  

TCP connection 1  

bottleneck  

router  
capacity R  
TCP connection 2  

![Slide 133 preview](Chapter_3_v8.0_assets/slide-133.png)

## Slide 134 - Q: is TCP Fair?

Example: two competing TCP sessions:  

- additive increase gives slope of 1, as throughout increases
- multiplicative decrease decreases throughput proportionally

equal bandwidth share  

R  

loss: decrease window by factor of 2  

loss: decrease window by factor of 2  
congestion avoidance: additive increase  

congestion avoidance: additive increase  

Connection 1 throughput  

R  

Is TCP fair?  

A: Yes, under idealized  
assumptions:  

- same RTT
- fixed number of sessions

only in congestion  
avoidance  

## Slide 135 - Fairness: must all network apps be “fair”?

use TCP  

- do not want rate throttled by

congestion control  
- instead use UDP:

- send audio/video at constant rate,

tolerate packet loss  
- there is no “Internet police”

policing use of congestion  
control  

- application can open multiple

parallel connections between two  
hosts  
- web browsers do this, e.g., link of

rate R with 9 existing connections:  

- new app asks for 1 TCP, gets rate R/10
- new app asks for 11 TCPs, gets R/20

## Slide 136 - Transport layer: roadmap

- Transport-layer services
- Multiplexing and demultiplexing
- Connectionless transport: UDP
- Principles of reliable data transfer
- Connection-oriented transport: TCP
- Principles of congestion control
- TCP congestion control
- Evolution of transport-layer

functionality  

## Slide 137 - Evolving transport-layer functionality

- TCP, UDP: principal transport protocols for 40 years
- different “flavors” of TCP developed, for specific scenarios:

Scenario  
Challenges  
Long, fat pipes (large data  
transfers)  

Many packets “in flight”; loss shuts down  
pipeline  
Wireless networks  
Loss due to noisy wireless links, mobility;  
TCP treat this as congestion loss  
Long-delay links  
Extremely long RTTs  
Data center networks  
Latency sensitive  
Background traffic flows  
Low priority, “background” TCP flows  

- moving transport–layer functions to application layer, on top of UDP

- HTTP/3, QUIC

## Slide 138 - QUIC: Quick UDP Internet Connections

- application-layer protocol, on top of UDP

- increase performance of HTTP
- deployed on many Google servers, apps (Chrome, mobile YouTube app)

HTTP/2 (slimmed)  

HTTP/2  

Application  

HTTP/3  

QUIC  

TLS  

Transport  

TCP  

UDP  

IP  

Network  

IP  

HTTP/2 over QUIC over UDP  

HTTP/2 over TCP  

## Slide 139 - QUIC: Quick UDP Internet Connections

adopts approaches we’ve studied in this chapter for  
connection establishment, error control, congestion control  

- error and congestion control: “Readers familiar with TCP’s loss

detection and congestion control will find algorithms here that parallel  
well-known TCP ones.” [from QUIC specification]  
- connection establishment: reliability, congestion control,

authentication, encryption, state established in one RTT  

- multiple application-level “streams” multiplexed over single QUIC

connection  

- separate reliable data transfer, security
- common congestion control

## Slide 140 - QUIC: Connection establishment

TCP handshake  
(transport layer)  

TLS handshake  

(security)  

data  

TCP (reliability, congestion control state)  
+ TLS (authentication, crypto state)  

- 2 serial handshakes

QUIC handshake  

data  

QUIC: reliability, congestion control,  
authentication, crypto state  

- 1 handshake

## Slide 141 - QUIC: streams: parallelism, no HOL blocking

HTTP  

GET  

HTTP  

transport  
application  

GET  

HTTP  

GET  

TLS encryption  

TLS encryption  

TCP RDT  

TCP RDT  

error!  

TCP Cong. Contr.  

TCP Cong. Contr.  

(a) HTTP 1.1  

HTTP  

GET  
HTTP  

GET  
HTTP  

GET  

encrypt  
QUIC  

QUIC  

QUIC  
encrypt  
QUIC  

encrypt  
QUIC  

QUIC  

QUIC  
encrypt  
QUIC  

encrypt  

encrypt  

QUIC  

RDT  
QUIC  

QUIC  

RDT  
QUIC  

error!  

RDT  

RDT  

RDT  

RDT  

QUIC Cong. Cont.  

QUIC Cong. Cont.  

UDP  
UDP  

(b) HTTP/2 with QUIC: no HOL blocking  

## Slide 142 - Chapter 3: summary

- principles behind transport

layer services:  

- multiplexing, demultiplexing
- reliable data transfer
- flow control
- congestion control
- instantiation, implementation

on the Internet  

- UDP
- TCP

Up next:  

- leaving the network

“edge” (application,  
transport layers)  
- into the network “core”
- two network-layer

chapters:  

- data plane
- control plane

## Slide 143 - Slide 143

Additional Chapter 3 slides  

![Slide 143 preview](Chapter_3_v8.0_assets/slide-143.png)

## Slide 144 - Go-Back-N: sender extended FSM

rdt_send(data)  

if (nextseqnum < base+N) {  

sndpkt[nextseqnum] = make_pkt(nextseqnum,data,chksum)  
udt_send(sndpkt[nextseqnum])  
if (base == nextseqnum)  

start_timer  
nextseqnum++  
}  
else  

L  

refuse_data(data)  

base=1  
nextseqnum=1  

timeout  

start_timer  
udt_send(sndpkt[base])  
udt_send(sndpkt[base+1])  
…  
udt_send(sndpkt[nextseqnum-1])  

Wait  

rdt_rcv(rcvpkt)  

&& corrupt(rcvpkt)  

rdt_rcv(rcvpkt) &&  

notcorrupt(rcvpkt)  

base = getacknum(rcvpkt)+1  
If (base == nextseqnum)  

stop_timer  
else  

start_timer  

## Slide 145 - Go-Back-N: receiver extended FSM

any other event  

udt_send(sndpkt)  

rdt_rcv(rcvpkt)  

&& notcorrupt(rcvpkt)  
&& hasseqnum(rcvpkt,expectedseqnum)  

L  

Wait  

extract(rcvpkt,data)  
deliver_data(data)  
sndpkt = make_pkt(expectedseqnum,ACK,chksum)  
udt_send(sndpkt)  
expectedseqnum++  

expectedseqnum=1  
sndpkt =  

make_pkt(expectedseqnum,ACK,chksum)  

ACK-only: always send ACK for correctly-received packet with highest  

in-order seq #  

- may generate duplicate ACKs
- need only remember expectedseqnum
- out-of-order packet:

- discard (don’t buffer): no receiver buffering!
- re-ACK pkt with highest in-order seq #

## Slide 146 - TCP sender (simplified)

data received from application above  

create segment, seq. #: NextSeqNum  
pass segment to IP (i.e., “send”)  
NextSeqNum = NextSeqNum + length(data)  
if (timer currently not running)  

L  

start timer  

wait  

NextSeqNum = InitialSeqNum  
SendBase = InitialSeqNum  

for  
event  

timeout  

retransmit not-yet-acked segment  

with smallest seq. #  
start timer  

ACK received, with ACK field value y  

if (y > SendBase) {  

SendBase = y  
/* SendBase–1: last cumulatively ACKed byte */  
if (there are currently not-yet-acked segments)  

start timer  
else stop timer  
}  

## Slide 147 - TCP 3-way handshake FSM

closed  

Socket connectionSocket =  

welcomeSocket.accept();  

L  

Socket clientSocket =  

newSocket("hostname","port number");  

SYN(x)  

SYN(seq=x)  

SYNACK(seq=y,ACKnum=x+1)  
create new socket for communication  

back to client  

listen  

SYN  

SYN  

sent  

rcvd  

SYNACK(seq=y,ACKnum=x+1)  

ESTAB  

ACK(ACKnum=y+1)  
ACK(ACKnum=y+1)  

L  

## Slide 148 - TCP throughput

- avg. TCP throughput as function of window size, RTT?

- ignore slow start, assume there is always data to send
- W: window size (measured in bytes) where loss occurs

- avg. window size (# in-flight bytes) is ¾ W
- avg. throughput is 3/4W per RTT

avg TCP throughput = 3  

W  
RTT  
bytes/sec  

4  

W  

W/2  

## Slide 149 - TCP over “long, fat pipes”

- example: 1500-byte segments, 100ms RTT, want 10 Gbps throughput
- requires W = 83,333 in-flight segments
- throughput in terms of segment loss probability, L [Mathis 1997]:

➜to achieve 10 Gbps throughput, need a loss rate of L = 2·10-10 – a  

very small loss rate!  
- versions of TCP for long, high-speed scenarios

TCP throughput = 1.22 . MSS  

RTT  
L
