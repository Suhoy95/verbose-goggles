import os
import os.path as path
import cmd
import rpyc
import logging
import shutil

import src.dfs as dfs
from src.nameserverService import NameserverService


class VgException(Exception):
    pass


class ClientCmd(cmd.Cmd):
    # prompt is changing dynamically by self.cd()
    prompt = "sdfs> "

    def __init__(self, ns: NameserverService, local, args):
        cmd.Cmd.__init__(self)
        self._ns = ns
        self._args = args
        os.chdir(local)
        self.do_cd("/")
        self.do_usage("")

    def do_usage(self, line):
        """
        syntax: dfs

        print common recomendation how to use DFS
        """
        print("""
    GET HELP:
        help - print avaliable commands
        help command - print description of command
        usage - this help

    COMMANDS:
           du - print info about nodes, its capacity and free space
           ls - print content of DFS directory
        local - print content of local directory
           cd - change directory inside DFS tree
          pwd - print current DWS working directory and local path

        mkdir - create DFS dir
        rmdir - remove DFS dir

          get - download file to the local directory
          put - upload file to the DFS
           rm - remove file

          EOF - quit from client

    DFS NOTES:
        all filenames should contains only letters [a-zA-Z], digits [0-9],
        hyphen [-], underscore [_] or dot [.] with maximum length 255

        *_DFS_PATH - path on the dfs system,
            absolute path starts with '/'
            relative path is resolved relative to Current Working Directory
                (print with "pwd" command)
        *_LOCAL_PATH - path on the current machine,
            absolute path starts with '/'
            relative path is resolved relative to --local parameter
        """)

    def do_du(self, line):
        """
        syntax: du

        print the common information about DFS:
            - list of nodes
            - capacity and avaliable space per each node
        """
        print("{:>20}\t{:>20}\t{}\t{}".format(
            "NODE_NAME", "ADDR", "FREE", "CAPACITY"))
        for node in self._ns.du():
            print("{:>20}\t{:>20}\t{}\t{}".format(
                node['name'],
                str(node['addr']),
                node['free'],
                node['capacity']
            ))

    def do_get(self, line):
        """
        syntax: get SRC_DFS_PATH DST_LOCAL_PATH

        Download file SRC_DFS_PATH from nodes to the local DST_LOCAL_PATH
        """
        # [advanced] TODO: if SRC_DFS_PATH is dir: ask about loading dir recursevly
        parts = line.split()
        if len(parts) != 2:
            raise VgException(
                "Wrong amount of arguments. Expect: 2, actual: {0}".format(len(parts)))

        src_dfs_path = self._to_dfs_abs_path(parts[0])

        f = self._ns.stat(src_dfs_path)
        if f is None:
            raise VgException("{} does not exist".format(src_dfs_path))
        if f['type'] != dfs.FILE:
            raise VgException("{} is not a regular file".format(src_dfs_path))

        file = parts[1]
        dst_local_path = path.abspath(file)

        if path.exists(dst_local_path):
            answer = input("'%s' exists. Overwrite[y/N]? " % (dst_local_path,))
            if answer.lower() != 'y':
                return

        storages = self._ns.locations(src_dfs_path)
        if len(storages) == 0:
            raise VgException(
                "There are no availible storages. Contact with administrators")

        for s in storages:
            try:
                conn = rpyc.ssl_connect(s['addr'][0], port=s['addr'][1],
                                        keyfile=self._args.keyfile,
                                        certfile=self._args.certfile,
                                        ca_certs=self._args.ca_cert,
                                        config={
                                        'sync_request_timeout': -1,
                                        })
                with conn.root.open(src_dfs_path, "br") as fsrc:
                    with open(dst_local_path, "bw") as fout:
                        shutil.copyfileobj(fsrc, fout)
                conn.close()
                return
            except Exception as e:
                logging.warn("FAIL:get:%s from %s (%s)",
                             src_dfs_path, s['name'], s['addr'])
        else:
            raise VgException(
                "Could not download {} from storages".format(src_dfs_path))

    def do_put(self, line):
        """
        syntax: put SRC_LOCAL_PATH DST_DFS_PATH

        Upload local SRC_LOCAL_PATH file to DST_DFS_PATH
        """
        # [advanced] TODO: if SRC_LOCAL_PATH is dir: ask about loading dir recursevly
        parts = line.split()
        if len(parts) != 2:
            raise VgException(
                "Wrong amount of arguments. Expect: 2, actual: {0}".format(len(parts)))

        file = parts[0]
        src_local_path = path.abspath(file)

        if not os.path.exists(src_local_path):
            raise VgException("File {0} does not exist".format(file))

        if not os.path.isfile(src_local_path):
            raise VgException("{0} is not regular file".format(file))

        dst_dfs_path = self._to_dfs_abs_path(parts[1])

        # TODO:

        self.cmds.put(src_local_path, dst_dfs_path)

    def do_pwd(self, line):
        """
        syntax: pwd

        Print Current Working Directory (CWD) and local path
        """
        print("CWD: %s\nLOCAL: %s" % (self._cwd, os.getcwd()))

    def do_ls(self, line):
        """
        syntax: ls [DFS_DIR_PATH]

        list files of DFS_DIR_PATH.
        if DFS_DIR_PATH is not specified, current working DFS directory will be used
        """
        dfs_dir = self._to_dfs_abs_path(line, isdir=True)

        d = self._ns.stat(dfs_dir)
        if d is None:
            raise VgException("{} does not sxist".format(dfs_dir))

        if d['type'] != dfs.DIRECTORY:
            raise VgException("{} is not a directory".format(dfs_dir))

        print("{:4} {: >20}\t{}\t{}".format(
            "TYPE", "FILENAME", "FILESIZE", "Storages"))
        for f in self._ns.ls(dfs_dir):
            ftype = "D" if f['type'] == dfs.DIRECTORY else "F"
            print("{:4} {: >20}\t{}\t{}".format(
                ftype, f['name'], f['size'], f['nodes']))

    def do_cd(self, line):
        """
        syntax: cd [DFS_DIR_PATH]

        Change current working DFS directory to DFS_DIR_PATH.
        if DFS_DIR_PATH is not specified, current working directory will set to "/"
        """
        if line == '':
            line = '/'

        dfs_dir = self._to_dfs_abs_path(line, isdir=True)

        f = self._ns.stat(dfs_dir)
        if f is None:
            raise VgException("{} does not exist".format(dfs_dir))

        if f['type'] != dfs.DIRECTORY:
            raise VgException("'{0}' is not a directory".format(dfs_dir))

        self._cwd = dfs_dir
        self.prompt = "sdfs:{0}> ".format(dfs_dir)

    def do_rm(self, line):
        """
        syntax: rm DFS_FILE_PATH

        Remove file, which is blased according DFS_FILE_PATH
        """
        dfs_file = self._to_dfs_abs_path(line)
        f = self._ns.stat(dfs_file)
        if f is None:
            raise VgException("{} does not exist".format(dfs_file))

        if f['type'] != dfs.FILE:
            raise VgException("'{0}' is not a file".format(dfs_file))

        self._ns.rm(dfs_file)

    def do_local(self, line):
        """
        syntax: local [LOCAL_DIR]

        List content of LOCAL_DIR
        """
        line = path.abspath(line)

        if not path.isdir(line):
            raise VgException("'{}' is not a local directory".format(line))

        print("{:4} {: >30}\t{}".format("TYPE", "FILENAME", "FILESIZE"))
        for f in os.listdir(line):
            fpath = path.join(line, f)
            ftype = "D" if os.path.isdir(fpath) else "F"
            print("{:4} {: >30}\t{}".format(
                ftype, path.basename(f), os.path.getsize(fpath)))

    def do_mkdir(self, line):
        """
        syntax: mkdir DFS_DIR_PATH

        Create DFS directory on DFS_DIR_PATH
        """
        line = self._to_dfs_abs_path(line, isdir=True)
        self.cmds.mkdir(line)

    def do_rmdir(self, line):
        """
        syntax: rmdir DFS_DIR_PATH

        Remove directory DFS_DIR_PATH from DFS
        """
        line = self._to_dfs_abs_path(line, isdir=True)
        if len(self.cmds.ls(line)) > 0:
            confirm = input(
                "'{}' is not empty. Remove recursively [y/N]?".format(line))
            if confirm.lower() != 'y':
                return

        self.cmds.rm(line, recursive=True)

    def do_EOF(self, _):
        """
        syntax: EOF

        Exit from session
        """

        print("quiting...")
        return True

    def _to_dfs_abs_path(self, line, isdir=False):
        if not path.isabs(line):
            line = path.join(self._cwd, line)

        line = path.normpath(line)

        return line
