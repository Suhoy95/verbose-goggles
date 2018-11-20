import time
import os
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


GlobalLock = threading.Lock()


def walkOnStorage(rootPath, curdir, ns):
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
                os.remove(fullpath)  # <======================= rm
        elif isdir(fullpath):
            walkOnStorage(rootPath, dfs_path, ns)
            if not ns.isdir(dfs_path):
                os.rmdir(fullpath)  # <===================== rmdir
        else:
            raise ValueError("Bad file {}".format(fullpath))


def walkOnDfs(rootPath, dfs_dir, ns):
    """ Recreate directory according with dfs """
    for name in ns.listdir(dfs_dir):
        dfs_path = join(dfs_dir, name)
        if ns.isdir(dfs_path):
            fullpath = normpath(join(rootPath, '.' + dfs_path))
            if not exists(fullpath):
                os.mkdir(fullpath)
            walkOnDfs(rootPath, dfs_path, ns)


def recoverFiles(rootPath, ns):
    walkOnStorage(rootPath, '/', ns)
    walkOnDfs(rootPath, '/', ns)


def setWatchDog(nsConn, server):
    def checkNsConnection():
        while True:
            time.sleep(1)
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

    def __init__(self, args):
        self._args = args
        self._rootpath = args.rootpath

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
                with open(targetFile, "bw") as fout:
                    shutil.copyfileobj(fsrc, fout)
            conn.close()

    def exposed_open(self, filepath, mode):
        with GlobalLock:
            logging.debug("open:[%s] %s ", mode, filepath)
            fullpath = normpath(join(self._rootpath, '.' + filepath))
            return open(fullpath, mode)

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
