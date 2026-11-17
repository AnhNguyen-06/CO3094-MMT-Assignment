#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the LICENSE. Please see the LICENSE
# file that should have been included as part of this package.
#
# StreapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
StreapRous Raw Connection Library
A library for handling TCP connections with raw sockets.
Based on raw_connection_server.py implementation.
Provides connection management, send/receive functionality using raw sockets.
"""

import socket
import struct
import sys
import threading
import time
import queue
import secrets
from collections import namedtuple
import netifaces
from .streaprous_congestion_control import CubicController

# Import streaprout packet dispatcher functions
from .streaprous_packet_dispatcher import (
    start_packet_dispatcher,
    stop_packet_dispatcher,
    get_packet_queue,
    get_ack_queue,
    remove_packet_queue,
    _SYN_KEY,
)


# Connection structure 
# This structure holds connection and its state information
conn_struct = namedtuple('conn_struct', [
    'client_ip',
    'client_port',
    'server_ip',
    'server_port',
    'state',
    'server_seq',
    'client_seq',
    'expected_final_ack',
    'last_activity',
    # Per-connection transport state. Mutable buffers are initialized per
    # connection by the factory below, never shared as namedtuple defaults.
    'send_base', 'next_seq_num', 'rcv_buffer',
    'rcv_buffer_size', 'last_byte_read', 'peer_rwnd',
    'cwnd', 'ssthresh', 'ca_state', 'unacked', 'sender_state',
    'peer_window_seq', 'peer_window_ack'
], defaults=(None,) * 11)


def new_connection(**fields):
    """Create a connection record with independent per-connection buffers."""
    client_seq = fields.get('client_seq', None)
    server_seq = fields.get('server_seq', None)
    fields.setdefault('send_base', server_seq)
    fields.setdefault('next_seq_num', server_seq)
    fields.setdefault('rcv_buffer', {})
    fields.setdefault('rcv_buffer_size', 65536)
    fields.setdefault('last_byte_read', ((client_seq - 1) & M32) if client_seq is not None else None)
    fields.setdefault('peer_rwnd', 65535)
    fields.setdefault('cwnd', MSS)
    fields.setdefault('ssthresh', 65536)  # Group policy: 64 KiB initial threshold (slide FSM example)
    fields.setdefault('ca_state', 'SLOW_START')
    fields.setdefault('sender_state', SenderState())
    fields.setdefault('unacked', {})
    fields.setdefault('peer_window_seq', None)
    fields.setdefault('peer_window_ack', None)
    return conn_struct(**fields)


# Global table to manage multiple connection
# The mapping include {key: value} as { (client_ip, client_port): conn_struct }
connections = {}
connections_lock = threading.Lock()

# The transport receiver runs independently of application reads (Slides 90-93).
# An Event wakes run_conn_recv() when the receiver buffers data or closes.
_receive_workers = {}
_receive_events = {}
_receive_workers_lock = threading.Lock()

# Default raw port listener
DEFAULT_LISTEN_IP = "0.0.0.0"
DEFAULT_LISTEN_PORT = 22239
DEFAULT_INTERFACE_NAME = "lo0"

# ---------------------------------------------------------------------------
# Reliability helpers
# ---------------------------------------------------------------------------
# For IPv4 with the project's MTU=1500 B and base 20-byte IP/TCP headers.
# TCP options reduce effective payload size, so this is the option-free MSS.
MSS = 1460
M32 = 0xFFFFFFFF

def seq_diff(a, b):
    """a - b in modulo 2^32 arithmetic, returned as a signed number (handles sequence number wraparound)."""
    d = (a - b) & M32
    return d - (M32 + 1) if d >= 0x80000000 else d

def classify_segment(expected_seq, seq, length):
    """Classify a segment relative to the next expected byte."""
    d = seq_diff(seq, expected_seq)
    if d == 0:
        return "in_order"
    if d < 0 and d + length <= 0:
        return "duplicate"          # the whole segment was already received
    return "gap_or_overlap"         # there is a gap or overlap

def split_into_segments(payload, mss=MSS):
    return [payload[i:i + mss] for i in range(0, len(payload), mss)]

# --- RTT / RTO estimation and retransmission ---
ALPHA = 0.125       # weight of the new sample in EstimatedRTT
BETA = 0.25         # weight of the new sample in DevRTT
INITIAL_RTO = 1.0   # seconds, used when no RTT samples are available
MIN_RTO = 0.2       # seconds, lower bound (RTT in LAN networks is very small)
MAX_RTO = 10.0      # seconds, upper bound
MAX_RETRIES = 5     # maximum number of consecutive retransmissions before giving up

class RttEstimator:
    """Calculate EstimatedRTT, DevRTT and RTO from RTT samples (in seconds)."""
    def __init__(self):
        self.est = None
        self.dev = None
        self.rto = INITIAL_RTO

    def update(self, sample):
        if self.est is None:                   # first sample
            self.est = sample
            self.dev = sample / 2
        else:
            self.dev = (1 - BETA) * self.dev + BETA * abs(sample - self.est)
            self.est = (1 - ALPHA) * self.est + ALPHA * sample
        self.rto = min(max(self.est + 4 * self.dev, MIN_RTO), MAX_RTO)


class SenderState:
    """Reliability state owned by one connection, across ACK waits and sends.

    Slide 81-88: RTT estimator, timer for oldest unACKed data, duplicate ACKs.
    No congestion window algorithm is implemented by this state container.
    """
    def __init__(self):
        self.rtt = RttEstimator()
        self.rto = self.rtt.rto
        self.deadline = None
        self.retries = 0
        self.dup_count = 0
        self.probe_deadline = None
        # Serialize application sends; receiver uses its own transport thread.
        self.send_lock = threading.Lock()
        self.cc = CubicController(MSS)
        # Probe sequence bytes are excluded from ACK-based cwnd growth.
        self.probe_bytes = set()
        self.recover = None       # exclusive end of flight at fast recovery entry
        self.recovery_guard = None  # prevents repeated reductions for old flight
        self.partial_ack_seen = False
        # Active open only: (peer SYN sequence, ACK of our SYN), for a lost
        # final ACK. This is handshake identity, not another receive cursor.
        self.handshake_ack = None


def register_keep_port_alive(listen_ip="0.0.0.0", listen_port=22239, retry_interval=10):
    """
    Periodically register and maintain TCP port.
    Retry registration whenever binding/listening fails.
    Never accept incoming connections.
    
    Args:
        listen_ip: IP address to bind to (default: "0.0.0.0")
        listen_port: Port to bind to (default: 22239)
        retry_interval: Seconds to wait before retrying after failure (default: 10)
    
    Returns:
        threading.Thread: The background thread running the port keep-alive
    """
    def _keep_alive():
        print(f"[Streap_raw]  Start port keep-alive thread for {listen_ip}:{listen_port}")
        attempt = 0
        while True:
            attempt += 1
            standard_sock = None

            try:
                print(f"[Streap_raw] register_keep_port_alive: Attempt #{attempt} - Create socket...")
                standard_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                standard_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                print(f"[Streap_raw] register_keep_port_alive: Bind to {listen_ip}:{listen_port}...")
                standard_sock.bind((listen_ip, listen_port))
                
                print(f"[Streap_raw] register_keep_port_alive: Listen on port {listen_port}...")
                standard_sock.listen(0)  # No backlog, we won't accept connections
                print(f"[Streap_raw] register_keep_port_alive: Done port {listen_port} registration.")

                # Keep socket alive until an error occurs.
                while True:
                    time.sleep(3600)
            except Exception as e:
                print(f"[Streap_raw] register_keep_port_alive: Fail port registration with error {e}")
            finally:
                if standard_sock:
                    print(f"[Streap_raw] register_keep_port_alive: Close socket...")
                    standard_sock.close()

            print(f"[Streap_raw] register_keep_port_alive: Retry port registration in {retry_interval}s... (attempt #{attempt + 1})")
            time.sleep(retry_interval)
    
    print(f"[Streap_raw] register_keep_port_alive: Starting background thread for port {listen_port}")
    thread = threading.Thread(target=_keep_alive, daemon=True, name=f"port-keep-alive-{listen_port}")
    thread.start()
    print(f"[Streap_raw] register_keep_port_alive: Thread started (name={thread.name})")
    return thread


def checksum(msg):
    """Calculates a checksum and returns computed values.

    Args:
         msg message data
    """
    if len(msg) % 2 == 1:
        msg += b'\x00'
    s = 0
    for i in range(0, len(msg), 2):
        w = struct.unpack('!H', msg[i:i+2])[0]
        s += w
    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)
    return ~s & 0xffff

def verify_tcp_checksum(packet):
    """Return True if the TCP checksum of a received IP packet is valid."""
    # Check minimum len of packet and ensure the packet is of IPv4
    if len(packet) < 20 or packet[0] >> 4 != 4:
        return False
    ihl = (packet[0] & 0x0F) * 4
    total = struct.unpack('!H', packet[2:4])[0]
    if ihl < 20 or total < ihl + 20 or total > len(packet):
        return False
    tcp = packet[ihl:total]
    pseudo = (packet[12:16] + packet[16:20] +
              struct.pack('!BBH', 0, packet[9], len(tcp)))
    return packet[9] == socket.IPPROTO_TCP and checksum(pseudo + tcp) == 0


def build_tcp_packet(src_ip, dest_ip, src_port, dst_port, seq, ack_seq, syn=0, ack=0, fin=0, window=65535):
    """Stitches a structurally flawless 20-byte TCP header.

    Args:
         src_ip    Source IP address
         dest_ip   Destination IP address
         src_port  Source port
         dst_port  Destination port
         seq       Sequence number
         ack_seq   ACK for sequence
         syn=0     SYN flag
         ack=0     ACK flag
         fin=0     FIN flag
         window    Advertised receive window (Flow Control, Slide 94-95)
    """
    flags = (ack << 4) + (syn << 1) + fin
    offset_res = (5 << 4) + 0  # 20 bytes data offset (5 * 4)
    window = min(max(int(window), 0), 65535) # 16-bit window constraint
    urg_ptr = 0
    draft_checksum = 0

    # Build a draft (20 byte) header with no checksum
    tcp_header_temp = struct.pack('!HHLLBBHHH',
        src_port, dst_port, seq, ack_seq,
        offset_res, flags, window, draft_checksum, urg_ptr
    )
    
    # Build addressing-header
    address_header = struct.pack('!4s4sBBH',
        socket.inet_aton(src_ip), socket.inet_aton(dest_ip),
        0, socket.IPPROTO_TCP, len(tcp_header_temp)
    )
    
    # Calculate mathematical checksum integer
    tcp_checksum = checksum(address_header+ tcp_header_temp)
    
    # Build the final TCP packet
    tcp_header = struct.pack('!HHLLBBHHH',
        src_port, dst_port, seq, ack_seq,
        offset_res, flags, window, tcp_checksum, urg_ptr
    )
    
    return tcp_header


def build_ip_header(src_ip, dest_ip, protocol, payload_len):
    """Builds a structurally flawless 20-byte IP header.

    Args:
         src_ip       Source IP address
         dest_ip      Destination IP address
         protocol     Protocol number
         payload_len  Payload length
    """
    version_ihl = (4 << 4) | 5  # Version 4, IHL 5 (20 bytes)
    tos = 0
    total_len = 20 + payload_len  # IP header + payload

    # TODO: We draft with no-fragment package
    #       Full implementation must include fragment
    #       handling function
    identification = 0x1234
    flags_fragment = 0x4000
    flags_offset = 0 
    ttl = 64
    draft_checksum = 0
    
    # Build draft header with no checksum
    ip_header_temp = struct.pack('!BBHHHBBH4s4s',
        version_ihl, tos, total_len, identification,
        flags_offset, ttl, protocol, draft_checksum,
        socket.inet_aton(src_ip), socket.inet_aton(dest_ip)
    )
    
    # Calculate the checksum
    ip_checksum = checksum(ip_header_temp)
    
    # Build the final IP header
    ip_header = struct.pack('!BBHHHBBH4s4s',
        version_ihl, tos, total_len, identification,
        flags_offset, ttl, protocol, ip_checksum,
        socket.inet_aton(src_ip), socket.inet_aton(dest_ip)
    )
    
    return ip_header

def get_current_rwnd(session):
    """Advertise free space in the one receive buffer (slides 94-95)."""
    capacity = session.rcv_buffer_size
    if capacity is None:
        capacity = 65536
    occupied = sum(len(data) for data in session.rcv_buffer.values())
    if occupied > capacity:
        raise ValueError("receive buffer exceeds its capacity")
    return min(capacity - occupied, 65535)


def merge_interval_into_rcv_buffer(rcv_buffer, new_seq, new_data, capacity, window_start):
    """Store unique unread bytes within [window_start, window_start + capacity).

    Existing bytes win on overlap. The dict stores nonoverlapping {seq: bytes}
    intervals, including both contiguous and out-of-order unread data.
    """
    if capacity < 0 or capacity >= 0x80000000:
        raise ValueError("invalid receive buffer capacity")
    cells = {}
    for start, data in rcv_buffer.items():
        for index, value in enumerate(data):
            offset = seq_diff((start + index) & M32, window_start)
            if 0 <= offset < capacity:
                cells[offset] = value
    old_count = len(cells)
    for index, value in enumerate(new_data):
        offset = seq_diff((new_seq + index) & M32, window_start)
        if 0 <= offset < capacity and (offset in cells or len(cells) < capacity):
            cells.setdefault(offset, value)

    rcv_buffer.clear()
    offsets = sorted(cells)
    if offsets:
        first = previous = offsets[0]
        chunk = bytearray([cells[first]])
        for offset in offsets[1:]:
            if offset != previous + 1:
                rcv_buffer[(window_start + first) & M32] = bytes(chunk)
                first, chunk = offset, bytearray()
            chunk.append(cells[offset])
            previous = offset
        rcv_buffer[(window_start + first) & M32] = bytes(chunk)
    return len(cells) - old_count


def read_contiguous_buffer(session, max_bytes=None):
    """Remove at most max_bytes contiguous unread bytes from rcv_buffer."""
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("max_bytes must be nonnegative")
    next_read = (session.last_byte_read + 1) & M32
    # FIN consumes a sequence number, but is never application payload.
    data_end = (session.client_seq - (session.state == "CLOSE_WAIT")) & M32
    available = seq_diff(data_end, next_read)
    count = available if max_bytes is None else min(available, max_bytes)
    if count <= 0:
        return b"", session
    data = bytearray()
    for _ in range(count):
        chunk = session.rcv_buffer.pop(next_read, None)
        if chunk is None:
            raise ValueError("missing contiguous byte in receive buffer")
        data.append(chunk[0])
        if len(chunk) > 1:
            session.rcv_buffer[(next_read + 1) & M32] = chunk[1:]
        next_read = (next_read + 1) & M32
    return bytes(data), session._replace(last_byte_read=(next_read - 1) & M32)


def send_tcp_data_segment(s, src_ip, dest_ip, src_port, dst_port, seq, ack_seq, payload, window=65535):
    """Assembles and transmits a single TCP segment containing data payload.

    Args:
         src_ip       Source IP address
         dest_ip      Destination IP address
         src_port     Source port
         dst_port     Destination port
         seq          Sequence number
         ack_seq      ACK for sequence
         payload      Payload
         window       Advertised receive window (Flow Control, Slide 94-95)
    """

    # PSH + ACK
    flags = 0x18
    offset_res = (5 << 4) + 0
    window = min(max(int(window), 0), 65535) # 16 bits
    urg_ptr = 0
    draft_checksum = 0
    
    # Build draft header with no checksum
    tcp_header_temp = struct.pack('!HHLLBBHHH',
        src_port, dst_port, seq, ack_seq,
        offset_res, flags, window, draft_checksum, urg_ptr
    )
    
    tcp_len = len(tcp_header_temp) + len(payload)
    pseudo = struct.pack('!4s4sBBH',
        socket.inet_aton(src_ip), socket.inet_aton(dest_ip),
        0, socket.IPPROTO_TCP, tcp_len
    )

    # Calculate the checksum    
    tcp_checksum = checksum(pseudo + tcp_header_temp + payload)

    # Build the full TCP packet header    
    tcp_header = struct.pack('!HHLLBBHHH',
        src_port, dst_port, seq, ack_seq,
        offset_res, flags, window, tcp_checksum, urg_ptr
    )

    # Build the full IP packet header     
    ip_header = build_ip_header(src_ip, dest_ip, socket.IPPROTO_TCP, len(tcp_header) + len(payload))

    # Build the full packet header     
    full_packet = ip_header + tcp_header + payload

    # Send packet
    print(f"[Streap_raw] send_tcp_data_segment: seq={seq}, ack_seq={ack_seq}, payload_len={len(payload)}, flags=0x{flags:02x}")
    print(f"[Streap_raw] send_tcp_data_segment: TCP header seq={seq}, ack_seq={ack_seq}, flags=0x{flags:02x}")
    s.sendto(full_packet, (dest_ip, 0))
    
    return len(payload)


def clean_expired_connections(timeout=60):
    """Background thread to clean up stale or timed-out connections.

    Args:
         timeout Time expiration for clean-up working
    """
    while True:
        time.sleep(10)
        now = time.time()
        with connections_lock:
            expired = [k for k, session in connections.items() if now - session.last_activity > timeout]
            for k in expired:
                print(f"[Streap_raw] clean_expired_connections: Session [{k[0]}:{k[1]}] Connection timed out ({timeout}s inactivity). Remove connection.")
                del connections[k]

def create_raw_socket() -> socket.socket:
    """
    Create a raw socket for TCP protocol. The raw socket requires root privileges.
    It is raw with listen all packet for incoming port.
    
    Returns:
        Raw socket object
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        # TODO: port listener need to be post-procesed later
        #       raw_socket ignore the transport protocol deatails

        print(f"[Streap_raw] Create raw socket binding for 0.0.0.0 listening")
        return sock
    except PermissionError:
        print("Error: Root privileges required (sudo).")
        sys.exit(1)
    except OSError as e:
        print(f"Error creating raw socket: {e}")
        sys.exit(1)


