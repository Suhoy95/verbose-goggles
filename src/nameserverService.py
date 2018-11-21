import logging
import threading
import random
from os.path import (
    join
)
from typing import Dict, Set

import rpyc

import src.dfs as dfs


def tryReplicateFile(src, dst, filepath, args):
    addr = dst['addr']
    conn = rpyc.ssl_connect(addr[0], port=addr[1],
                            keyfile=args.keyfile,
                            certfile=args.certfile,
                            ca_certs=args.ca_cert,
                            config={'sync_request_timeout': -1, })
    conn.root.pull(src['name'], src['addr'][0], src['addr'][1], filepath)
    conn.close()


def rm_from(storage, dfs_path, args):
    addr = storage['addr']
    conn = rpyc.ssl_connect(addr[0], port=addr[1],
                            keyfile=args.keyfile,
                            certfile=args.certfile,
                            ca_certs=args.ca_cert,
                            config={'sync_request_timeout': -1, })
    conn.root.rm(dfs_path)
    conn.close()


def mkdir_on(storage, dfs_dir, args):
    addr = storage['addr']
    conn = rpyc.ssl_connect(addr[0], port=addr[1],
                            keyfile=args.keyfile,
                            certfile=args.certfile,
                            ca_certs=args.ca_cert,
                            config={'sync_request_timeout': -1, })
    conn.root.mkdir(dfs_dir)
    conn.close()


def rmdir_from(storage, dfs_dir, args):
    addr = storage['addr']
    conn = rpyc.ssl_connect(addr[0], port=addr[1],
                            keyfile=args.keyfile,
                            certfile=args.certfile,
                            ca_certs=args.ca_cert,
                            config={'sync_request_timeout': -1, })
    conn.root.rmdir(dfs_dir)
    conn.close()


class NameserverService(rpyc.Service):
    def __init__(self,
                 Tree: dfs.Tree,
                 Location: Dict[str, set],
                 NeedReplication: Set[str],
                 ActiveStorages: set,
                 GlobalLock: threading.Lock,
                 args):

        rpyc.Service.__init__(self)
        self._Tree = Tree
        self._Location = Location
        self._NeedReplication = NeedReplication
        self._ActiveStorages = ActiveStorages
        self._GlobalLock = GlobalLock
        self._args = args
        self._storage = None

    @property
    def name(self):
        if self._storage is None:
            return 'client'
        return self._storage['name']

    def on_connect(self, conn):
        pass

    def on_disconnect(self, conn):
        if self._storage is None:
            return

        with self._GlobalLock:
            logging.info('Storage "%s" has disconnected',
                         self._storage['name'])
            self._ActiveStorages.discard(self)
            for filepath, storages in self._Location.items():
                storages.discard(self)
                if len(storages) <= 1:
                    self._NeedReplication.add(filepath)
            self.tryReplicate()

#
#   method for storage(s)
#
    def exposed_upgrade(self, name: str, hostname: str, port: int, capacity: int):
        """ Exclaim that connection is storage """
        self._storage = dfs.Storage(
            name=name,
            addr=[hostname, port],
            capacity=capacity
        )
        logging.debug('upgrade: storage="%s"', self.name)

    def exposed_tryPublishFile(self, file):
        """ Storage asks should it keeps the file or not """
        if self._storage is None:
            raise ValueError("Client tries to publish files")

        logging.debug('isActualFile:%s:%s', self.name, file['path'])
        with self._GlobalLock:
            f = self._Tree.get(file['path'])
            if (f is None or
                f['type'] == dfs.DIRECTORY or
                f['hash'] != file['hash'] or
                    f['size'] != file['size']):
                return False

            self._storage['free'] -= file['size']
            self._Location[f['path']].add(self)
            return True

    def exposed_isdir(self, path):
        logging.debug('isdir:%s:%s', self.name, path)
        with self._GlobalLock:
            stat = self._Tree.get(path)
            return (stat is not None and
                    stat['type'] == dfs.DIRECTORY)

    def exposed_isfile(self, path):
        logging.debug('isfile:%s:%s', self.name, path)
        with self._GlobalLock:
            stat = self._Tree.get(path)
            return (stat is not None and
                    stat['type'] == dfs.FILE)

    def exposed_listdir(self, path):
        with self._GlobalLock:
            d = self._Tree.get(path)
            if d is None or d['type'] != dfs.DIRECTORY:
                raise ValueError("{} is not a directory".format(path))
            return list(d['files'])

    def exposed_activate(self):
        """ Exclaim that storage become active """
        if self._storage is None:
            raise ValueError("Client tries to activate")
        with self._GlobalLock:
            self._ActiveStorages.add(self)
            logging.info('Storage "%s" has activated', self.name)
            self.tryReplicate()

    def exposed_write_notification(self, filepath, filehash, size):
        """ event of client's writing file (create/update)"""
        if self._storage is None:
            raise ValueError("Write notification from client")

        logging.info("write_notification from %s. file: %s",
                     self.name, filepath)

        with self._GlobalLock:
            f = self._Tree.pop(filepath)

            # file was updated, we remove previous file
            # and go to situation when file was created
            if f is not None:
                # TODO: not delete file on current storage, because it has been overwritten
                # TODO: remove files
                for st in self._Location.get(filepath, set()):
                    st._storage['free'] += f['size']
                    if st != self:
                        try:
                            rm_from(st._storage, filepath, self._args)
                        except Exception as e:
                            logging.warn("Could not remove prev version of %s from %s. %s",
                                         filepath, st.name, e)

            # file was created
            self._Tree.add(dfs.File(filepath, size, filehash))
            self._Location[filepath] = {self}
            self._NeedReplication.add(filepath)
            self._storage['free'] -= size

            self.tryReplicate()

    def tryReplicate(self):
        """
            Trying to find new storage to backup the file
            Call it under _GlobalLock and from storage-bind conection!!!
        """
        # remove files, which has become replicated
        notNeed = set()
        for filepath in self._NeedReplication:
            if len(self._Location.get(filepath, [])) > 1:
                notNeed.add(filepath)

        self._NeedReplication.difference_update(notNeed)

        for filepath in self._NeedReplication:
            avail_storages = list(self._ActiveStorages - self._Location[filepath])
            random.shuffle(avail_storages)
            for s in avail_storages:
                file = self._Tree.get(filepath)
                if s._storage['free'] >= file['size'] and len(self._Location[filepath]) > 0:
                    try:
                        src_storage = list(self._Location[filepath])[0]
                        logging.info('Trying to replicate "%s" from "%s" to "%s"',
                                     filepath,
                                     src_storage._storage['name'],
                                     s._storage['name'],
                                     )
                        tryReplicateFile(
                            src_storage._storage,
                            s._storage,
                            filepath,
                            self._args)
                        s._storage['free'] -= file['size']
                        self._Location[filepath].add(s)
                        break
                    except Exception as e:
                        print(e)
            else:
                logging.warn('Could not replicate "%s"', filepath)

