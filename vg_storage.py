import logging
import argparse
from threading import Thread

import rpyc
from rpyc.utils.authenticators import SSLAuthenticator
from rpyc.utils.server import ThreadedServer

import src.dfs as dfs
from src.storageService import (
    StorageService,
    recoverFiles,
    setWatchDog
)


def parse_args():
    parser = argparse.ArgumentParser(add_help="Storage server")
    parser.add_argument("--name")
    parser.add_argument("--hostname")
    parser.add_argument("--port", type=int)
    parser.add_argument("--capacity", type=int)

    parser.add_argument("--ca_cert")
    parser.add_argument("--keyfile")
    parser.add_argument("--certfile")

    parser.add_argument("--ns_hostname")
    parser.add_argument("--ns_port")

    parser.add_argument("--rootpath")

    return parser.parse_args()


def main(args):
    logging.basicConfig(level=logging.DEBUG)

    try:
        nsConn = rpyc.ssl_connect(
            args.ns_hostname, port=args.ns_port,
            keyfile=args.keyfile,
            certfile=args.certfile,
            ca_certs=args.ca_cert,
            config={
                'sync_request_timeout': -1,
            }
        )
    except Exception:
        logging.fatal("Could not connect too the nameserver")
        exit(-1)

    def becomeStorage():
        nsConn.root.upgrade(
            name=args.name,
            hostname=args.hostname,
            port=args.port,
            capacity=args.capacity
        )
        recoverFiles(args.rootpath, nsConn.root)
        nsConn.root.activate()

    t = Thread(target=becomeStorage)
    t.daemon = True
    t.start()


    sslAuth = SSLAuthenticator(
        keyfile=args.keyfile,
        certfile=args.certfile,
        ca_certs=args.ca_cert,
    )

    service = StorageService(args, nsConn.root)

    server = ThreadedServer(
        service=service,
        hostname=args.hostname,
        port=args.port,
        authenticator=sslAuth,
        protocol_config={
            'allow_public_attrs': True,
        })

    setWatchDog(nsConn, server)
    server.start()


if __name__ == "__main__":
    args = parse_args()
    main(args)