def get_interface_ip(interface_name: str = None) -> str:
    """
    Get the IPv4 address of a network interface.
    
    Args:
        interface_name: Network interface name (e.g., 'enp0s8', 'eth0', 'en0')
                        If None, tries to find the default route interface.
    
    Returns:
        IPv4 address string
    """
    try:
        if interface_name:
            addrs = netifaces.ifaddresses(interface_name)
            if netifaces.AF_INET in addrs:
                return addrs[netifaces.AF_INET][0]['addr']
        else:
            # Try to get default route interface
            gateways = netifaces.gateways()
            default_gateway = gateways.get('default', {}).get(netifaces.AF_INET)
            if default_gateway:
                iface = default_gateway[1]
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    return addrs[netifaces.AF_INET][0]['addr']
    except Exception:
        pass
    
    # Fallback: try to get any non-loopback IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _handshake_header(packet, local_ip, local_port, peer_ip=None, peer_port=None):
    """Validate the IPv4/TCP header and endpoint tuple before handshake state."""
    if not verify_tcp_checksum(packet):
        return None
    ihl = (packet[0] & 0x0f) * 4
    total = struct.unpack('!H', packet[2:4])[0]
    tcp = packet[ihl:total]
    header = struct.unpack('!HHLLBBHHH', tcp[:20])
    offset = (header[4] >> 4) * 4
    if offset < 20 or offset > len(tcp) or header[1] != local_port:
        return None
    if packet[16:20] != socket.inet_aton(local_ip):
        return None
    if peer_ip is not None and packet[12:16] != socket.inet_aton(peer_ip):
        return None
    if peer_port is not None and header[0] != peer_port:
        return None
    return header


