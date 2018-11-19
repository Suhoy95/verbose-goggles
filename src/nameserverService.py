import logging
from typing import Dict, Set

import rpyc

import dfs


class NameserverService(rpyc.Service):
    def __init__(self,
                 Tree: dfs.Tree,
                 Location: Dict[str, set],
                 NeedReplication: Set[str],
                 ActiveStorages: set):

        rpyc.Service.__init__(self)
        self._Tree = Tree
        self._Location = Location
        self._NeedReplication = NeedReplication
        self._ActiveStorages = ActiveStorages
        self._storage = None

    def on_connect(self, conn):
        pass

    def on_disconnect(self, conn):
        if self._storage is None:
            return

        logging.info('Storage "%s" has disconnected', self._storage['name'])
        self._ActiveStorages.pop(self)
        for filepath, storages in self._Location.items():
            storages.pop(self)
            if len(storages) == 1:
                self._NeedReplication.add(filepath)
        self.tryReplicate()

#
#   method for storage(s)
#
    def exposed_upgrade(self, storage):
        """ Exclaim that connection is storage """
        self._storage = storage

    def exposed_isActualFile(self, file):
        """ Storage asks should it keeps the file or not """
        f = self._Tree.get(file['path'])
        if (f is None or
            f['type'] == dfs.DIRECTORY or
            f['hash'] != file['hash'] or
                f['size'] != file['size']):
            return False

        self._Location[f['path']].add(self)
        return True

    def exposed_isActualDir(self, path):
        d = self._Tree.get(path)
        return (d is not None and
                d['type'] == dfs.DIRECTORY)

    def exposed_activate(self):
        """ Exclaim that storage become active """
        self._ActiveStorages.add(self)
        self.tryReplicate()
        logging.info('Storage "%s" has activated', self._storage['name'])

    def exposed_write_notification(self, file):
        # TODO: add global mutex

        f = self._Tree.get(file['path'])

        if f is not None and (f['hash'] == file['hash'] and f['size'] == file['size']):
            self._Location[f['path']].add(self)
            return

        # file was updated, we remove previous file
        # and go to situation when file was created
        if f is not None:
            # TODO: not delete file on current storage, because it has been overwritten
            self.rm(file)

        # file was created
        self._Tree.add(file)
        self._Location[f['path']].add(self)
        self._NeedReplication.add(f['path'])
        self._storage['free'] -= file['size']
        # TODO: mutex unlock

        self.tryReplicate()

    def tryReplicate(self):
        """ Trying to find new storage to backup the file """
        # remove files, which has become replicated
        notNeed = set()
        for filepath in self._NeedReplication:
            if len(self._Location.get(filepath, [])) > 1:
                notNeed.add(filepath)

        self._NeedReplication.difference_update(notNeed)

        for filepath in self._NeedReplication:
            logging.info('Trying to replicate "%s"', filepath)
            # TODO:
            pass

    def rm(self, file):
        self._Tree.pop(file['path'])
        self._Location.pop(file['path'], None)
        for s in self._Location.get(file['path'], set()):
            addr = s._storage['addr']
            s._storage['free'] += file['size']
            try:
                c = rpyc.connect(addr[0], port=addr[1])
                c.root.rm(file['path'])
            except:
                pass

#
#   method for the Client
#
    def du(self):
        # return information about
        # self._ActiveStorages
        pass