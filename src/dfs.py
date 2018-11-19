import enum
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


def Dir(path, files=[]):
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
        # TODO: loading from file
        self._tree = {}

    def add(self, file):
        # TODO: putting to the structure and saving to the file
        pass

    def get(self, path) -> dict:
        self._tree.get(path, None)

    def pop(self, path):
        self._tree.pop(path, None)
        # TODO: saving to the file