def _wait_handshake(s, session, syn_packet):
    """Retransmit the same SYN/SYN-ACK; unrelated packets never reset the timer.

    Slide 101: SYN consumes one sequence number; ACK alone consumes none.
    Retry/backoff uses existing project RTO limits, independently of CUBIC.
    """
    key = (session.client_ip, session.client_port)
    q = get_packet_queue(key)
    active_open = session.state == "SYN_SENT"
    rto, retries = INITIAL_RTO, 0
    s.sendto(syn_packet, (session.client_ip, 0))
    deadline = time.monotonic() + rto
    while True:
        with connections_lock:
            current = connections.get(key)
            if current is None or current.sender_state is not session.sender_state:
                raise ConnectionError("handshake session replaced")
        left = deadline - time.monotonic()
        if left <= 0:
            if retries >= MAX_RETRIES:
                raise TimeoutError("handshake retries exhausted")
            retries += 1
            s.sendto(syn_packet, (session.client_ip, 0))
            rto = min(rto * 2, MAX_RTO)
            deadline = time.monotonic() + rto
            continue
        try:
            packet, _ = q.get(timeout=min(left, .2))
        except queue.Empty:
            continue
        # A queued packet must not mutate a replacement session after waiting.
        with connections_lock:
            current = connections.get(key)
            if current is None or current.sender_state is not session.sender_state:
                raise ConnectionError("handshake session replaced")
        header = _handshake_header(packet, session.server_ip, session.server_port,
                                   session.client_ip, session.client_port)
        if header is None:
            continue
        seq, ack, flags = header[2], header[3], header[5]
        if flags & 0x04:
            if ((active_open and flags & 0x10 and ack == session.expected_final_ack)
                    or (not active_open and seq == session.client_seq)):
                raise ConnectionRefusedError("peer reset handshake")
            continue
        if active_open:
            if flags & 0x17 == 0x12 and ack == session.expected_final_ack:
                return packet, header
        else:
            if flags & 0x17 == 0x02 and seq == ((session.client_seq - 1) & M32):
                # Duplicate SYN belongs to this pending open. Keep both ISNs;
                # resend SYN-ACK without extending its retransmission deadline.
                s.sendto(syn_packet, (session.client_ip, 0))
            elif (flags & 0x17 == 0x10 and ack == session.expected_final_ack
                    and seq == session.client_seq):
                return packet, header


