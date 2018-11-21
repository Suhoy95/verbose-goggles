import time
import os
import hashlib
from os import (
    remove,
    mkdir,
    rmdir,
)
from os.path import (
    getsize,
    join,
    normpath,
    isfile,
    isdir,
    exists,
)
import threading
from threading import Thread
import logging
import shutil

import rpyc

import src.dfs as dfs
from src.nameserverService import NameserverService

GlobalLock = threading.Lock()


def walkOnStorage(rootPath: str, curdir: str, ns: NameserverService):
    d = normpath(join(rootPath, '.' + curdir))

    for name in os.listdir(d):
        fullpath = normpath(join(d, name))
        dfs_path = normpath(join(curdir, name))

        if isfile(fullpath):
            file = dfs.File(
                dfs_path,
                getsize(fullpath),
                dfs.filehash(fullpath)
            )
            if not ns.tryPublishFile(file):
                logging.warn("Remove old %s", fullpath)
                os.remove(fullpath)  # <======================= rm
        elif isdir(fullpath):
            walkOnStorage(rootPath, dfs_path, ns)
            if not ns.isdir(dfs_path):
                logging.warn("Remove dir %s", fullpath)
                os.rmdir(fullpath)  # <===================== rmdir
        else:
            raise ValueError("Bad file {}".format(fullpath))


def walkOnDfs(rootPath: str, dfs_dir: str, ns: NameserverService):
    """ Recreate directory according with dfs """
    for name in ns.listdir(dfs_dir):
        dfs_path = join(dfs_dir, name)
        if ns.isdir(dfs_path):
            fullpath = normpath(join(rootPath, '.' + dfs_path))
            if not exists(fullpath):
                os.mkdir(fullpath)
            walkOnDfs(rootPath, dfs_path, ns)


def becomeStorage(args, ns: NameserverService):
    ns.upgrade(
        name=args.name,
        hostname=args.hostname,
        port=args.port,
        capacity=args.capacity
    )
    walkOnStorage(args.rootpath, '/', ns)
    walkOnDfs(args.rootpath, '/', ns)
    ns.activate()


def setWatchDog(nsConn: rpyc.Connection, server):
    def checkNsConnection():
        while True:
            time.sleep(10)
            try:
                nsConn.ping("Hello")
            except:
                logging.fatal("Lost connection with nameserver")
                server.close()
                exit(-1)

    t = Thread(target=checkNsConnection)
    t.daemon = True
    t.start()


class StorageService(rpyc.Service):

    def __init__(self, args, ns: NameserverService):
        self._args = args
        self._rootpath = args.rootpath
        self._ns = ns

    def exposed_pull(self, src_name, src_hostname, src_port, filepath):
        with GlobalLock:
            logging.info('Pulling %s from "%s"', filepath, src_name)
            conn = rpyc.ssl_connect(src_hostname, port=src_port,
                                    keyfile=self._args.keyfile,
                                    certfile=self._args.certfile,
                                    ca_certs=self._args.ca_cert,
                                    config={
                                        'sync_request_timeout': -1,
                                    })
            targetFile = normpath(join(self._rootpath, '.' + filepath))
            with conn.root.open(filepath, "br") as fsrc:
                with open(targetFile, "bw") as fdst:
                    shutil.copyfileobj(fsrc, fdst)
            conn.close()

    def exposed_open(self, filepath, mode):
        with GlobalLock:
            logging.debug("open:[%s] %s ", mode, filepath)
            fullpath = normpath(join(self._rootpath, '.' + filepath))
            return open(fullpath, mode)

    def exposed_write_fileobj(self, filepath, fsrc):
        with GlobalLock:
            logging.debug("write_fileobj: %s", filepath)
            fullpath = normpath(join(self._rootpath, '.' + filepath))
            sha256 = hashlib.sha256()
            size = 0
            with open(fullpath, "bw") as fdst:
                while 1:
                    buf = fsrc.read(1024)
                    if not buf:
                        break
                    size += len(buf)
                    sha256.update(buf)
                    fdst.write(buf)

        # release lock early as soon other replicas come to us after notification
        self._ns.exposed_write_notification(
            filepath=filepath,
            filehash=sha256.hexdigest(),
            size=size
        )

    def exposed_rm(self, filepath):
        with GlobalLock:
            logging.debug("rm: %s", filepath)
            fullpath = normpath(join(self._rootpath, '.' + filepath))
            remove(fullpath)

    def exposed_mkdir(self, dirpath):
        with GlobalLock:
            logging.debug("mkdir: %s", dirpath)
            fullpath = normpath(join(self._rootpath, '.' + dirpath))
            mkdir(fullpath)

    def exposed_rmdir(self, dirpath):
        with GlobalLock:
            logging.debug("rmdir: %s", dirpath)
            fullpath = normpath(join(self._rootpath, '.' + dirpath))
            rmdir(fullpath)
