import time
import logging
import argparse
import threading

from rpyc.utils.helpers import classpartial
from rpyc.utils.authenticators import SSLAuthenticator
from rpyc.utils.server import ThreadedServer


import src.dfs as dfs
from src.nameserverService import NameserverService


def parse_args():
    parser = argparse.ArgumentParser(add_help="Start Nameserver")
    parser.add_argument("--hostname")
    parser.add_argument("--port", type=int)
    parser.add_argument("--treejson")

    parser.add_argument("--ca_cert")
    parser.add_argument("--keyfile")
    parser.add_argument("--certfile")

    return parser.parse_args()


def main(args):
    sslAuth = SSLAuthenticator(
        keyfile=args.keyfile,
        certfile=args.certfile,
        ca_certs=args.ca_cert,
    )

    # Global state of Nameserver
    Tree = dfs.Tree(jsonfile=args.treejson)
    Location = dict()
    NeedReplication = set()
    ActiveStorages = set()
    GlobalLock = threading.Lock()

    for path, file in Tree._tree.items():
        if file['type'] == dfs.FILE:
            Location[path] = set()
            NeedReplication.add(path)


    service = classpartial(NameserverService,
                           Tree=Tree,
                           Location=Location,
                           NeedReplication=NeedReplication,
                           ActiveStorages=ActiveStorages,
                           GlobalLock=GlobalLock,
                           args=args,
                           )

    server = ThreadedServer(
        service=service,
        hostname=args.hostname,
        port=args.port,
        authenticator=sslAuth,
        protocol_config={
            'allow_public_attrs': True,
        })

    server.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    main(args)