def accept(s: socket.socket, listen_ip: str, listen_port: int, interface_name: str = None) -> conn_struct:
    """Accept serialized three-way handshakes with SYN-ACK retransmission."""
    start_packet_dispatcher(s, listen_port)
    syn_q = get_packet_queue(_SYN_KEY)
    while True:
        try:
            packet, _ = syn_q.get(timeout=1.0)
        except queue.Empty:
            continue
        # With wildcard listen, reply from the actual destination of this SYN.
        if len(packet) < 20:
            continue
        send_ip = socket.inet_ntoa(packet[16:20]) if listen_ip == "0.0.0.0" else listen_ip
        header = _handshake_header(packet, send_ip, listen_port)
        if header is None or header[5] & 0x17 != 0x02:
            continue
        peer_ip, peer_port = socket.inet_ntoa(packet[12:16]), header[0]
        key = (peer_ip, peer_port)
        # SYN payload / TCP Fast Open is outside the assignment's handshake.
        total = struct.unpack('!H', packet[2:4])[0]
        if total != (packet[0] & 0x0f) * 4 + (header[4] >> 4) * 4:
            continue
        isn = secrets.randbits(32)  # Chosen once per attempt, stable on retry.
        session = new_connection(client_ip=peer_ip, client_port=peer_port,
            server_ip=send_ip, server_port=listen_port, state="SYN_RCVD",
            server_seq=isn, client_seq=(header[2] + 1) & M32,
            expected_final_ack=(isn + 1) & M32, last_activity=time.time(),
            peer_rwnd=header[6])
        with connections_lock:
            if key in connections:
                continue
            connections[key] = session
        get_packet_queue(key)  # Register before sending SYN-ACK.
        tcp = build_tcp_packet(send_ip, peer_ip, listen_port, peer_port,
            seq=isn, ack_seq=session.client_seq, syn=1, ack=1,
            window=get_current_rwnd(session))
        syn_ack = build_ip_header(send_ip, peer_ip, socket.IPPROTO_TCP, len(tcp)) + tcp
        try:
            final_packet, final_header = _wait_handshake(s, session, syn_ack)
            with connections_lock:
                current = connections.get(key)
                if current is None or current.sender_state is not session.sender_state:
                    raise ConnectionError("handshake session replaced")
                session = current._replace(state="ESTABLISHED",
                    server_seq=current.expected_final_ack,
                    send_base=current.expected_final_ack, next_seq_num=current.expected_final_ack,
                    peer_rwnd=final_header[6], peer_window_seq=final_header[2],
                    peer_window_ack=final_header[3], last_activity=time.time())
                connections[key] = session
            # Hand off the consumed final segment directly: queue.put() could
            # reorder it or fail on a full queue. Receiver handles its payload
            # through the same bounded buffer/reassembly path exactly once.
            start_connection_receiver(s, session, initial_packet=final_packet)
            return session
        except (OSError, ConnectionError) as exc:
            print(f"[Streap_raw] accept: handshake failed for {key}: {exc}")
            with connections_lock:
                current = connections.get(key)
                if current is not None and current.sender_state is session.sender_state:
                    connections.pop(key)
                    remove_packet_queue(key)


def raw_connect(dest_ip: str, dest_port: int, client_port: int = None, interface_name: str = None):
    """Active open: retry SYN, validate SYN-ACK, then acknowledge the peer SYN."""
    import random
    s = create_raw_socket()
    send_ip = get_interface_ip(interface_name)
    if client_port is None:
        while True:
            candidate = random.randint(49152, 65530)
            with connections_lock:
                if not any(conn.server_port == candidate for conn in connections.values()):
                    client_port = candidate
                    break
    key = (dest_ip, dest_port)
    isn = secrets.randbits(32)
    session = new_connection(client_ip=dest_ip, client_port=dest_port,
        server_ip=send_ip, server_port=client_port, state="SYN_SENT",
        server_seq=isn, client_seq=0, expected_final_ack=(isn + 1) & M32,
        last_activity=time.time())
    with connections_lock:
        if key in connections:
            s.close()
            raise ConnectionError("peer key already in use")
        connections[key] = session
    get_packet_queue(key)
    start_packet_dispatcher(s, client_port)
    tcp = build_tcp_packet(send_ip, dest_ip, client_port, dest_port,
        seq=isn, ack_seq=0, syn=1, window=get_current_rwnd(session))
    syn = build_ip_header(send_ip, dest_ip, socket.IPPROTO_TCP, len(tcp)) + tcp
    try:
        syn_ack, header = _wait_handshake(s, session, syn)
        # SYN payload / Fast Open is not supported; never silently discard it.
        total = struct.unpack('!H', syn_ack[2:4])[0]
        if total != (syn_ack[0] & 0x0f) * 4 + (header[4] >> 4) * 4:
            raise ConnectionError("SYN payload is unsupported")
        with connections_lock:
            current = connections.get(key)
            if current is None or current.sender_state is not session.sender_state:
                raise ConnectionError("handshake session replaced")
            session = current._replace(state="ESTABLISHED", server_seq=(isn + 1) & M32,
                send_base=(isn + 1) & M32, next_seq_num=(isn + 1) & M32,
                client_seq=(header[2] + 1) & M32, last_byte_read=header[2],
                peer_rwnd=header[6], peer_window_seq=header[2], peer_window_ack=header[3],
                last_activity=time.time())
            session.sender_state.handshake_ack = (header[2], header[3])
            connections[key] = session
        tcp = build_tcp_packet(send_ip, dest_ip, client_port, dest_port,
            seq=session.server_seq, ack_seq=session.client_seq, ack=1,
            window=get_current_rwnd(session))
        s.sendto(build_ip_header(send_ip, dest_ip, socket.IPPROTO_TCP, len(tcp)) + tcp,
                 (dest_ip, 0))
        start_connection_receiver(s, session)
        return session, s
    except (OSError, ConnectionError) as exc:
        print(f"[Streap_raw] raw_connect: handshake failed for {key}: {exc}")
        owns_session = False
        with connections_lock:
            current = connections.get(key)
            if current is not None and current.sender_state is session.sender_state:
                owns_session = True
                connections.pop(key)
                remove_packet_queue(key)
        if owns_session:
            stop_packet_dispatcher(s)
            s.close()
        return None, None


def start_connection_receiver(s: socket.socket, conn_info: conn_struct, initial_packet=None):
    """Start transport-side packet processing independently of application reads.

    Buffering and ACK/window advertisement continue while the application is
    busy (Slides 90-95).
    """
    key = (conn_info.client_ip, conn_info.client_port)
    with _receive_workers_lock:
        worker = _receive_workers.get(key)
        if worker is not None and worker.is_alive() and key in _receive_events:
            return
        _receive_events[key] = threading.Event()
        worker = threading.Thread(
            target=_run_conn_receive_loop,
            args=(s, conn_info, initial_packet),
            daemon=True,
            name=f"tcp-recv-{conn_info.client_ip}-{conn_info.client_port}",
        )
        _receive_workers[key] = worker
        worker.start()


def run_conn_recv(s: socket.socket, conn_info: conn_struct, max_bytes: int = None) -> bytes:
    """Read contiguous buffered bytes for the application.

    Removing bytes advances LastByteRead and reopens receive-window capacity
    (Slides 90-95); packet processing is done by the independent receiver.
    """
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("max_bytes must be nonnegative")
    if max_bytes == 0:
        return b""
    key = (conn_info.client_ip, conn_info.client_port)
    with _receive_workers_lock:
        event = _receive_events.get(key)
    if event is None:
        start_connection_receiver(s, conn_info)
        with _receive_workers_lock:
            event = _receive_events[key]

    while True:
        with connections_lock:
            session = connections.get(key)
            if session is None:
                return b""
            if session.state == "ERROR":
                raise ConnectionError("transport receiver failed; see receiver error log")
            delivered, session = read_contiguous_buffer(session, max_bytes)
            if delivered:
                connections[key] = session
                # The ACK number is still the next contiguous byte expected;
                # the larger window advertises the space freed by the app read.
                window = get_current_rwnd(session)
                ack_packet = build_tcp_packet(
                    session.server_ip, session.client_ip,
                    session.server_port, session.client_port,
                    seq=session.server_seq, ack_seq=session.client_seq,
                    ack=1, window=window,
                )
                ip_header = build_ip_header(
                    session.server_ip, session.client_ip,
                    socket.IPPROTO_TCP, len(ack_packet),
                )
                closed = False
            else:
                ack_packet = None
                closed = session.state in ("CLOSED", "RESET", "CLOSE_WAIT")
        if ack_packet is not None:
            s.sendto(ip_header + ack_packet, (session.client_ip, 0))
            return delivered
        if closed:
            return b""
        # Recheck periodically so an event arriving between the buffer check
        # and wait cannot leave the application asleep indefinitely.
        event.wait(0.1)
        event.clear()


