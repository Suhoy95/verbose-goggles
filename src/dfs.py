import json
import hashlib
import logging
from os.path import (
    basename,
    dirname
)
from typing import Dict, Set


DIRECTORY = 'DIRECTORY'
FILE = 'FILE'


def File(path, size, filehash):
    return {
        'path': path,
        'type': FILE,
        'size': size,
        'hash': filehash,
    }


def Dir(path, files=None):
    if files is None:
        files = []

    return {
        'path': path,
        'type': DIRECTORY,
        'files': files
    }


def Storage(name, addr, capacity):
    return {
        'name': name,
        'addr': addr,
        'free': capacity,
        'capacity': capacity,
    }


def filehash(filename):
    hash_sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


class Tree:
    def __init__(self, jsonfile):
        self._jsonfile = jsonfile
        try:
            with open(jsonfile, "r") as f:
                self._tree = json.load(f)
        except Exception:
            logging.warn("Could not read from jsonfile, new created")
            self._tree = dict()
            self._tree['/'] = Dir('/')
            self.save()

    def refresh(self):
        with open(self._jsonfile, "r") as f:
            self._tree = json.load(f)

    def save(self):
        # TODO: write to tmp-file and then rename to self._jsonfile
        # currently it is dangeros non-atomic operation
        # termination of which will buries whole DFS
        with open(self._jsonfile, "w") as f:
            f.write(json.dumps(self._tree, indent=4))

    def add(self, stat):
        name = basename(stat['path'])
        dfs_dir = dirname(stat['path'])
        dstat = self.get(dfs_dir)
        dstat['files'].append(name)
        self._tree[stat['path']] = stat
        self.save()

    def get(self, path) -> dict:
        # by this way, if client gets the stat of dir or file,
        # he can remotely change the internal Tree state
        # but from client side we intrested these structure only as read-only, so OK
        return self._tree.get(path, None)

    def pop(self, path):
        f = self._tree.pop(path, None)
        if f is None:
            return None

        name = basename(path)
        dfs_dir = dirname(path)
        dstat = self._tree.get(dfs_dir)
        dstat['files'].remove(name)
        self.save()
        return f
