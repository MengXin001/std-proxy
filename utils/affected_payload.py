import sys
import time

import csv
import queue
import socket
import logging
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

from utils._config import *

logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def worker(id, jobs, results, addr):
    while True:
        job = jobs.get()
        if job is None:
            break

        payload = job["payload"]
        port = job["port"]
        host = f"{addr}:{port}"

        logging.info(f"worker {id} is testing payload {payload}")

        count_success = 0
        consecutive_timeout = 0
        total_timeout = 0
        code = ""

        for _ in range(REPEAT):
            try:
                with socket.create_connection((addr, port), timeout=TIMEOUT) as conn:
                    conn.send(bytes.fromhex(payload))
                    count_success += 1
                    consecutive_timeout = 0
                    time.sleep(SLEEP)
            except socket.timeout:
                consecutive_timeout += 1
                total_timeout += 1
                code = "timeout"
                time.sleep(WAIT)
            except Exception as e:
                code = str(e)
                break

            time.sleep(INTERVAL)
        jobs.task_done()
        affected = "unknown"
        if count_success == 0:
            affected = "unknown"
        elif consecutive_timeout == MAX_NUM_TIMEOUT:
            affected = "true"
        elif count_success == REPEAT:
            affected = "false"

        results.put(
            [
                time.time(),
                host,
                payload,
                count_success,
                total_timeout,
                consecutive_timeout,
                code,
                affected,
            ]
        )
        results.task_done()
        logging.info(f"worker {id} finished testing payload {payload} on {host}")


def main():
    parser = ArgumentParser(
        description="Test if payloads in FILE(s) are affected by the dynamic blocking. With no FILE, read standard input. By default, print results to stdout and log to stderr."
    )
    parser.add_argument(
        "-p",
        type=str,
        default="80",
        help="Comma-separated list of ports to which the program sends random payload. eg. 3000,4000-4002",
    )
    parser.add_argument(
        "-host", type=str, default="REDACTED_US_SERVER_IP", help="host to send to"
    )
    parser.add_argument(
        "-out", type=str, default="", help="output csv file.  (default stdout)"
    )
    parser.add_argument(
        "-log", type=str, default="", help="log to file.  (default stderr)"
    )
    parser.add_argument(
        "-repeat",
        type=int,
        default=25,
        help="repeatedly make up to this number of connections to each ip:port.",
    )
    parser.add_argument(
        "-try",
        type=int,
        default=5,
        help="mark an ip:port as affected if this number of consecutive connections all timeout.",
    )
    parser.add_argument(
        "-timeout", type=int, default=TIMEOUT, help="timeout value of TCP connections."
    )
    parser.add_argument(
        "-interval",
        type=int,
        default=INTERVAL,
        help="time interval between each connection to a ip:port.",
    )
    parser.add_argument(
        "-wait",
        type=int,
        default=WAIT,
        help="time interval between each connection, when a ip:port timeout.",
    )
    parser.add_argument(
        "-sleep",
        type=int,
        default=SLEEP,
        help="time interval between sending a probe and closing the connection. This value doesn't affect the -interval between each connection.",
    )
    parser.add_argument(
        "-worker",
        type=int,
        default=MAX_NUM_WORKERS,
        help="number of workers in parallel.",
    )
    parser.add_argument("files", nargs="*", help="List of files containing payloads.")
    args = parser.parse_args()

    if args.log:
        logging.basicConfig(filename=args.log, level=logging.DEBUG)

    output_file = sys.stdout if args.out == "" else open(args.out, "w")
    writer = csv.writer(output_file)
    writer.writerow(
        [
            "endTime",
            "addr",
            "payload",
            "countSuccess",
            "totalTimeout",
            "consecutiveTimeout",
            "code",
            "affected",
        ]
    )

    addrs = []
    for part in args.p.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            addrs.extend(range(start, end + 1))
        else:
            addrs.append(int(part))

    jobs = queue.Queue()
    results = queue.Queue()

    with ThreadPoolExecutor(max_workers=args.worker) as executor:
        for i in range(args.worker):
            executor.submit(worker, i, jobs, results, args.host)

        payloads = []
        for f in args.files:
            with open(f, "r") as file:
                for line in file:
                    payloads.append(line.strip())

        for payload in payloads:
            for addr in addrs:
                jobs.put({"payload": payload, "port": addr})
        jobs.join()
        for _ in range(args.worker):
            jobs.put(None)
        while not results.empty():
            result = results.get()
            writer.writerow(result)
            output_file.flush()
        output_file.close()
        logging.info("all payload testing finished")