def _run_conn_receive_loop(s: socket.socket, conn_info: conn_struct, initial_packet=None) -> None:
    """
    Transport-side receive loop: validate, buffer, and ACK packets continuously.
    It deliberately does not remove payload bytes; only the application read
    path advances LastByteRead and frees receive-buffer space (Slides 90-95).
    
    Args:
        s: raw socket
        conn_info: conn_struct tuple for the connection
    """
    client_ip = conn_info.client_ip
    client_port = conn_info.client_port
    client_key = (client_ip, client_port)
    listen_ip = conn_info.server_ip
    listen_port = conn_info.server_port
    receive_event = _receive_events[client_key]
    # Get the packet queue for this connection from the dispatcher
    packet_queue = get_packet_queue(client_key)
    
    print(f"[Streap_raw] run_conn_recv: Starting receive loop for {client_ip}:{client_port} (waiting for data...)")
    
    # Remember an out-of-order FIN until all preceding bytes arrive. This is
    # transport bookkeeping, not an additional payload receive buffer.
    pending_fin = None
    try:
        while True:
            with connections_lock:
                if client_key not in connections or _receive_events.get(client_key) is not receive_event:
                    return
            # Get packet from the dispatcher queue instead of reading directly from socket
            if initial_packet is not None:
                packet, initial_packet = initial_packet, None
            else:
                try:
                    packet, addr = packet_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
            with connections_lock:
                session = connections.get(client_key)
                if (session is None or session.sender_state is not conn_info.sender_state
                        or _receive_events.get(client_key) is not receive_event):
                    return

            # Every time received a packet, verify checksum
            if not verify_tcp_checksum(packet):
                continue
            # IP padding is not TCP application data (including a final ACK
            # handed off from the handshake).
            packet = packet[:struct.unpack('!H', packet[2:4])[0]]

            # Extract IP Header Length
            ihl = (packet[0] & 0x0F) * 4
            tcp_packet = packet[ihl:]
            
            if len(tcp_packet) < 20:
                continue

            # Unpack the received TCP header
            tcph = struct.unpack('!HHLLBBHHH', tcp_packet[:20])
            src_port, dest_port, pkt_seq, pkt_ack, flags, window_size = (
                tcph[0],
                tcph[1],
                tcph[2],
                tcph[3],
                tcph[5],
                tcph[6],
            )

            # Bypass non-listen port
            if dest_port != listen_port:
                continue

            # Check if this packet is for our connection
            if (src_port != client_port
                    or packet[12:16] != socket.inet_aton(client_ip)
                    or packet[16:20] != socket.inet_aton(listen_ip)):
                continue
            
            syn_flag = (flags & 0x02) >> 1
            ack_flag = (flags & 0x10) >> 4
            psh_flag = (flags & 0x08) >> 3
            fin_flag = (flags & 0x01)
            rst_flag = (flags & 0x04) >> 2

            print(f"[Streap_raw] run_conn_recv: Received packet from {client_ip}:{client_port} (SYN={syn_flag}, ACK={ack_flag}, PSH={psh_flag}, FIN={fin_flag}, RST={rst_flag}, Seq={pkt_seq}, Ack={pkt_ack}, Win={window_size})")

            tcp_header_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
            if tcp_header_len < 20 or tcp_header_len > len(tcp_packet):
                continue
            if rst_flag:
                with connections_lock:
                    session = connections.get(client_key)
                    if session is not None:
                        connections[client_key] = session._replace(state="RESET")
                return
            if syn_flag:
                # Lost final ACK: the server retransmits its original SYN-ACK.
                # Do not consume SYN again or overwrite current data cursors.
                with connections_lock:
                    session = connections.get(client_key)
                    if (session is None or session.sender_state is not conn_info.sender_state
                            or _receive_events.get(client_key) is not receive_event):
                        return
                    if (session.state != "ESTABLISHED" or flags & 0x17 != 0x12
                            or session.sender_state.handshake_ack != (pkt_seq, pkt_ack)
                            or len(tcp_packet) != tcp_header_len):
                        continue
                    response = build_tcp_packet(listen_ip, client_ip, listen_port, client_port,
                        seq=session.server_seq, ack_seq=session.client_seq, ack=1,
                        window=get_current_rwnd(session))
                s.sendto(build_ip_header(listen_ip, client_ip, socket.IPPROTO_TCP,
                         len(response)) + response, (client_ip, 0))
                continue
            if not ack_flag:
                continue
            with connections_lock:
                session = connections.get(client_key)
                if session is None:
                    return
                # Always replace the latest record under the same lock. App
                # reads and sender updates must never be overwritten by a copy.
                session = session._replace(last_activity=time.time())
                connections[client_key] = session

            # Store both contiguous and out-of-order unread bytes in one buffer.
            tcp_header_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
            has_data = len(tcp_packet) > tcp_header_len
            if has_data or fin_flag:
                app_payload = tcp_packet[tcp_header_len:]
                with connections_lock:
                    session = connections.get(client_key)
                    if session is None:
                        continue
                    window_start = (session.last_byte_read + 1) & M32
                    if session.state == "CLOSE_WAIT":
                        app_payload = b""
                    elif fin_flag and pending_fin is None:
                        fin_seq = (pkt_seq + len(app_payload)) & M32
                        # FIN must lie in the receive window and cannot precede
                        # data already acknowledged (TCP ordered byte stream).
                        if (seq_diff(fin_seq, session.client_seq) >= 0
                                and 0 <= seq_diff(fin_seq, window_start) < session.rcv_buffer_size):
                            pending_fin = fin_seq
                            # Previously buffered out-of-order bytes beyond FIN
                            # are outside the completed stream; never deliver them.
                            for start, data in list(session.rcv_buffer.items()):
                                count = max(0, seq_diff(fin_seq, start))
                                if count == 0:
                                    del session.rcv_buffer[start]
                                elif count < len(data):
                                    session.rcv_buffer[start] = data[:count]
                    if pending_fin is not None:
                        app_payload = app_payload[:max(0, seq_diff(pending_fin, pkt_seq))]
                    merge_interval_into_rcv_buffer(
                        session.rcv_buffer, pkt_seq, app_payload,
                        session.rcv_buffer_size, window_start
                    )
                    # TCP ACKs only the contiguous prefix, even when later bytes
                    # have already arrived and remain in the receive buffer.
                    next_expected = session.client_seq
                    while True:
                        covering = next((
                            (start, data) for start, data in session.rcv_buffer.items()
                            if 0 <= seq_diff(next_expected, start) < len(data)
                        ), None)
                        if covering is None:
                            break
                        start, data = covering
                        next_expected = (start + len(data)) & M32
                    if pending_fin is not None and seq_diff(next_expected, pending_fin) >= 0:
                        # FIN is acknowledged only after the missing prefix is
                        # present. Preserve unread data until the app drains it.
                        next_expected = (pending_fin + 1) & M32
                        session = session._replace(state="CLOSE_WAIT")
                        pending_fin = None
                    session = session._replace(client_seq=next_expected, last_activity=time.time())
                    connections[client_key] = session
                    # Buffer occupancy includes unread in-order and out-of-order
                    # bytes. ACK remains cumulative (next_expected); rwnd reports
                    # free space in this receive buffer (Slides 78-80, 94-95).
                    window = get_current_rwnd(session)
                    ack_packet = build_tcp_packet(
                        listen_ip, client_ip, listen_port, client_port,
                        seq=session.server_seq, ack_seq=next_expected, ack=1, window=window
                    )
                    ip_header = build_ip_header(listen_ip, client_ip, socket.IPPROTO_TCP, len(ack_packet))
                s.sendto(ip_header + ack_packet, (client_ip, 0))
                receive_event.set()
                continue

            # ACK processing for sent data belongs to wait_for_ack(), which
            # validates ACK numbers before advancing send_base. A peer ACK must
            # never overwrite server_seq (the next sequence to send).

    except Exception as e:
        print(f"[Streap_raw] Transport receiver failed for {client_key}: {e}")
        with connections_lock:
            session = connections.get(client_key)
            if session is not None and _receive_events.get(client_key) is receive_event:
                connections[client_key] = session._replace(state="ERROR")
    finally:
        receive_event.set()
        with _receive_workers_lock:
            if _receive_workers.get(client_key) is threading.current_thread():
                _receive_workers.pop(client_key, None)


