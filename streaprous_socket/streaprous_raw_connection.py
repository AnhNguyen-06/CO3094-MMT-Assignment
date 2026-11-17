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
from collections import namedtuple, deque
from dataclasses import dataclass
import netifaces

# Import streaprout packet dispatcher functions
from .streaprous_packet_dispatcher import (
    start_packet_dispatcher,
    stop_packet_dispatcher,
    get_packet_queue,
    remove_packet_queue,
    _packet_dispatcher_lock,
    _SYN_KEY,
)

# Global table to manage multiple connection
# The mapping include {key: value} as { (client_ip, client_port): conn_struct }
connections = {}
connections_lock = threading.Lock()

# Management structure to serialize the 3-way handshake
# Each hand shake is manage by a unique ID client_key
# including client_ip client_port
handshake_lock = threading.Lock()
handshake_in_progress = {}


# Default raw port listener
DEFAULT_LISTEN_IP = "0.0.0.0"
DEFAULT_LISTEN_PORT = 22239
DEFAULT_INTERFACE_NAME = "lo0"

# ---------------------------------------------------------------------------
# Reliability helpers
# ---------------------------------------------------------------------------
MSS = 1460
M32 = 0xFFFFFFFF

def seq_diff(a, b):
    """a - b in modulo 2^32 arithmetic, returned as a signed number (handles sequence number wraparound)."""
    d = (a - b) & M32
    return d - (M32 + 1) if d >= 0x80000000 else d

def split_into_segments(payload, mss=MSS):
    return [payload[offset:offset + mss] for offset in range(0, len(payload), mss)] # slide 77 chapter 3

# --- RTT / RTO estimation and retransmission (slide 82, 83 chapter 3) ---
ALPHA = 0.125       # weight of the new sample in EstimatedRTT
BETA = 0.25         # weight of the new sample in DevRTT
INITIAL_RTO = 1.0   # seconds, used when no RTT samples are available
MIN_RTO = 0.2       # seconds, lower bound (RTT in LAN networks is very small)
MAX_RTO = 10.0      # seconds, upper bound
MAX_RETRIES = 5     # maximum number of consecutive retransmissions before giving up

class RttEstimator:
    """ Calculate EstimatedRTT, DevRTT and RTO from RTT samples """
    def __init__(self):
        self.est = None
        self.dev = None
        self.rto = INITIAL_RTO

    def update(self, sample):
        if sample <= 0:
            return
        if self.est is None:
            self.est = sample
            self.dev = sample / 2
        else:
            self.dev = (1 - BETA) * self.dev + BETA * abs(sample - self.est)    # slide 83 chapter 3: DevRTT = (1-beta)*DevRTT + beta*abs(SampleRTT - EstimatedRTT).
            self.est = (1 - ALPHA) * self.est + ALPHA * sample  # slide 82 chapter 3: # EstimatedRTT = (1-alpha)*EstimatedRTT + alpha*SampleRTT.
        calculated_rto = self.est + 4 * self.dev    # Chapter 3, slide 3-83: TimeOutInterval = EstimatedRTT + 4*DevRTT.
        self.rto = min(max(calculated_rto, MIN_RTO), MAX_RTO)


@dataclass
class OutstandingSegment:
    # slides 79 và 146 chapter 3: lưu dữ liệu đã gửi, chờ cumulative ACK
    seq: int
    payload: bytes
    first_sent_at: float
    last_sent_at: float
    retransmitted: bool = False

# hàm mới cùng các biến đã thống nhất với sender
def on_ack(conn, segment, received_at):
    """xử lý dữ liệu ACK sau khi đã thiết lập handshake"""
    ack_flag = bool(segment.flags & 0x10)
    syn_or_rst = bool(segment.flags & 0x06)
    if not ack_flag or syn_or_rst:
        return "invalid"

    ack = segment.ack
    with conn.cv:
        if conn.state not in ("ESTABLISHED", "CLOSE_WAIT", "FIN_WAIT_1", "FIN_WAIT_2", "CLOSING", "LAST_ACK", "TIMED_WAIT"): # slide 96, 103, 104 chapter 3: ACK được xử lý theo vòng đời connection
            return "invalid"
        if conn.error is not None or seq_diff(ack, conn.server_seq) > 0: # ACK phải nằm trong giới hạn dữ liệu đã gửi
            return "invalid"
        progress = seq_diff(ack, conn.send_base)
        if progress < 0:
            return "old"
        elif progress == 0:
            conn.last_activity = time.time()
            pure_ack = (not segment.payload and not (segment.flags & 0x07)) # ko có SYN/RST/FIN
            same_window = segment.window == conn.last_ack_window
            if conn.unacked and pure_ack and same_window:
                conn.dup_ack_count += 1
                if conn.dup_ack_count == 3:
                    conn.fast_retransmit_pending = True # slide 88 chapter 3: 3 duplicate ACK cần fast retransmit
            else:
                conn.dup_ack_count = 0
            conn.last_ack_window = segment.window
            conn.cv.notify_all()
            return "duplicate"

        # slide 79, 146 chapter 3: ACK mới xác nhận liên tục các byte trước ACK number
        rtt_sample = None
        ack_retransmission = False
        while conn.unacked:
            record = conn.unacked[0]
            ack_bytes = seq_diff(ack, record.seq)
            if ack_bytes <= 0:
                break
            if record.retransmitted: # đánh dấu để loại mẫu RTT
                ack_retransmission = True
            if ack_bytes >= len(record.payload):
                conn.unacked.popleft() # record đã đủ nên cần giải phóng bớt dữ liệu đã ACK kể cả khi record từng được gửi lại
                if not record.retransmitted:
                    rtt_sample = received_at - record.first_sent_at
            else:
                record.payload = record.payload[ack_bytes:] # bỏ prefix đã ACK
                record.seq = ack
                break

        conn.send_base = ack # slide 146 chapter 3: send_base = y
        conn.last_activity = time.time()
        # slide 81 chapter 3: bỏ qua mẫu từ retransmission, chọn cách thận trọng: bỏ mẫu nếu ACK này cũng xác nhận dữ liệu đã từng được gửi lại
        if rtt_sample is not None and not ack_retransmission:
            conn.rtt.update(rtt_sample)
        conn.dup_ack_count = 0
        conn.retry_count = 0
        conn.fast_retransmit_pending = False
        conn.last_ack_window = segment.window
        # slide 146 chapter 3: còn dữ liệu chưa ACK -> khởi động lại timer, ACK hết dữ liệu -> dừng timer
        if conn.unacked:
            conn.timer_deadline = received_at + conn.rtt.rto
        else:
            conn.timer_deadline = None

        conn.cv.notify_all()
        return "new"

