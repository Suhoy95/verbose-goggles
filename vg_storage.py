import os
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
    parser.add_argument("--name", default=None)
    parser.add_argument("--hostname", default=None, required=False)
    parser.add_argument("--port", type=int, default=None, required=False)
    parser.add_argument("--capacity", type=int, default=None, required=False)

    parser.add_argument("--ca_cert")
    parser.add_argument("--keyfile", default=None, required=False)
    parser.add_argument("--certfile", default=None, required=False)

    parser.add_argument("--ns_hostname", default=None, required=False)
    parser.add_argument("--ns_port", default=None, required=False)

    parser.add_argument("--rootpath")

    args = parser.parse_args()

    # Try extract ARGS from ENVIRONMENT if we are in the docker
    if args.name is None:
        args.name = os.environ['name']
    if args.hostname is None:
        args.hostname = os.environ['hostname']
    if args.port is None:
        args.port = int(os.environ['port'])
    if args.capacity is None:
        args.capacity = int(os.environ['capacity'])

    if args.keyfile is None:
        args.keyfile = "certs/{0}/{0}.key".format(args.name)
    if args.certfile is None:
        args.certfile = "certs/{0}/{0}.crt".format(args.name)

    if args.ns_hostname is None:
        args.ns_hostname = os.environ['ns_hostname']
    if args.ns_port is None:
        args.ns_port = int(os.environ['ns_port'])

    return args


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