def wait_for_ack(s, conn_info, start, target, unacked, rtt, ack_seq, return_on_update=False, probe_data=b""):
    """Wait for the client to ACK up to the last byte of the response, and retransmit lost segments.

    Returns (last_byte_acked, all_acked).
    last_byte_acked = the LAST byte the client has acknowledged (slide 3-122) = ACK number - 1.
    `start` = first byte of the response, `target` = the byte right after the last byte.
    Retransmits the OLDEST unacknowledged segment when:
      - the RTO timer expires (RTO doubles after each expiry), or
      - exactly 3 consecutive duplicate ACKs arrive (fast retransmit).
    Gives up after MAX_RETRIES consecutive retransmissions without progress.
    return_on_update lets the existing sender refill its sliding window after
    a new ACK or window update, without waiting for all outstanding data.
    """
    last_byte_acked = (start - 1) & M32          # no byte acknowledged yet
    last_byte_sent = (target - 1) & M32          # last byte of the response
    if seq_diff(start, target) >= 0 and not return_on_update:
        return last_byte_acked, True

    client_key = (conn_info.client_ip, conn_info.client_port)
    packet_queue = get_ack_queue(client_key)
    with connections_lock:
        state = connections[client_key].sender_state
    # Retain the public helper signature; the connection owns the estimator.
    rtt = state.rtt
    if unacked and state.deadline is None:
        state.deadline = time.monotonic() + state.rto
    if state.probe_deadline is None:
        state.probe_deadline = time.monotonic() + 1.0

    def retransmit_oldest(reason):
        seg_seq = min(unacked, key=lambda seq: seq_diff(seq, start))
        seg_chunk = unacked[seg_seq][0]
        with connections_lock:
            session = connections[client_key]
            cur_rwnd = get_current_rwnd(session)
        send_tcp_data_segment(
            s, conn_info.server_ip, conn_info.client_ip,
            conn_info.server_port, conn_info.client_port,
            seq=seg_seq, ack_seq=session.client_seq, payload=seg_chunk,
            window=cur_rwnd
        )
        unacked[seg_seq] = (seg_chunk, time.monotonic(), True)   # True = already retransmitted
        print(f"[Streap_raw] wait_for_ack: RETRANSMIT seq={seg_seq} ({len(seg_chunk)} bytes), "
              f"reason: {reason}, RTO={state.rto*1000:.0f} ms, attempt {state.retries}")

    while True:
        with connections_lock:
            session = connections.get(client_key)
            if (session is None or session.sender_state is not state
                    or session.state in ("CLOSED", "RESET", "ERROR")):
                raise ConnectionError("connection closed while waiting for ACK/window")
            zero_window = session.peer_rwnd == 0
            # RFC 9438 5.8: receiver-limited time is excluded even before
            # the first persist probe. An open window alone cannot resume CA.
            state.cc.update_clock(time.monotonic(),
                session.peer_rwnd >= session.cwnd)
        if zero_window:
            if time.monotonic() >= state.probe_deadline:
                if unacked:
                    probe_seq = min(unacked, key=lambda seq: seq_diff(seq, start))
                    chunk, sent_at, _ = unacked[probe_seq]
                    probe_byte = chunk[:1]
                    unacked[probe_seq] = (chunk, sent_at, True)
                elif probe_data:
                    probe_seq, probe_byte = target, probe_data[:1]
                    unacked[probe_seq] = (probe_byte, time.monotonic(), True)
                    target = (target + 1) & M32
                    last_byte_sent = (target - 1) & M32
                    with connections_lock:
                        connections[client_key] = connections[client_key]._replace(
                            next_seq_num=target, server_seq=target)
                else:
                    probe_byte = b""
                if probe_byte:
                    state.probe_bytes.add(probe_seq)
                    with connections_lock:
                        session = connections[client_key]
                        probe_window = get_current_rwnd(session)
                    send_tcp_data_segment(
                        s, conn_info.server_ip, conn_info.client_ip,
                        conn_info.server_port, conn_info.client_port,
                        seq=probe_seq, ack_seq=session.client_seq,
                        payload=probe_byte, window=probe_window)
                state.probe_deadline = time.monotonic() + 1.0
            # Persist waits do not exhaust data-loss retries or trigger fast
            # retransmit. Poll close/error state even when the peer is silent.
            left = min(0.2, max(0.001, state.probe_deadline - time.monotonic()))
            # Suspend data-loss timer during persist; reopening restarts it.
            state.deadline = None
        else:
            if unacked and state.deadline is None:
                state.deadline = time.monotonic() + state.rto
            left = min(0.2, state.deadline - time.monotonic()) if unacked else 0.2
        if not unacked and not zero_window:
            left = 0.2
        if left <= 0:                            # RTO expired
            if state.retries >= MAX_RETRIES:
                print(f"[Streap_raw] wait_for_ack: GIVE UP after {state.retries} retransmissions, last_byte_acked={last_byte_acked}")
                if return_on_update:
                    raise TimeoutError("peer did not acknowledge outstanding data")
                return last_byte_acked, False
            with connections_lock:
                session = connections[client_key]
                if state.retries == 0:
                    new_cwnd, threshold = state.cc.on_loss(
                        session.cwnd, seq_diff(target, (last_byte_acked + 1) & M32),
                        time.monotonic(), timeout=True)
                else:
                    # Same segment timing out again: keep threshold/backoff.
                    new_cwnd, threshold = state.cc.mss, session.ssthresh
                connections[client_key] = session._replace(
                    cwnd=new_cwnd, ssthresh=threshold, ca_state="SLOW_START")
                state.recover = None
                state.recovery_guard = target
                state.partial_ack_seen = False
            print(f"[CUBIC] event=RTO connection={client_key} "
                  f"cwnd={session.cwnd:.3f}->{new_cwnd:.3f} "
                  f"ssthresh={threshold:.3f} phase=SLOW_START")
            state.retries += 1
            retransmit_oldest("RTO expired")     # the log shows the RTO that just expired
            state.rto = min(state.rto * 2, MAX_RTO)          # next wait is twice as long (exponential backoff)
            state.dup_count = 0
            state.deadline = time.monotonic() + state.rto
            continue
        try:
            packet, addr = packet_queue.get(timeout=left)
        except queue.Empty:
            continue

        # Invalid checksum packets are not accepted
        if not verify_tcp_checksum(packet):
            continue

        ihl = (packet[0] & 0x0F) * 4
        tcp_packet = packet[ihl:]
        if len(tcp_packet) < 20:
            continue
        tcph = struct.unpack('!HHLLBBHHH', tcp_packet[:20])
        src_port, dest_port, pkt_seq, pkt_ack, flags, window_size = (
            tcph[0],
            tcph[1],
            tcph[2],
            tcph[3],
            tcph[5],
            tcph[6],
        )
        if src_port != conn_info.client_port or dest_port != conn_info.server_port:
            continue
        if not (flags & 0x10):                   # no ACK flag
            continue
        if flags & 0x07:                        # no SYN, RST or FIN as data ACK
            continue
        if packet[12:16] != socket.inet_aton(conn_info.client_ip) or packet[16:20] != socket.inet_aton(conn_info.server_ip):
            continue
        if seq_diff(pkt_ack, (last_byte_acked + 1) & M32) < 0 or seq_diff(pkt_ack, target) > 0:
            continue                            # ACK cannot acknowledge unsent bytes

        # Flow Control: Update peer_rwnd from advertised window in TCP header (Slide 94-95)
        with connections_lock:
            client_key = (conn_info.client_ip, conn_info.client_port)
            if client_key not in connections:
                return last_byte_acked, False
            session = connections[client_key]
            old_window = session.peer_rwnd
            # Window freshness bookkeeping follows TCP's ordered SEQ/ACK
            # update rule; these fields are sender metadata, not payload buffers.
            fresh_window = (session.peer_window_seq is None
                or seq_diff(pkt_seq, session.peer_window_seq) > 0
                or (pkt_seq == session.peer_window_seq
                    and seq_diff(pkt_ack, session.peer_window_ack) >= 0))
            if fresh_window:
                connections[client_key] = session._replace(
                    peer_rwnd=window_size, peer_window_seq=pkt_seq,
                    peer_window_ack=pkt_ack)
            else:
                window_size = old_window
            state.cc.update_clock(time.monotonic(),
                window_size >= session.cwnd)
            if old_window != 0 and window_size == 0:
                state.probe_deadline = time.monotonic() + 1.0

        if pkt_ack == ((last_byte_acked + 1) & M32) and not fresh_window:
            continue  # stale SEQ/window metadata is not a fresh loss indication
        new_last = (pkt_ack - 1) & M32           # ACK number = next byte expected, so last byte received = ACK - 1
        if seq_diff(new_last, last_byte_acked) > 0:          # NEW ACK: advance
            ack_start = (last_byte_acked + 1) & M32
            newly_acked = seq_diff(pkt_ack, ack_start)
            probe_acked = {seq for seq in state.probe_bytes
                if 0 <= seq_diff(seq, ack_start) < newly_acked}
            state.probe_bytes.difference_update(probe_acked)
            with connections_lock:
                session = connections[client_key]
                cwnd = session.cwnd
                inflight_before_ack = seq_diff(target, ack_start)
                eligible = (not zero_window and min(old_window, window_size) >= cwnd
                    and inflight_before_ack >= int(cwnd)
                    and not probe_acked and state.retries == 0)
            last_byte_acked = new_last
            newest_sent_at = None
            acknowledged_retransmission = False
            for seg_seq in list(unacked):
                seg_chunk, seg_sent_at, was_retx = unacked[seg_seq]
                if was_retx and seq_diff(pkt_ack, seg_seq) > 0:
                    acknowledged_retransmission = True
                seg_last_byte = (seg_seq + len(seg_chunk) - 1) & M32     # last byte of the segment
                if seq_diff(last_byte_acked, seg_last_byte) >= 0:
                    del unacked[seg_seq]
                    if not was_retx:             # Karn: do not sample RTT from retransmitted segments
                        newest_sent_at = seg_sent_at
                elif seq_diff(pkt_ack, seg_seq) > 0:
                    # A cumulative ACK may cover only a prefix of a segment.
                    del unacked[seg_seq]
                    unacked[pkt_ack] = (seg_chunk[seq_diff(pkt_ack, seg_seq):], seg_sent_at, was_retx)
            # An ACK covering any retransmitted bytes is ambiguous (Karn),
            # even if it cumulatively covers some original transmissions too.
            if acknowledged_retransmission:
                newest_sent_at = None
            if newest_sent_at is not None:
                sample = time.monotonic() - newest_sent_at
                rtt.update(sample)
                print(f"[Streap_raw] wait_for_ack: RTT sample={sample*1000:.1f} ms, "
                      f"Est={rtt.est*1000:.1f} ms, Dev={rtt.dev*1000:.1f} ms, RTO={rtt.rto*1000:.1f} ms")
            print(f"[Streap_raw] wait_for_ack: ACK={pkt_ack} (last_byte_acked={last_byte_acked}, "
                  f"{seq_diff(last_byte_sent, last_byte_acked)} bytes remaining, {len(unacked)} unacked segments)")
            # Commit progress before any return_on_update exit. Window-only
            # updates below must not restart this timer or clear loss retries.
            state.retries = 0
            state.dup_count = 0
            if newest_sent_at is not None:
                state.rto = rtt.rto
            partial_recovery = (state.recover is not None
                and seq_diff(pkt_ack, state.recover) < 0)
            if not partial_recovery or not state.partial_ack_seen:
                state.deadline = time.monotonic() + state.rto if unacked else None
            with connections_lock:
                session = connections[client_key]
                if state.recover is not None:
                    if partial_recovery:
                        # NewReno (no SACK): one repair per partial ACK; do not
                        # reduce ssthresh/W_max again within this recovery flight.
                        updated_cwnd = max(state.cc.mss,
                            session.cwnd - newly_acked
                            + (state.cc.mss if newly_acked >= state.cc.mss else 0))
                        phase = "FAST_RECOVERY"
                        state.partial_ack_seen = True
                    else:
                        updated_cwnd = session.ssthresh
                        state.recover = None
                        phase = "CONGESTION_AVOIDANCE"
                    state.cc.pause(time.monotonic())
                else:
                    updated_cwnd = state.cc.on_ack(
                        session.cwnd, session.ssthresh, newly_acked,
                        rtt.est, time.monotonic(), eligible and not acknowledged_retransmission)
                    phase = ("SLOW_START" if updated_cwnd < session.ssthresh
                             else "CONGESTION_AVOIDANCE")
                connections[client_key] = session._replace(
                    send_base=pkt_ack, cwnd=updated_cwnd, ca_state=phase)
                if not unacked:
                    state.cc.pause(time.monotonic())
            print(f"[CUBIC] event=ACK connection={client_key} ack={pkt_ack} "
                  f"new_bytes={newly_acked} cwnd={session.cwnd:.3f}->{updated_cwnd:.3f} "
                  f"ssthresh={session.ssthresh:.3f} phase={phase}")
            if partial_recovery and unacked:
                retransmit_oldest("partial recovery ACK")
            if seq_diff(last_byte_acked, last_byte_sent) >= 0:
                return last_byte_acked, True
            if return_on_update:
                return last_byte_acked, False

        elif new_last == last_byte_acked and window_size != old_window:
            # An unchanged ACK number can advertise newly available space.
            # A window update is not counted as a duplicate loss indication.
            if return_on_update:
                return last_byte_acked, not unacked
        elif new_last == last_byte_acked and unacked and not zero_window:        # DUPLICATE ACK
            tcp_hdr_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
            pure_ack = len(tcp_packet) == tcp_hdr_len and not (flags & 0x07)   # no SYN/RST/FIN, no data
            if pure_ack:
                state.dup_count += 1
                print(f"[Streap_raw] wait_for_ack: duplicate ACK #{state.dup_count} (ack={pkt_ack})")
                if state.recover is not None:
                    with connections_lock:
                        session = connections[client_key]
                        connections[client_key] = session._replace(
                            cwnd=session.cwnd + state.cc.mss)
                    if return_on_update:
                        return last_byte_acked, False
                elif (state.dup_count == 3 and
                      (state.recovery_guard is None or
                       seq_diff((last_byte_acked + 1) & M32, state.recovery_guard) > 0)):
                    with connections_lock:
                        session = connections[client_key]
                        reduced, threshold = state.cc.on_loss(
                            session.cwnd, seq_diff(target, (last_byte_acked + 1) & M32),
                            time.monotonic())
                        connections[client_key] = session._replace(
                            cwnd=reduced + 3 * state.cc.mss,
                            ssthresh=threshold, ca_state="FAST_RECOVERY")
                        state.recover = state.recovery_guard = target
                        state.partial_ack_seen = False
                    print(f"[CUBIC] event=FAST_RETRANSMIT connection={client_key} "
                          f"cwnd={session.cwnd:.3f}->{reduced + 3 * state.cc.mss:.3f} "
                          f"ssthresh={threshold:.3f} recover={target}")
                    retransmit_oldest("3 duplicate ACKs (fast retransmit)")
                    state.deadline = time.monotonic() + state.rto
                    if return_on_update:
                        return last_byte_acked, False