#
#   method for the Client
#

    def exposed_du(self):
        with self._GlobalLock:
            return list(map(lambda s: s._storage, self._ActiveStorages))

    def exposed_stat(self, path):
        with self._GlobalLock:
            return self._Tree.get(path)

    def exposed_locations(self, path):
        with self._GlobalLock:
            return list(map(lambda s: s._storage, self._Location[path]))

    def exposed_availableStorages(self, dfs_path, size):
        with self._GlobalLock:
            storages = []
            stat = self._Tree.get(dfs_path)
            for s in self._ActiveStorages:
                increase = 0
                if stat is not None and s in self._Location.get(dfs_path, set()):
                    increase = stat['size']

                if s._storage['free'] + increase >= size:
                    storages.append(dict(s._storage))

            random.shuffle(storages) # Random balancing!!
            return storages

    def exposed_ls(self, dfs_dir):
        with self._GlobalLock:
            d = self._Tree.get(dfs_dir)
            stats = list()
            for name in d['files']:
                filepath = join(dfs_dir, name)
                f = self._Tree.get(filepath)
                if f['type'] == dfs.FILE:
                    nodes = list(map(lambda s: s._storage['name'],
                                     self._Location.get(f['path'], [])))
                elif f['type'] == dfs.DIRECTORY:
                    nodes = list(map(lambda s: s._storage['name'],
                                     self._ActiveStorages))
                else:
                    raise ValueError(
                        "Bad filetype: {}, path: {}".format(f['type'], filepath))

                stats.append({
                    'type': f['type'],
                    'name': name,
                    'size': f.get('size', 0),
                    'nodes': str(nodes)
                })
            return stats

    def exposed_rm(self, dfs_file):
        logging.info("rm %s", dfs_file)
        with self._GlobalLock:
            self._NeedReplication.discard(dfs_file)
            f = self._Tree.pop(dfs_file)
            locations = self._Location.pop(dfs_file, set())
            for s in locations:
                try:
                    rm_from(s._storage, dfs_file, self._args)
                    s._storage['free'] += f['size']
                except Exception as e:
                    logging.warn("FAIL: rm %s : %s", dfs_file, e)
            # we have new free space for replication
            self.tryReplicate()

    def exposed_mkdir(self, dfs_dir: str):
        with self._GlobalLock:
            logging.info("mkdir %s", dfs_dir)
            self._Tree.add(dfs.Dir(dfs_dir))

            for s in self._ActiveStorages:
                try:
                    mkdir_on(s._storage, dfs_dir, self._args)
                except Exception as e:
                    logging.warn("FAIL: mkdir %s : %s", dfs_dir, e)

    def exposed_rmdir(self, dfs_dir: str):
        with self._GlobalLock:
            logging.info("rmdir %s", dfs_dir)
            self._Tree.pop(dfs_dir)

            for s in self._ActiveStorages:
                try:
                    rmdir_from(s._storage, dfs_dir, self._args)
                except Exception as e:
                    logging.warn("FAIL: rmdir %s : %s", dfs_dir, e)
