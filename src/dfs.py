import json
import hashlib
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
        with open(jsonfile, "r") as f:
            self._tree = json.load(f)

    def refresh(self):
        with open(self._jsonfile, "r") as f:
            self._tree = json.load(f)

    def save(self):
        with open(self._jsonfile, "w") as f:
            f.write(json.dumps(self._tree, indent=4))

    def add(self, file):
        self._tree[file['path']] = file
        self.save()

    def get(self, path) -> dict:
        return self._tree.get(path, None)

    def pop(self, path):
        self._tree.pop(path, None)
        self.save()