def run_conn_send(s: socket.socket, conn_info: conn_struct, payload: bytes) -> int:
    """Serialize application writes on a connection; retain RTT/timers in it."""
    key = (conn_info.client_ip, conn_info.client_port)
    with connections_lock:
        session = connections.get(key)
        if session is None:
            return -1
        state = session.sender_state
    with state.send_lock:
        with connections_lock:
            current = connections.get(key)
            if (current is None or current.sender_state is not state
                    or current.state in ("CLOSED", "RESET", "ERROR")):
                return -1
        return _run_conn_send(s, conn_info, payload)


def _run_conn_send(s: socket.socket, conn_info: conn_struct, payload: bytes) -> int:
    """
    Send data on an established connection using raw sockets.
    
    Args:
        s: Raw socket
        conn_info: conn_struct tuple for the connection
        payload: Bytes payload to send
    
    Returns:
        int: Number of bytes sent, or -1 on error
    """
    client_ip = conn_info.client_ip
    client_port = conn_info.client_port
    client_key = (client_ip, client_port)
    listen_ip = conn_info.server_ip
    listen_port = conn_info.server_port
    
    with connections_lock:
        if client_key not in connections:
            print(f"[Streap_raw] run_conn_send Connection not found for {client_ip}:{client_port}")
            return -1
        session = connections[client_key]
    
    if not payload:
        return 0
    if len(payload) >= 0x80000000:
        raise ValueError("payload exceeds the supported sequence comparison range")
    if session.unacked:
        raise ValueError("connection already has unacknowledged data")
    start = session.server_seq
    send_base = next_seq_num = start
    target = (start + len(payload)) & M32
    unacked = session.unacked
    state = session.sender_state
    rtt = state.rtt
    with connections_lock:
        connections[client_key] = connections[client_key]._replace(
            send_base=send_base, next_seq_num=next_seq_num
        )
    try:
        while send_base != target:
            # Textbook 3.5.5 / slides 94-95: outstanding bytes are limited
            # by the peer's advertised receive window, in byte units.
            with connections_lock:
                session = connections.get(client_key)
                if session is None:
                    return -1
                budget = max(0, min(session.peer_rwnd, int(session.cwnd)) - seq_diff(next_seq_num, send_base))
                # Count waiting for congestion-window ACKs, but exclude idle
                # and receiver-limited periods (RFC 9438 4.2, 5.8).
                state.cc.update_clock(time.monotonic(),
                    session.peer_rwnd >= session.cwnd
                    and seq_diff(target, send_base) >= int(session.cwnd)
                    and state.recover is None)
            while next_seq_num != target:
                with connections_lock:
                    session = connections[client_key]
                    budget = max(0, min(session.peer_rwnd, int(session.cwnd)) - seq_diff(next_seq_num, send_base))
                if budget == 0:
                    break
                offset = seq_diff(next_seq_num, start)
                chunk = payload[offset:offset + min(MSS, budget)]
                with connections_lock:
                    session = connections[client_key]
                    window = get_current_rwnd(session)
                send_tcp_data_segment(
                    s, listen_ip, client_ip, listen_port, client_port,
                    seq=next_seq_num, ack_seq=session.client_seq,
                    payload=chunk, window=window
                )
                # Resume on real non-probe transmission, including refill
                # while older bytes remain outstanding. Preserve paused time.
                state.cc.update_clock(time.monotonic(),
                    session.peer_rwnd >= session.cwnd
                    and seq_diff(target, send_base) >= int(session.cwnd)
                    and state.recover is None, transmitting=True)
                if not unacked:
                    state.deadline = time.monotonic() + state.rto
                unacked[next_seq_num] = (chunk, time.monotonic(), False)
                next_seq_num = (next_seq_num + len(chunk)) & M32
                budget -= len(chunk)
                with connections_lock:
                    connections[client_key] = connections[client_key]._replace(
                        next_seq_num=next_seq_num, server_seq=next_seq_num,
                        last_activity=time.time()
                    )

            last_byte_acked, _ = wait_for_ack(
                s, conn_info, send_base, next_seq_num, unacked, rtt,
                session.client_seq, return_on_update=True,
                probe_data=payload[seq_diff(next_seq_num, start):seq_diff(next_seq_num, start)+1]
            )
            with connections_lock:
                next_seq_num = connections[client_key].next_seq_num
            send_base = (last_byte_acked + 1) & M32
            with connections_lock:
                if client_key not in connections:
                    return -1
                connections[client_key] = connections[client_key]._replace(
                    send_base=send_base, last_activity=time.time()
                )
        return len(payload)

    except Exception as e:
        print(f"[Streap_raw] run_conn_send Error in run_conn_send: {e}")
        return -1