class TcpSegment:
    """ Cấu trúc segment đã qua kiểm tra header/checksum để truyền vào on_ack """
    def __init__(self, seq, ack, flags, payload=b"", window=0):
        self.seq = seq
        self.ack = ack
        self.flags = flags
        self.payload = payload
        self.window = window

class conn_struct:
    """ Đối tượng trạng thái kết nối giữa sender và receiver
        3-20, 3-21
        3-84, 3-146
        3-68, 3-90, 3-96, 3-145
        3-101, 3-104, 3-147 """
    def __init__(
        self,
        client_ip,
        client_port,
        server_ip,
        server_port,
        state="LISTEN",
        server_seq=2000,
        client_seq=0,
        expected_final_ack=0,
        last_activity=None,
        send_base=None,
    ):
        # Địa chỉ 4-tuple và trạng thái kết nối hiện có
        self.client_ip = client_ip
        self.client_port = client_port
        self.server_ip = server_ip
        self.server_port = server_port
        self.state = state
        self.expected_final_ack = expected_final_ack
        self.last_activity = time.time() if last_activity is None else last_activity
    
        # Các trường Sequence / ACK
        self.server_seq = server_seq
        self.send_base = server_seq if send_base is None else send_base
        self.client_seq = client_seq

        # Các trường phía Sender
        self.unacked = deque()
        self.rtt = RttEstimator()
        self.timer_deadline = None
        self.dup_ack_count = 0
        self.retry_count = 0
        self.fast_retransmit_pending = False
        self.last_ack_window = None

        # Khóa đồng bộ dùng chung
        self.cv = threading.Condition()
        self.send_lock = threading.Lock()

        # Các trường phía receiver
        self.recv_buffer = bytearray()
        self.peer_eof = False
        self.error = None

    def _replace(self, **kwargs):
        with self.cv:
            for k, v in kwargs.items():
                setattr(self, k, v)
        return self

def classify_segment(rcv_next, seq, length):
    """ Phân loại segment nhạn được so với byte mong đợi tiếp theo rcv_next """
    """ Slide 3-68, 3-78, 3-79, 3-85 """
    d = seq_diff(seq, rcv_next)
    if d == 0:
        return "in_order"
    if d < 0:
        if d + length <= 0:
            return "duplicate" # toàn bộ các byte trong gói đã nhận trước đó (3-52, 3-61)
        return "partial_overlap" # phần đầu (-d bytes) trùng, phần đuôi là byte mới từ rcv_next (3-78, 3-79)
    return "gap" # d>0: gói đến sớm hơn rcv_next, có gap (3-68, 3-85)

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
    """Return True if the TCP checksum of a received IPv4 packet is valid.
    Grounded in Chapter 4 (Slide 4-43: IP datagram format) and
    Chapter 3 (Slide 3-31..3-34, 3-78: Internet checksum & TCP segment structure).
    """
    if not isinstance(packet, (bytes, bytearray)) or len(packet) < 40: # gói IPv4 + TCP tối thiểu 40 bytes (Slide 4-43, 3-78)
        return False

    version = (packet[0] >> 4) & 0x0F
    ihl = (packet[0] & 0x0F) * 4 # kiểm tra đúng IPv4 và độ dài IP header >= 20 bytes (Slide 4-43)
    if version != 4 or ihl < 20 or len(packet) < ihl + 20:
        return False

    total = struct.unpack('!H', packet[2:4])[0]
    if total < ihl + 20 or len(packet) < total: # đảm bảo total length hợp lệ và gói không bị cắt cụt (Slide 4-43)
        return False

    if packet[9] != socket.IPPROTO_TCP: # giao thức tầng trên phải là TCP = 6 (Slide 4-43)
        return False

    tcp = packet[ihl:total]
    tcp_header_len = ((tcp[12] >> 4) & 0x0F) * 4 # kiểm tra head len của TCP >= 20 và <= len(tcp) (Slide 3-78)
    if tcp_header_len < 20 or len(tcp) < tcp_header_len:
        return False

    pseudo = packet[12:16] + packet[16:20] + struct.pack('!BBH', 0, socket.IPPROTO_TCP, len(tcp))
    return checksum(pseudo + tcp) == 0 # kiểm tra tổng kiểm 16-bit bù 1 (Slide 3-31..3-34, 3-44)

