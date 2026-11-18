"""Transfer a selected file over the project's raw TCP transport (Linux/root)."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import socket
import struct
import subprocess
import time

from streaprous_socket import streaprous_raw_connection as transport


ROOT = Path(__file__).resolve().parent
MAX_FILE = 16 * 1024 * 1024


def recv_exact(sock, conn, size, read_size=16384, delay=0):
    result = bytearray()
    while len(result) < size:
        chunk = transport.run_conn_recv(sock, conn, min(read_size, size - len(result)))
        if not chunk:
            raise ConnectionError(f"Connection closed after {len(result)}/{size} bytes")
        result.extend(chunk)
        if delay:
            time.sleep(delay)
    return bytes(result)


def send_bytes(sock, conn, data):
    sent = transport.run_conn_send(sock, conn, data)
    if sent != len(data):
        raise ConnectionError(f"Transport sent {sent}/{len(data)} bytes")


def send_json(sock, conn, value):
    payload = json.dumps(value).encode("utf-8")
    send_bytes(sock, conn, struct.pack("!I", len(payload)) + payload)


def recv_json(sock, conn):
    size = struct.unpack("!I", recv_exact(sock, conn, 4))[0]
    if not 0 < size <= 4096:
        raise ValueError("Invalid metadata length")
    return json.loads(recv_exact(sock, conn, size).decode("utf-8"))


@contextmanager
def rst_rule(port):
    # Preserve existing rules; remove only the rule added by this process.
    rule = ["OUTPUT", "-p", "tcp", "--sport", str(port),
            "--tcp-flags", "RST", "RST", "-j", "DROP"]
    exists = subprocess.run(["iptables", "-C", *rule], capture_output=True).returncode == 0
    if not exists:
        subprocess.run(["iptables", "-A", *rule], check=True)
    try:
        yield
    finally:
        if not exists:
            subprocess.run(["iptables", "-D", *rule], check=False)


def choose_file(filename):
    if filename:
        path = Path(filename).resolve()
    else:
        files = sorted((ROOT / "test_data").glob("*.bin"))
        if not files:
            raise ValueError("No files in test_data; use --file PATH")
        for index, candidate in enumerate(files, 1):
            print(f"{index}. {candidate.name} ({candidate.stat().st_size} bytes)")
        choice = int(input("Choose file number: "))
        if not 1 <= choice <= len(files):
            raise ValueError("Invalid file number")
        path = files[choice - 1]
    if not path.is_file() or not 0 <= path.stat().st_size <= MAX_FILE:
        raise ValueError("Choose a regular file of at most 16 MiB")
    return path


def send_file(args, sock, conn, path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    send_json(sock, conn, {"name": path.name, "size": len(data), "sha256": digest})
    if recv_json(sock, conn).get("status") != "ready":
        raise ConnectionError("Receiver is not ready")
    started = time.monotonic()
    # One application write keeps data available for cwnd/rwnd experiments.
    send_bytes(sock, conn, data)
    receipt = recv_json(sock, conn)
    elapsed = time.monotonic() - started
    if (receipt.get("status") != "ok" or receipt.get("sha256") != digest
            or receipt.get("size") != len(data)):
        raise ValueError(f"Receiver verification failed: {receipt}")
    print(f"SUCCESS: receiver verified {len(data)} bytes, SHA-256={digest}")
    print(f"Transfer + verification: {elapsed:.3f}s; {len(data)/max(elapsed, 1e-9)/1024:.1f} KiB/s")
    send_json(sock, conn, {"status": "receipt_received"})


def receive_file(args, sock, conn):
    key = (conn.client_ip, conn.client_port)
    with transport.connections_lock:
        current = transport.connections[key]
        transport.connections[key] = current._replace(rcv_buffer_size=args.recv_buffer)
    meta = recv_json(sock, conn)
    size = meta["size"]
    name = meta["name"]
    if (type(size) is not int or not 0 <= size <= MAX_FILE
            or not isinstance(name, str) or Path(name).name != name
            or name in ("", ".", "..") or not isinstance(meta["sha256"], str)):
        raise ValueError("Invalid file metadata")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Unique name prevents overwriting earlier transfers.
    destination = output / f"{time.time_ns()}_{name}"
    print(f"Receiving {name}: {size} bytes; buffer={args.recv_buffer}, "
          f"hold={args.hold}s, read={args.read_size} bytes/{args.read_delay}s")
    send_json(sock, conn, {"status": "ready"})
    # Transport receiver stays active: rwnd can reach zero while the app sleeps.
    time.sleep(args.hold)
    data = recv_exact(sock, conn, size, args.read_size, args.read_delay)
    digest = hashlib.sha256(data).hexdigest()
    verified = digest == meta["sha256"]
    if verified:
        with destination.open("xb") as out:
            out.write(data)
    send_json(sock, conn, {"status": "ok" if verified else "hash_mismatch",
                           "size": len(data), "sha256": digest})
    recv_json(sock, conn)  # Keep connection alive until sender consumes receipt.
    if not verified:
        raise ValueError("SHA-256 mismatch; file not saved")
    print(f"SUCCESS: saved {destination}\nSHA-256={digest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sender = sub.add_parser("send", help="Choose and send a file")
    sender.add_argument("--peer-ip", required=True)
    sender.add_argument("--peer-port", type=int, default=9001)
    sender.add_argument("--local-port", type=int, default=22240)
    sender.add_argument("--interface", help="Local NIC, e.g. enp0s3 or eth0")
    sender.add_argument("--file", help="Omit to choose a sample interactively")
    receiver = sub.add_parser("receive", help="Receive one file, verify and exit")
    receiver.add_argument("--listen-ip", required=True, help="Receiver's LAN IPv4")
    receiver.add_argument("--port", type=int, default=9001)
    receiver.add_argument("--output", default=str(ROOT / "received_files"))
    receiver.add_argument("--recv-buffer", type=int, default=65536)
    receiver.add_argument("--read-size", type=int, default=16384)
    receiver.add_argument("--read-delay", type=float, default=0)
    receiver.add_argument("--hold", type=float, default=0)
    args = parser.parse_args()
    if args.mode == "receive":
        if (not 1024 <= args.recv_buffer <= 65536 or args.read_size <= 0
                or args.read_delay < 0 or args.hold < 0):
            parser.error("buffer must be 1024..65536, read-size > 0, delays >= 0")
        port = args.port
        path = None
    else:
        path = choose_file(args.file)
        port = args.local_port
    ports = [port, args.peer_port] if args.mode == "send" else [port]
    if any(not 1 <= value <= 65535 for value in ports):
        parser.error("ports must be 1..65535")
    sock = conn = None
    with rst_rule(port):
        try:
            if args.mode == "send":
                sock_conn, sock = transport.raw_connect(
                    args.peer_ip, args.peer_port, args.local_port, args.interface)
                conn = sock_conn
                if conn is None or sock is None:
                    raise ConnectionError("Handshake failed")
                send_file(args, sock, conn, path)
            else:
                sock = transport.create_raw_socket()
                print(f"Waiting for one file on {args.listen_ip}:{port}")
                conn = transport.accept(sock, args.listen_ip, port)
                receive_file(args, sock, conn)
        finally:
            if sock is not None:
                try:
                    if conn is not None:
                        transport.close_connection(sock, conn)
                finally:
                    transport.stop_packet_dispatcher(sock)
                    sock.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
        raise SystemExit(130)
    except (OSError, ValueError, ConnectionError, KeyError, TypeError,
            subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
