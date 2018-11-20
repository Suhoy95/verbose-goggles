#!/usr/bin/env python3
import argparse
import os
import traceback
import logging
from os import path
from os.path import (
    abspath,
)

import rpyc

from src.clientcmd import (
    ClientCmd,
    VgException
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local",
                        default=os.getcwd(),
                        help="""
                        local directory for exchanging file with DFS.
                        Current Working Directory by default.
                        """,
                        )
    parser.add_argument("--logfile",
                        default=None,
                        help="""Path to log file""",
                        )
    parser.add_argument("--loglevel",
                        default="WARNING",
                        help="Set logging level (DEBUG, INFO, WARNING, ERROR)",
                        )
    parser.add_argument("--ns_hostname",
                        help="""hostname of nameserver"""
                        )
    parser.add_argument("--ns_port",
                        type=int,
                        help="port of nameserver"
                        )

    parser.add_argument("--ca_cert")
    parser.add_argument("--keyfile")
    parser.add_argument("--certfile")

    args = parser.parse_args()

    if path.isdir(args.local):
        args.local = path.abspath(args.local)
    else:
        print("""ERROR:
ERROR: --local is not a local directory
ERROR:""")
        parser.print_help()
        exit(-1)

    numeric_level = getattr(logging, args.loglevel, None)
    if not isinstance(numeric_level, int):
        print("""ERROR:
ERROR: Invalid logging level: {}
ERROR: """.format(args.loglevel))
        exit(-1)

    # we will change CWD to local
    args.ca_cert = abspath(args.ca_cert)
    args.keyfile = abspath(args.keyfile)
    args.certfile = abspath(args.certfile)

    logging.basicConfig(
        level=numeric_level,
        filename=args.logfile,
        format='%(asctime)s %(levelname)s %(module)s | %(message)s')

    return args


if __name__ == "__main__":
    args = parse_args()

    logging.debug("Starting client:")
    logging.debug('--local %s', args.local)
    logging.debug('--logfile %s',
                  args.logfile if args.logfile else 'NULL')  # pay respect to C
    logging.debug('--loglevel %s', args.loglevel)
    logging.debug('--ns_hostname %s', args.ns_hostname)
    logging.debug('--ns_port %s', args.ns_port)

    quit = False

    clientCmd = None
    try:
        conn = rpyc.ssl_connect(
            args.ns_hostname, port=args.ns_port,
            keyfile=args.keyfile,
            certfile=args.certfile,
            ca_certs=args.ca_cert,
            config={
                'sync_request_timeout': -1,
            }
        )
        clientCmd = ClientCmd(conn.root, args.local, args)
    except:
        print("Faild to connect to {}".format(args.ns_hostname))
        exit(-1)

    while not quit:
        try:
            clientCmd.cmdloop()
            quit = True
        except KeyboardInterrupt:
            print("Use C^D to exiting")
        except VgException as e:
            print(e)
        except Exception as e:
            print("[ERROR] ", type(e), e)
            logging.exception("[ERROR]")
