import sys
import time
import csv
import queue
import logging
import requests
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

from utils._config import *

TIMEOUT = 5
REPEAT = 3
SLEEP = 1
WAIT = 2
MAX_NUM_TIMEOUT = 2
INTERVAL = 1
MAX_NUM_WORKERS = 10

logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def worker(id, jobs, results, doh_server):
    while True:
        job = jobs.get()
        if job is None:
            break

        domain = job["domain"]
        logging.info(
            f"worker {id} is testing domain {domain} with DoH server {doh_server}"
        )

        count_success = 0
        consecutive_timeout = 0
        total_timeout = 0
        code = ""

        for _ in range(REPEAT):
            try:
                params = {
                    "name": domain,
                    "type": "A",
                    "cd": "false",
                }
                headers = {"Accept": "application/dns-json"}
                response = requests.get(
                    doh_server, params=params, headers=headers, timeout=TIMEOUT
                )

                if response.status_code == 200:
                    result = response.json()
                    if "Answer" in result:
                        for answer in result["Answer"]:
                            logging.info(f"响应: {answer['data']}")
                        count_success += 1
                    else:
                        code = "no_answer"
                        total_timeout += 1
                else:
                    code = f"error_{response.status_code}"
                    total_timeout += 1
            except requests.exceptions.Timeout:
                consecutive_timeout += 1
                total_timeout += 1
                code = "timeout"
            except Exception as e:
                code = str(e)
                break

            time.sleep(SLEEP)

        jobs.task_done()

        affected = "unknown"
        if count_success == 0:
            affected = "unknown"
        elif consecutive_timeout >= MAX_NUM_TIMEOUT:
            affected = "true"
        elif count_success == REPEAT:
            affected = "false"

        results.put(
            [
                time.time(),
                domain,
                count_success,
                total_timeout,
                consecutive_timeout,
                code,
                affected,
            ]
        )
        results.task_done()
        logging.info(f"worker {id} finished testing domain {domain}")


def main():
    parser = ArgumentParser(
        description="Test if domains are affected by DNS blocking using DoH (DNS over HTTPS)."
    )
    parser.add_argument(
        "-host", type=str, default=DOH_SERVER, help="DoH server to send requests to"
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
        default=REPEAT,
        help="repeat up to this number of queries for each domain.",
    )
    parser.add_argument(
        "-try",
        type=int,
        default=MAX_NUM_TIMEOUT,
        help="mark a domain as affected if this number of consecutive queries all timeout.",
    )
    parser.add_argument(
        "-timeout", type=int, default=TIMEOUT, help="timeout value for DoH requests."
    )
    parser.add_argument(
        "-worker",
        type=int,
        default=MAX_NUM_WORKERS,
        help="number of workers in parallel.",
    )
    parser.add_argument("files", nargs="*", help="List of files containing domains.")
    args = parser.parse_args()

    if args.log:
        logging.basicConfig(filename=args.log, level=logging.DEBUG)

    output_file = (
        sys.stdout if args.out == "" else open(args.out, "w", encoding="utf-8")
    )
    writer = csv.writer(output_file)
    writer.writerow(
        [
            "endTime",
            "domain",
            "countSuccess",
            "totalTimeout",
            "consecutiveTimeout",
            "code",
            "affected",
        ]
    )

    jobs = queue.Queue()
    results = queue.Queue()

    with ThreadPoolExecutor(max_workers=args.worker) as executor:
        for i in range(args.worker):
            executor.submit(worker, i, jobs, results, args.host)

        domains = []
        for f in args.files:
            with open(f, "r") as file:
                for line in file:
                    domains.append(line.strip())

        for domain in domains:
            jobs.put({"domain": domain})

        jobs.join()
        for _ in range(args.worker):
            jobs.put(None)
        while not results.empty():
            result = results.get()
            writer.writerow(result)
            output_file.flush()
        output_file.close()
        logging.info("all domain testing finished")


if __name__ == "__main__":
    main()
