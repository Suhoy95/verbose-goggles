import json
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


class Tree:
    def __init__(self, jsonfile):
        self._jsonfile = jsonfile
        with open(jsonfile, "r") as f:
            self._tree = json.load(f)

    def refresh(self):
        with open(self._jsonfile, "r") as f:
            self._tree = json.load(f)

    def add(self, file):
        # TODO: putting to the structure and saving to the file
        pass

    def get(self, path) -> dict:
        self._tree.get(path, None)

    def pop(self, path):
        self._tree.pop(path, None)
        # TODO: saving to the file
