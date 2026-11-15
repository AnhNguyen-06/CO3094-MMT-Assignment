#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
#
# StreapRous Raw TCP Client / Peer
#

"""
client.py
~~~~~~~~~
A standalone Raw TCP client for testing 3-way handshake, reliable data transfer,
and peer-to-peer communication based on Chapter 3 (Transport Layer).
"""

import sys
import os
import argparse
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from streaprous_socket.streaprous_raw_connection import (
    raw_connect,
    run_conn_send,
    run_conn_recv,
    close_connection,
    get_interface_ip,
    MSS
)
from start_backend import setup_rst_block, detect_interface


def main():
    parser = argparse.ArgumentParser(
        prog="StreapRousClient",
        description="Raw TCP Client performing 3-way handshake (Chapter 3 - Slide 101)"
    )
    parser.add_argument("--server-ip", type=str, default=None, help="Target Server IPv4 address (default: auto-detected real IP)")
    parser.add_argument("--server-port", type=int, default=9000, help="Target Server Port (default: 9000)")
    parser.add_argument("--client-port", type=int, default=None, help="Local Client Port (default: 22238)")
    parser.add_argument("--interface", type=str, default=None, help="Network Interface name")
    parser.add_argument("--message", type=str, default=None, help="Message to send after handshake")
    args = parser.parse_args()

    # Tự động lấy IP thật của card mạng nếu không truyền vào
    server_ip = args.server_ip or get_interface_ip(args.interface)

    # Cảnh báo và tự động sửa nếu người dùng truyền localhost (vì backend cấm localhost)
    if server_ip in ("127.0.0.1", "localhost") or server_ip.startswith("127."):
        real_ip = get_interface_ip(args.interface)
        if real_ip != "127.0.0.1":
            print(f"[!] Chú ý: Backend StreapRous cấm dùng localhost (127.0.0.1).")
            print(f"[*] Tự động chuyển --server-ip sang IP thật của máy: {real_ip}")
            server_ip = real_ip

    server_port = args.server_port

    # Auto-detect interface
    interface = args.interface or detect_interface(server_ip)

    # Cổng client cố định để firewall iptables chặn RST chuẩn xác
    client_port = args.client_port or 22238

    # Chặn kernel RST tại cổng client để kernel không tự ý gửi RST phá kết nối raw
    setup_rst_block(server_ip, client_port)

    print(f"============================================================")
    print(f"[*] Starting StreapRous Raw TCP Client")
    print(f"[*] Connecting to: {server_ip}:{server_port}")
    print(f"[*] Local Port:    {client_port} | Interface: {interface}")
    print(f"[*] MSS:           {MSS} bytes")
    print(f"============================================================")

    # Thực hiện 3-Way Handshake (Slide 101)
    session, sock = raw_connect(server_ip, server_port, client_port, interface)
    if not session or not sock:
        print("[-] Bắt tay 3 bước THẤT BẠI!")
        sys.exit(1)

    print(f"[+] Bắt tay 3 bước THÀNH CÔNG! Trạng thái: {session.state}")
    print(f"[+] Local Seq: {session.server_seq} | Peer Ack Seq: {session.client_seq}")

    # Gửi dữ liệu nếu có truyền qua command-line
    if args.message:
        payload = args.message.encode("utf-8")
        print(f"\n[*] Gửi dữ liệu ({len(payload)} bytes)...")
        bytes_sent = run_conn_send(sock, session, payload)
        print(f"[+] Đã gửi: {bytes_sent} bytes")

        print("[*] Đang chờ phản hồi từ Server...")
        resp = run_conn_recv(sock, session)
        if resp:
            print(f"[+] Nhận phản hồi ({len(resp)} bytes):\n{resp.decode('utf-8', errors='replace')}")

    # Vòng lặp tương tác dòng lệnh (Interactive CLI)
    try:
        print("\n--- Nhập tin nhắn để gửi (Gõ 'http' để test gửi HTTP GET, hoặc 'exit' để thoát) ---")
        while True:
            msg = input("client> ").strip()
            if not msg:
                continue
            if msg.lower() in ("exit", "quit"):
                break

            if msg.lower() in ("http", "get"):
                payload = f"GET / HTTP/1.1\r\nHost: {server_ip}\r\nConnection: close\r\n\r\n".encode("utf-8")
                print(f"[*] Gửi HTTP GET Request chuẩn...")
            else:
                payload = msg.encode("utf-8")
            bytes_sent = run_conn_send(sock, session, payload)
            print(f"[+] Đã gửi {bytes_sent} bytes. Đang chờ phản hồi...")

            resp = run_conn_recv(sock, session)
            if resp:
                print(f"[Server phản hồi]: {resp.decode('utf-8', errors='replace')}")
            else:
                print("[-] Không có phản hồi hoặc kết nối đã đóng.")
                break

    except KeyboardInterrupt:
        print("\n[*] Ngắt bởi người dùng.")
    finally:
        print("[*] Đóng kết nối...")
        close_connection(sock, session)
        print("[+] Kết nối đã đóng.")


if __name__ == "__main__":
    main()
