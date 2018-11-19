import json
import hashlib

from os.path import (
    normpath,
    join,
    isfile,
    isdir,
    getsize,
    abspath
)

from os import (
    listdir
)

from dfs import (
    File,
    Dir
)


def filehash(filename):
    hash_sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def walk(absroot, curdir, tree):
    d = normpath(join(absroot, '.' + curdir))

    for filename in listdir(d):
        fullpath = normpath(join(d, filename))
        dfs_path = normpath(join(curdir, filename))

        tree[curdir]['files'].append(filename)

        if isfile(fullpath):
            tree[dfs_path] = File(dfs_path,
                                  getsize(fullpath),
                                  filehash(fullpath))
        elif isdir(fullpath):
            tree[dfs_path] = Dir(dfs_path)
            walk(absroot, dfs_path, tree)
        else:
            raise ValueError("Bad file {}".format(fullpath))


def restoreTree(storageRoot):
    tree = {
        '/': Dir('/')
    }

    absroot = abspath(storageRoot)

    walk(absroot, '/', tree)

    return tree


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        add_help="Create tree.json from rootPath-directory")
    parser.add_argument("--rootpath")
    parser.add_argument("--treejson")

    args = parser.parse_args()

    tree = restoreTree(args.rootpath)
    with open(args.treejson, "w") as f:
        f.write(json.dumps(tree, indent=4))
