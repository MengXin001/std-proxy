import socket
import sys
import ssl
import time
import csv
import threading
import logging
from argparse import ArgumentParser

logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def handle_connection(conn, addr, results, retaddr):
    start_time = time.time()
    total_length = 0
    truncated_payload = ""

    try:
        while True:
            data = conn.recv(2048)
            if not data:
                break
            total_length += len(data)
            if total_length == len(data):
                truncated_payload = data.hex()

            logging.debug("Recv: %s: %s", addr, data.hex())

        end_time = time.time()
        duration = end_time - start_time
        results.append(
            [
                str(int(start_time * 1000)),
                str(retaddr[0]),
                retaddr[1],
                addr[0],
                str(addr[1]),
                truncated_payload,
                str(total_length),
                f"{duration:.3f}",
            ]
        )
    except Exception as e:
        logging.error(f"Error handling connection {addr}: {e}")
    finally:
        conn.close()


def main():
    parser = ArgumentParser(description="Sink server to receive TCP/TLS connections")
    parser.add_argument(
        "-ip",
        default="0.0.0.0",
        help="IP address to listen on. (default listen on 0.0.0.0 and ::/0)",
    )
    parser.add_argument(
        "-p",
        default="12345",
        help="Comma-separated list of addrs to listen on. eg. 3000,4000-4002",
    )
    parser.add_argument("-timeout", default=60, type=int, help="Timeout value")
    parser.add_argument("-out", default="output.csv", help="Output CSV file")
    parser.add_argument("-log", default="", help="Log to file")
    parser.add_argument(
        "-header", default=True, action="store_true", help="Print CSV header"
    )
    parser.add_argument(
        "-tls", default=False, action="store_true", help="Listen with TLS."
    )
    parser.add_argument(
        "-tlsCert",
        default="server.crt",
        help="specify TLS certificate file (PEM) for listening.",
    )
    parser.add_argument(
        "-tlsKey",
        default="server.key",
        help="specify TLS certificate file (PEM) for listening.",
    )

    args = parser.parse_args()

    if args.log:
        logging.basicConfig(filename=args.log, level=logging.DEBUG)

    addrs = []
    for part in args.p.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            addrs.extend(range(start, end + 1))
        else:
            addrs.append(int(part))

    with open(args.out, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if args.header:
            writer.writerow(
                [
                    "ts",
                    "localIP",
                    "localPort",
                    "remoteIP",
                    "remotePort",
                    "truncatedPayload",
                    "len",
                    "duration",
                ]
            )

        results = []
        for addr in addrs:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((args.ip, addr))
            sock.listen(5)

            logging.info(
                f"TCP server is listening on {args.ip}:{addr}, timeout value: {args.timeout}s"
            )

            if args.tls:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=args.tlsCert, keyfile=args.tlsKey)
                sock = context.wrap_socket(sock, server_side=True)
                logging.info(
                    f"TLS server is listening on {args.ip}:{addr}, timeout value: {args.timeout}s"
                )

            def accept_connections():
                while True:
                    conn, addr = sock.accept()
                    conn.settimeout(args.timeout)
                    retaddr = sock.getsockname()
                    threading.Thread(
                        target=handle_connection, args=(conn, addr, results, retaddr)
                    ).start()

            thread = threading.Thread(target=accept_connections)
            thread.setDaemon(True)
            thread.start()
        while True:
            try:
                if results:
                    row = results.pop(0)
                    writer.writerow(row)
                    csvfile.flush()  # todo flush automatically
            except KeyboardInterrupt:
                logging.info("sink server exited gracefully")
                sys.exit(0)
