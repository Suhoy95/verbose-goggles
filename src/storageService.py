import time
import os
from os.path import (
    getsize,
    join,
    normpath,
    isfile,
    isdir,
    exists
)
from threading import Thread
import logging

import rpyc

import src.dfs as dfs


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
            if not ns.isActualFile(file):
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

    def rm(self, path):
        pass