def build_tcp_packet(src_ip, dest_ip, src_port, dst_port, seq, ack_seq, syn=0, ack=0, fin=0):
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
    """
    flags = (ack << 4) + (syn << 1) + fin
    offset_res = (5 << 4) + 0  # 20 bytes data offset (5 * 4)
    window = 5840
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


def send_tcp_data_segment(s, src_ip, dest_ip, src_port, dst_port, seq, ack_seq, payload):
    """Assembles and transmits a single TCP segment containing data payload.

    Args:
         src_ip       Source IP address
         dest_ip      Destination IP address
         src_port     Source port
         dst_port     Destination port
         seq          Sequence number
         ack_seq      ACK for sequence
         syn          SYN flag
         ack          ACK flag
         payload      Payload

    """

    # TODO: Hardcode for fast data pushing
    #       The setting PSH + ACK
    #       need to modify in full schema
    flags = 0x18
    offset_res = (5 << 4) + 0
    window = 5840
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


def accept(s: socket.socket, listen_ip: str, listen_port: int, interface_name: str = None) -> conn_struct:
    """
    Accept a new connection by performing the 3-way handshake using raw sockets.
    Returns a conn_struct tuple for the established connection.
    Handshakes are serialized to ensure only one 3-way handshake is processed at a time.
    
    Args:
        s: Raw socket
        listen_ip: Server IP to listen on (e.g., '0.0.0.0')
        listen_port: Server port to listen on
        interface_name: Network interface name for sending packets (optional)
    
    Returns:
        conn_struct: Established connection information
    """
    # Start packet dispatcher for this port
    start_packet_dispatcher(s, listen_port)
    
    # Get actual source IP for sending packets
    if listen_ip == "0.0.0.0":
        send_ip = get_interface_ip(interface_name)
        print(f"[Streap_raw] accept: listen_ip=0.0.0.0, using send_ip={send_ip} for outgoing packets")
    else:
        send_ip = listen_ip
    
    server_seq = 2000
    client_ip = None
    client_port = None

    print(f"[Streap_raw] accept: Waiting for incoming connections on {listen_ip}:{listen_port} (send_ip={send_ip})...")
    try:
        while True:
            # Get packet from dispatcher queue (for SYN packets)
            syn_q = get_packet_queue(_SYN_KEY)
            try:
                packet, addr = syn_q.get(timeout=1.0)
                print(f"[Streap_raw] accept: Got packet from SYN queue")
            except queue.Empty:
                continue

            if not verify_tcp_checksum(packet):
                continue
            ihl = (packet[0] & 0x0F) * 4
            total = struct.unpack('!H', packet[2:4])[0]
            tcp_packet = packet[ihl:total]

            # Unpack the received TCP header
            tcph = struct.unpack('!HHLLBBHHH', tcp_packet[:20])
            src_port, dest_port, pkt_seq, pkt_ack, flags = (
                tcph[0],
                tcph[1],
                tcph[2],
                tcph[3],
                tcph[5],
            )

            # Bypass non-listen port
            if dest_port != listen_port:
                continue

            syn_flag = (flags & 0x02) >> 1
            ack_flag = (flags & 0x10) >> 4

            # Build client_key from client IP and client port
            client_ip = socket.inet_ntoa(packet[12:16])
            client_port = src_port
            client_key = (client_ip, client_port)
            print(f"\n[Streap_raw] accept: Receiv packet from Client ({client_ip}:{client_port}) (Seq={pkt_seq}, SYN={syn_flag}, ACK={ack_flag})")

            # Create queue for each connection associated 
            # with tupple client_key=(client_ip, client_port)
            q = get_packet_queue(client_key)
            print(f"[Streap_raw] accept: Createet per-connection queue for {client_key}")
            with connections_lock:
                # Declare initialized session if not available
                if client_key not in connections:
                    connections[client_key] = conn_struct(
                        client_ip=client_ip,
                        client_port=client_port,
                        server_ip=send_ip,
                        server_port=listen_port,
                        state="LISTEN",
                        server_seq=2000,
                        client_seq=0,
                        expected_final_ack=0,
                        last_activity=time.time()
                    )
                session = connections[client_key]

                        
            # Perform 3 handshake step
            # STEP 1: Obtain client SYN 
            if syn_flag == 1 and ack_flag == 0:
                print(f"\nHandshake1: Received SYN from Client ({client_ip}:{client_port}) (Seq={pkt_seq})")

                # Quick duplicate handshake check (fast, no heavy operations)
                with handshake_lock:
                    if handshake_in_progress.get(client_key, False):
                        print(f"[Streap_raw] accept: Handshake already in progress for {client_ip}:{client_port}, dropping SYN")
                        continue
                    handshake_in_progress[client_key] = True

                # STEP 2: Reply SYN-ACK immediately
                # Build TCP packet for SYN-ACK
                next_ack = (pkt_seq + 1) & M32
                syn_ack_packet = build_tcp_packet(send_ip, client_ip, listen_port, client_port,
                                                  seq=server_seq, ack_seq=next_ack, syn=1, ack=1)
                ip_header = build_ip_header(send_ip, client_ip, socket.IPPROTO_TCP, len(syn_ack_packet))
                full_packet = ip_header + syn_ack_packet

                # Send SYN-ACK packet
                print(f"[Streap_raw] accept: Sending SYN-ACK to {client_ip}:{client_port} from {send_ip}:{listen_port}")
                print(f"[Streap_raw] accept: SYN-ACK packet size: {len(full_packet)} bytes (IP={len(ip_header)}, TCP={len(syn_ack_packet)})")
                bytes_sent = s.sendto(full_packet, (client_ip, 0))
                print(f"Handshake2: Sent SYN-ACK to Client (Seq={server_seq}, Ack={next_ack}, bytes_sent={bytes_sent})")

                # Register connection to the associated queue for each connection associated 
                # with tupple client_key=(client_ip, client_port)
                with connections_lock:
                    connections[client_key] = conn_struct(
                        client_ip=client_ip,
                        client_port=client_port,
                        server_ip=send_ip,  # Use actual sending IP
                        server_port=listen_port,
                        state="SYN_RCVD",
                        server_seq=server_seq,
                        client_seq=next_ack,
                        expected_final_ack=(server_seq + 1) & M32,
                        last_activity=time.time()
                    )
                    session = connections[client_key]

                # STEP 3: Wait for client FIN-ACK
                # The final ACK will arrive on the per-connection queue, not the SYN queue
                deadline = time.time() + 10.0
                while time.time() < deadline:
                    try:
                        packet, addr = q.get(timeout=0.5)
                        print(f"[Streap_raw] accept: Got packet from per-connection queue for {client_ip}:{client_port}")
                    except queue.Empty:
                        print(f"[Streap_raw] accept: Per-connection queue empty for {client_ip}:{client_port}, waiting...")
                        continue

                    if not verify_tcp_checksum(packet):
                        continue
                    ihl = (packet[0] & 0x0F) * 4
                    total = struct.unpack('!H', packet[2:4])[0]
                    tcp_packet = packet[ihl:total]

                    # Unpack the received TCP header
                    tcph = struct.unpack('!HHLLBBHHH', tcp_packet[:20])
                    src_port, dest_port, pkt_seq, pkt_ack, flags = (
                        tcph[0],
                        tcph[1],
                        tcph[2],
                        tcph[3],
                        tcph[5],
                    )

                    syn_flag = (flags & 0x02) >> 1
                    ack_flag = (flags & 0x10) >> 4
                    print(f"[Streap_raw] accept: Received packet in handshake wait - SYN={syn_flag}, ACK={ack_flag}, Seq={pkt_seq}, Ack={pkt_ack}")

                    # Check if this is the final ACK (ACK only, no SYN)
                    if syn_flag == 1 and ack_flag == 0:
                        s.sendto(full_packet, (client_ip, 0))
                        continue
                    if syn_flag == 0 and ack_flag == 1 and pkt_ack == session.expected_final_ack and pkt_seq == session.client_seq:
                        print(f"[Streap_raw] accept: handshake3 Received FIN-ACK from Client (Seq={pkt_seq}, Ack={pkt_ack})")
                        tcp_header_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
                        app_payload = tcp_packet[tcp_header_len:]
                        with connections_lock:
                            if session.state != "SYN_RCVD":
                                print(f"[Streap_raw] accept: Non handshake state for {client_ip}:{client_port}")
                                break
                            with session.cv:
                                session.state = "ESTABLISHED"
                                session.server_seq = pkt_ack
                                session.send_base = pkt_ack
                                session.last_ack_window = tcph[6] # slide 78, 88 chapter 3: trường window trong TCP header đã đc kiểm tra, hỗ trợ khởi tạo state để nhận diện duplicate ACK
                                session.client_seq = (pkt_seq + len(app_payload)) & M32
                                if len(app_payload) > 0:
                                    session.recv_buffer.extend(app_payload)
                                session.last_activity = time.time()
                        
                        if len(app_payload) > 0:
                            ack_packet = build_tcp_packet(send_ip, client_ip, listen_port, client_port, seq=session.server_seq, ack_seq=session.client_seq, ack=1)
                            ip_header = build_ip_header(send_ip, client_ip, socket.IPPROTO_TCP, len(ack_packet))
                            s.sendto(ip_header + ack_packet, (client_ip, 0))
                        with handshake_lock:
                            handshake_in_progress[client_key] = False
                        
                        print(f"[Streap_raw] Etablished handshak with connection: ({client_ip}:{client_port}) ESTABLISHED")
                        return session
                    
                print(f"[Streap_raw] Handshake timeout for {client_ip}:{client_port}")
                with handshake_lock:
                    handshake_in_progress[client_key] = False
                remove_packet_queue(client_key)
                with connections_lock:
                    connections.pop(client_key, None)
                continue
                
            if session.state == "SYN_RCVD" and syn_flag == 0 and ack_flag == 1 and pkt_ack == session.expected_final_ack and pkt_seq == session.client_seq:
                print(f"[Streap_raw] accept: handshake3 received Final ACK from Client on SYN queue (Seq={pkt_seq}, Ack={pkt_ack})")
                print(f"[Streap_raw] accept: Fallback - got final ACK on SYN queue for {client_ip}:{client_port}")
                tcp_header_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
                app_payload = tcp_packet[tcp_header_len:]

                with connections_lock:
                    if session.state != "SYN_RCVD":
                        print(f"[Streap_raw] accept: Non handshake state for {client_ip}:{client_port}")
                        continue
                    with session.cv:
                        session.state = "ESTABLISHED"
                        session.server_seq = pkt_ack
                        session.send_base = pkt_ack
                        session.last_ack_window = tcph[6]
                        session.client_seq = (pkt_seq + len(app_payload)) & M32
                        if len(app_payload) > 0:
                            session.recv_buffer.extend(app_payload)
                        session.last_activity = time.time()
                    
                if len(app_payload) > 0:
                    ack_packet = build_tcp_packet(send_ip, client_ip, listen_port, client_port, seq=session.server_seq, ack_seq=session.client_seq, ack=1)
                    ip_header = build_ip_header(send_ip, client_ip, socket.IPPROTO_TCP, len(ack_packet))
                    s.sendto(ip_header + ack_packet, (client_ip, 0))
                    
                with handshake_lock:
                    handshake_in_progress[client_key] = False
                print(f"[Streap_raw] Etablished handshak with connection: ({client_ip}:{client_port}) ESTABLISHED")
                return session
                            
    except KeyboardInterrupt:
        print("\n[-] Server stopped.")
        # Clear handshake flags on interrupt
        with handshake_lock:
            handshake_in_progress.clear()
        raise


def run_conn_recv(s: socket.socket, session: conn_struct) -> bytes:
    """
    Receive data on an established connection using raw sockets.
    This function handles incoming packets for a specific connection by reading
    from the packet dispatcher's per-connection queue.
    
    Args:
        s: raw socket
        conn_info: conn_struct tuple for the connection
    
    Returns:
        bytes: The received data payload, or empty bytes if connection closed
    """
    """
    Gặp ACK: gọi on_ack cho sender (3-80, 3-84)
    Gặp data: kiểm tra thứ tự, lưu vào session.recv_buffer (3-90, 3-91)
    Gặp FIN/RST: cập nhật peer_eof/error (3-104)
    """
    client_ip = session.client_ip
    client_port = session.client_port
    listen_ip = session.server_ip
    listen_port = session.server_port
    client_key = (client_ip, client_port)
    
    # Get the packet queue for this connection from the dispatcher
    packet_queue = get_packet_queue(client_key)
    
    print(f"[Streap_raw] run_conn_recv: Starting receive loop for {client_ip}:{client_port} (waiting for data...)")
    
    try:
        while True:
            with session.cv:
                if len(session.recv_buffer) > 0:
                    data = bytes(session.recv_buffer)
                    session.recv_buffer.clear()
                    return data
                if session.peer_eof or session.state == "CLOSED" or session.error is not None:
                    return b""
            
            # Get packet from the dispatcher queue instead of reading directly from socket
            try:
                packet, addr = packet_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not verify_tcp_checksum(packet):
                continue
            ihl = (packet[0] & 0x0F) * 4
            total = struct.unpack('!H', packet[2:4])[0]
            tcp_packet = packet[ihl:total]

            # Unpack the received TCP header
            tcph = struct.unpack('!HHLLBBHHH', tcp_packet[:20])
            src_port, dest_port, pkt_seq, pkt_ack, flags, window = (
                tcph[0],
                tcph[1],
                tcph[2],
                tcph[3],
                tcph[5],
                tcph[6],
            )
            tcp_header_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
            app_payload = tcp_packet[tcp_header_len:]
            has_data = len(app_payload) > 0

            # Bypass non-listen port
            if dest_port != listen_port:
                continue

            # Check if this packet is for our connection
            if src_port != client_port:
                continue
            
            syn_flag = (flags & 0x02) >> 1
            ack_flag = (flags & 0x10) >> 4
            psh_flag = (flags & 0x08) >> 3
            fin_flag = (flags & 0x01)
            rst_flag = (flags & 0x04) >> 2

            print(f"[Streap_raw] run_conn_recv: Received packet from {client_ip}:{client_port} (SYN={syn_flag}, ACK={ack_flag}, PSH={psh_flag}, FIN={fin_flag}, RST={rst_flag}, Seq={pkt_seq}, Ack={pkt_ack})")
            # Handle RST (connection reset)
            if rst_flag:
                print(f"[Streap_raw] Received RST from {client_ip}:{client_port}")
                with session.cv:
                    session.error = "Connection reset by peer"
                    session.state = "CLOSED"
                    session.cv.notify_all()
                with connections_lock:
                    connections.pop(client_key, None)
                remove_packet_queue(client_key)
                return b""

            # Xử lý ACK cho mọi segment có cờ ACK hợp lệ (3-80)
            # quy ước: gọi on_ack() ở ngoài khóa session.cv để on_ack() tự lấy session.cv bên trong
            if ack_flag and not syn_flag:
                segment = TcpSegment(
                    seq=pkt_seq,
                    ack=pkt_ack,
                    flags=flags,
                    payload=app_payload,
                    window=window,
                )
                on_ack(session, segment, time.monotonic())
            
            with session.cv:
                session.last_activity = time.time()

            # Handle data payload (PSH + ACK) or (ACK with data) - Fast path ACK
            # Some clients may not set PSH flag for small requests
            
            
            if (psh_flag and ack_flag) or (ack_flag and has_data and not syn_flag and not rst_flag):
                # Dynamically look up header length to bypass any incoming TCP Options
                
                app_payload = tcp_packet[tcp_header_len:]
                
                if len(app_payload) > 0:
                    print(f"[Streap_raw] Received {len(app_payload)} bytes of data from {client_ip}:{client_port}")
                    print(f"[Streap_raw] Received payload: {app_payload[:100]}...")
                    
                    # # Send ACK for received data IMMEDIATELY (fast path)
                    # next_ack = pkt_seq + len(app_payload)
                    
                    # Order check: accept only the segment that starts at the expected byte (client_seq)
                    kind = classify_segment(session.client_seq, pkt_seq, len(app_payload))
                    if kind == "partial_overlap":
                        overlap_bytes = -seq_diff(pkt_seq, session.client_seq) # số byte đầu bị trùng
                        app_payload = app_payload[overlap_bytes:]
                        print(f"[Streap_raw] run_conn_recv: partial_overlap seq={pkt_seq}, trimmed {overlap_bytes}B, kept {len(app_payload)}B")
                    elif kind != "in_order":
                        print(f"[Streap_raw] run_conn_recv: {kind} seq={pkt_seq}, expected={session.client_seq} -> dup ACK")
                        dup_ack = build_tcp_packet(session.server_ip, client_ip, listen_port, client_port, seq=session.server_seq, ack_seq=session.client_seq, ack=1)
                        ip_header = build_ip_header(session.server_ip, client_ip, socket.IPPROTO_TCP, len(dup_ack))
                        s.sendto(ip_header + dup_ack, (client_ip, 0))
                        continue
                    next_ack = (session.client_seq + len(app_payload)) & M32       

                    ack_packet = build_tcp_packet(session.server_ip, client_ip, listen_port, client_port,
                                                  seq=session.server_seq, ack_seq=next_ack, ack=1)
                    ip_header = build_ip_header(session.server_ip, client_ip, socket.IPPROTO_TCP, len(ack_packet))
                    s.sendto(ip_header + ack_packet, (client_ip, 0))
                    print(f"[Streap_raw] Sent ACK for data (Ack={next_ack})")
                    
                    # Update sequence numbers AFTER ACK sent
                    with session.cv:
                        session.client_seq = next_ack
                        session.recv_buffer.extend(app_payload)
                        session.last_activity = time.time()
                        session.cv.notify_all()
            
            # Handle FIN (connection close)
            if fin_flag:
                print(f"[Streap_raw] Received FIN from {client_ip}:{client_port}")
                with session.cv:
                    fin_ack = (session.client_seq + 1) & M32
                    session.client_seq = fin_ack
                    session.peer_eof = True
                    if session.state == "ESTABLISHED":
                        session.state = "CLOSE_WAIT"
                    session.cv.notify_all()
                # Send ACK for FIN
                ack_packet = build_tcp_packet(listen_ip, client_ip, listen_port, client_port,
                                              seq=session.server_seq, ack_seq=fin_ack, ack=1)
                ip_header = build_ip_header(listen_ip, client_ip, socket.IPPROTO_TCP, len(ack_packet))
                s.sendto(ip_header + ack_packet, (client_ip, 0))

    except KeyboardInterrupt:
        print("\n[Streap_raw] Receive loop interrupted.")
        return b""
    except Exception as e:
        print(f"[Streap_raw] Error in run_conn_recv: {e}")
        return b""

def wait_for_ack(s, conn_info, start, target, unacked, rtt, ack_seq):
    """Wait for the client to ACK up to the last byte of the response, and retransmit lost segments.

    Returns (last_byte_acked, all_acked).
    last_byte_acked = the LAST byte the client has acknowledged (slide 3-146) = SendBase - 1.
    `start` = first byte of the response, `target` = the byte right after the last byte.
    Retransmits the OLDEST unacknowledged segment when:
      - the RTO timer expires (RTO doubles after each expiry), or
      - exactly 3 consecutive duplicate ACKs arrive (fast retransmit).
    Gives up after MAX_RETRIES consecutive retransmissions without progress.

    start: sequence bắt đầu của payload trong lần gửi
    target: sequence ngay sau byte cuối của payload
    unacked: là conn_info.unacked
    rtt: là conn_info.rtt
    trả về (last_byte_acked, all_acked)
    """
    last_byte_acked = (start - 1) & M32          # no byte acknowledged yet
    last_byte_sent = (target - 1) & M32          # last byte of the response
    # if seq_diff(start, target) >= 0:             # nothing to wait for
    #     return last_byte_acked, True

    # client_key = (conn_info.client_ip, conn_info.client_port)
    # packet_queue = get_packet_queue(client_key)
    # rto = rtt.rto
    # retries = 0
    # dup_count = 0
    # deadline = time.time() + rto

    def retransmit_oldest(reason):
        record = unacked[0]
        seg_seq = record.seq            # seq đầu của phần dữ liệu còn chờ ACK
        seg_chunk = record.payload
        
        sent_at = time.monotonic()

        send_tcp_data_segment(
            s, conn_info.server_ip, conn_info.client_ip,
            conn_info.server_port, conn_info.client_port,
            seq=seg_seq, ack_seq=conn_info.client_seq, payload=seg_chunk
        )
        record.last_sent_at = sent_at   # thời điểm gửi gần nhất
        record.retransmitted = True
        conn_info.timer_deadline = sent_at + rtt.rto
        print(f"[Streap_raw] wait_for_ack: RETRANSMIT seq={seg_seq} ({len(seg_chunk)} bytes), "
              f"reason: {reason}, RTO={rto*1000:.0f} ms, attempt {retries}")

    with conn_info.cv:
        while True:
            # kiểm tra đầu loop
            last_byte_acked = (conn_info.send_base - 1) & M32
            if conn_info.error is not None:
                return last_byte_acked, False
            if seq_diff(conn_info.send_base, target) >= 0:
                return last_byte_acked, True
            if not unacked or conn_info.timer_deadline is None:
                raise RuntimeError("Chưa đạt mốc ACK nhưng buffer hoặc timer không hợp lệ")
            rto = rtt.rto
            retries = conn_info.retry_count
            deadline = conn_info.timer_deadline
            left = deadline - time.monotonic()

            if left <= 0:                            # RTO expired
                # phần xử lý timeout
                if retries >= MAX_RETRIES:
                    print(f"[Streap_raw] wait_for_ack: GIVE UP after {retries} retransmissions, last_byte_acked={last_byte_acked}")
                    conn_info.error = TimeoutError("Đã hết số lần gửi lại cho phép")
                    conn_info.timer_deadline = None
                    conn_info.fast_retransmit_pending = False
                    conn_info.cv.notify_all()
                    return last_byte_acked, False
                retries += 1
                conn_info.retry_count = retries
                conn_info.dup_ack_count = 0
                conn_info.fast_retransmit_pending = False
                rto = min(rto * 2, MAX_RTO)          # next wait is twice as long (exponential backoff)
                rtt.rto = rto
                retransmit_oldest("RTO expired")     # RTO trong log là khoảng chờ mới
                continue
            # try:
            #     packet, addr = packet_queue.get(timeout=left)
            # except queue.Empty:
            #     continue

            # ihl = (packet[0] & 0x0F) * 4
            # tcp_packet = packet[ihl:]
            # if len(tcp_packet) < 20:
            #     continue
            # tcph = struct.unpack('!HHLLBBHHH', tcp_packet[:20])
            # src_port, dest_port, pkt_ack, flags = tcph[0], tcph[1], tcph[3], tcph[5]
            # if src_port != conn_info.client_port or dest_port != conn_info.server_port:
            #     continue
            # if not (flags & 0x10):                   # no ACK flag
            #     continue

            # new_last = (pkt_ack - 1) & M32           # ACK number = next byte expected, so last byte received = ACK - 1
            # if seq_diff(new_last, last_byte_acked) > 0:          # NEW ACK: advance
            #     last_byte_acked = new_last
            #     newest_sent_at = None
            #     for seg_seq in list(unacked):
            #         seg_chunk, seg_sent_at, was_retx = unacked[seg_seq]
            #         seg_last_byte = (seg_seq + len(seg_chunk) - 1) & M32     # last byte of the segment
            #         if seq_diff(last_byte_acked, seg_last_byte) >= 0:
            #             del unacked[seg_seq]
            #             if not was_retx:             # Karn: do not sample RTT from retransmitted segments
            #                 newest_sent_at = seg_sent_at
            #     if newest_sent_at is not None:
            #         sample = time.time() - newest_sent_at
            #         rtt.update(sample)
            #         print(f"[Streap_raw] wait_for_ack: RTT sample={sample*1000:.1f} ms, "
            #             f"Est={rtt.est*1000:.1f} ms, Dev={rtt.dev*1000:.1f} ms, RTO={rtt.rto*1000:.1f} ms")
            #     print(f"[Streap_raw] wait_for_ack: ACK={pkt_ack} (last_byte_acked={last_byte_acked}, "
            #         f"{seq_diff(last_byte_sent, last_byte_acked)} bytes remaining, {len(unacked)} unacked segments)")
            #     if seq_diff(last_byte_acked, last_byte_sent) >= 0:
            #         return last_byte_acked, True
            #     retries = 0
            #     dup_count = 0
            #     rto = rtt.rto
            #     deadline = time.time() + rto         # progress made: restart the timer

            # elif new_last == last_byte_acked and unacked:        # DUPLICATE ACK
            #     tcp_hdr_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
            #     pure_ack = len(tcp_packet) == tcp_hdr_len and not (flags & 0x07)   # no SYN/RST/FIN, no data
            #     if pure_ack:
            #         dup_count += 1
            #         print(f"[Streap_raw] wait_for_ack: duplicate ACK #{dup_count} (ack={pkt_ack})")
            #         if dup_count == 3:
            #             retransmit_oldest("3 duplicate ACKs (fast retransmit)")
            #             deadline = time.time() + rto

            # trách nhiệm xử lý ACK đã được chuyển sang hàm on_ack()
            if conn_info.fast_retransmit_pending:
                conn_info.fast_retransmit_pending = False
                retransmit_oldest("3 duplicate ACKs cần fast retransmit")
                continue
            conn_info.cv.wait(timeout=left)
            
def run_conn_send(s: socket.socket, conn_info: conn_struct, payload: bytes) -> int:
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
    
    total = 0

    try:
        # slide 103, 104 chapter 3: CLOSE_WAIT vẫn cho phép gửi
        with session.cv:
            if session.error is not None:
                return -1
            if session.state not in ("ESTABLISHED", "CLOSE_WAIT"):
                raise ConnectionError("Trạng thái connection không cho phép gửi dữ liệu mới")
            start_seq = session.server_seq

        # server_seq dùng để biểu diễn sequence dành cho byte dữ liệu mới tiếp theo (chapter 3 tương ứng với NextSeqNum)
        for chunk in split_into_segments(payload):  # slide 77 chapter 3 chia dữ liệu theo MSS)
            # wait_for_ack(s, session, start_seq, None, session.unacked, session.rtt, session.client_seq) # kiểm tra timeout/fast retransmit giữa các segment.
            with session.cv:
                if session.error is not None:
                    return -1
                if session.state not in ("ESTABLISHED", "CLOSE_WAIT"):
                    raise ConnectionError("Chiều gửi bắt đầu đóng")
                
                # slide 78, 79 chapter 3: seq đánh số byte đầu trong segment
                segment_seq = session.server_seq
                sent_at = time.monotonic()

                send_tcp_data_segment(
                    s, listen_ip, client_ip, listen_port, client_port,
                    seq=segment_seq, ack_seq=session.client_seq, payload=chunk
                )

                session.unacked.append(OutstandingSegment(seq=segment_seq, payload=chunk, first_sent_at=sent_at, last_sent_at=sent_at)) # slide 79, 146 chapter 3: giữ dữ liệu chưa ACK để có thể gửi lại
                session.server_seq = (segment_seq + len(chunk)) & M32    # slide 146 chapter 3: NextSeqNum = NextSeqNum + length(data)
                session.last_activity = time.time()
                if session.timer_deadline is None: 
                    session.timer_deadline = sent_at + session.rtt.rto  # slide 84, 146 chapter 3: khởi động timer nếu chưa chạy
            total += len(chunk)

        with session.cv:
            target_seq = session.server_seq # ACK phải tiến đến mốc này để xác nhận hết lần gửi
            ack_seq = session.client_seq
        print(f"[Streap_raw] run_conn_send Sent {total} bytes in segments to {client_ip}:{client_port}")
        last_byte_acked, all_acked = wait_for_ack(s, session, start_seq, target_seq, session.unacked, session.rtt, ack_seq)   # start_seq into wait_for_ack()

        with session.cv:
            print(f"[Streap_raw] run_conn_send ACK {'COMPLETE' if all_acked else 'INCOMPLETE'}: LastByteAcked={last_byte_acked}, LastByteSent={(target_seq - 1) & M32}, {len(session.unacked)} unacked segments")
        if not all_acked:
            print(f"[Streap_raw] run_conn_send FAILED: client did not ACK all data")
            return -1            # không lùi server_seq về start_seq khi chưa được ACK toàn bộ

        return total

    except Exception as e:
        with session.cv:
            if session.error is None:
                session.error = e
            session.timer_deadline = None
            session.fast_retransmit_pending = False
            session.cv.notify_all()

        print(f"[Streap_raw] run_conn_send Error in run_conn_send: {e}")
        return -1


def close_connection(s: socket.socket, conn_info: conn_struct):
    """ Đóng kết nối TCP theo đúng FSM trong slide 3-103, 3-104:
    - Nếu đang CLOSE_WAIT: gửi FIN -> sang LAST_ACK -> chờ ACK(fin_seq + 1) -> CLOSED
    - Nếu đang ESTABLISHED: gửi FIN -> sang FIN_WAIT_1 -> chờ ACK(fin_seq + 1) (FIN_WAIT2) và chờ FIN từ peer -> gửi ACK -> TIMED_WAIT -> CLOSED """
    client_ip = conn_info.client_ip
    client_port = conn_info.client_port
    client_key = (client_ip, client_port)
    listen_ip = conn_info.server_ip
    listen_port = conn_info.server_port

    with connections_lock:
        session = connections.get(client_key)
    if session is None:
        remove_packet_queue(client_key)
        return
    
    with session.cv:
        if session.state == "CLOSED" or session.error is not None:
            with connections_lock:
                connections.pop(client_key, None)
            remove_packet_queue(client_key)
            return
        if session.unacked or session.send_base != session.server_seq: # slide 103, 104 chapter 3: phương án nhóm chọn là hoàn tất ACK dữ liệu trước khi phát FIN
            raise RuntimeError("Cần hoàn tất dữ liệu đang chờ ACK trước khi bắt đầu FIN")
        fin_seq = session.server_seq
        expected_fin_ack = (fin_seq + 1) & M32
        session.server_seq = expected_fin_ack
        if session.state == "CLOSE_WAIT":
            session.state = "LAST_ACK"
        else:
            session.state = "FIN_WAIT_1"
        ack_seq = session.client_seq
    
    packet_queue = get_packet_queue(client_key)
    rto = session.rtt.rto
    retries = 0
    fin_acked = False

    def send_fin():
        with session.cv:
            cur_ack = session.client_seq
        fin_pkt = build_tcp_packet(listen_ip, client_ip, listen_port, client_port, seq=fin_seq, ack_seq=cur_ack, ack=1, fin=1)
        ip_hdr = build_ip_header(listen_ip, client_ip, socket.IPPROTO_TCP, len(fin_pkt))
        s.sendto(ip_hdr + fin_pkt, (client_ip, 0))
        print(f"[Streap_raw] close_connection: Sent FIN (Seq={fin_seq}, Ack={cur_ack}, state={session.state})")
    
    send_fin()
    deadline = time.time() + rto

    while retries < MAX_RETRIES:
        with session.cv:
            if session.error is not None or session.state == "CLOSED":
                break
            if fin_acked and session.peer_eof:
                session.state = "TIMED_WAIT"
                break
        left = deadline - time.time()
        if left <= 0:
            retries += 1
            if not fin_acked and retries < MAX_RETRIES:
                send_fin()
                rto = min(rto * 2, MAX_RTO)
                deadline = time.time() + rto
                continue
            break
        try:
            packet, addr = packet_queue.get(timeout=min(left, 0.5))
        except queue.Empty:
            continue
        
        if not verify_tcp_checksum(packet):
            continue
        ihl = (packet[0] & 0x0F) * 4
        total = struct.unpack('!H', packet[2:4])[0]
        tcp_packet = packet[ihl:total]
        tcph = struct.unpack('!HHLLBBHHH', tcp_packet[:20])
        src_port, dest_port, pkt_seq, pkt_ack, flags = tcph[0], tcph[1], tcph[2], tcph[3], tcph[5]
        if src_port != client_port or dest_port != listen_port:
            continue
        
        rst_flag = (flags & 0x04) >> 2
        ack_flag = (flags & 0x10) >> 4
        fin_flag = flags & 0x01
        if rst_flag:
            break
        if ack_flag and seq_diff(pkt_ack, expected_fin_ack) >= 0:
            fin_acked = True
            with session.cv:
                session.send_base = expected_fin_ack
            if session.state == "LAST_ACK":
                session.state = "CLOSED"
                break
            elif session.state == "FIN_WAIT_1":
                session.state = "FIN_WAIT_2"
            
        if fin_flag:
            tcp_header_len = ((tcp_packet[12] >> 4) & 0x0F) * 4
            app_payload = tcp_packet[tcp_header_len:]
            with session.cv:
                if len(app_payload) > 0 and seq_diff(pkt_seq, session.client_seq) == 0:
                    session.client_seq = (session.client_seq + len(app_payload)) & M32
                    session.recv_buffer.extend(app_payload)
                fin_ack_num = (session.client_seq + 1) & M32
                session.client_seq = fin_ack_num
                session.peer_eof = True
                session.state = "TIMED_WAIT" if fin_acked else "CLOSING"
            ack_pkt = build_tcp_packet(listen_ip, client_ip, listen_port, client_port, seq=session.server_seq, ack_seq=fin_ack_num, ack=1)
            ip_hdr = build_ip_header(listen_ip, client_ip, socket.IPPROTO_TCP, len(ack_pkt))
            s.sendto(ip_hdr + ack_pkt, (client_ip, 0))
            if fin_acked:
                break
    with session.cv:
        session.state = "CLOSED"
        session.cv.notify_all()
    with connections_lock:
        connections.pop(client_key, None)
    remove_packet_queue(client_key)


def close_all_connections():
    """Close all connections and clean up."""
    with connections_lock:
        connections.clear()