def close_connection(s: socket.socket, conn_info: conn_struct):
    """Close a specific connection by sending FIN and removing from connection table."""
    client_ip = conn_info.client_ip
    client_port = conn_info.client_port
    client_key = (client_ip, client_port)
    listen_ip = conn_info.server_ip
    listen_port = conn_info.server_port
    
    with connections_lock:
        if client_key in connections:
            session = connections[client_key]
            # Send FIN packet
            fin_packet = build_tcp_packet(listen_ip, client_ip, listen_port, client_port,
                                          seq=session.server_seq, ack_seq=session.client_seq, ack=1, fin=1)
            ip_header = build_ip_header(listen_ip, client_ip, socket.IPPROTO_TCP, len(fin_packet))
            s.sendto(ip_header + fin_packet, (client_ip, 0))
            print(f"[Streap_raw] run_conn_send: Send FIN to {client_ip}:{client_port}")
            del connections[client_key]
    
    # Wake application reads; the worker notices removal on its queue timeout.
    with _receive_workers_lock:
        event = _receive_events.pop(client_key, None)
    if event is not None:
        event.set()
    remove_packet_queue(client_key)


def close_all_connections():
    """Close all connections and clean up."""
    with connections_lock:
        keys = list(connections)
        connections.clear()
    for key in keys:
        remove_packet_queue(key)
    with _receive_workers_lock:
        events = list(_receive_events.values())
        _receive_events.clear()
    for event in events:
        event.set()
