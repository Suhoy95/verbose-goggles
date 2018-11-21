# verbose-goggles / dfs over rpyc

```
last commit:
url: https://github.com/Suhoy95/verbose-goggles.git
```

## Get-started / how to test

Since our applications work over SSL/rpyc and have several hosts(nameserver + storages) which expose different ports to the workstation with docker,
we have to provide a lot of arguments, which should be set precisely
to run working system configuration. To resolve this issue all programs build
and run with `docker-compose`. if you want to run system by you own,
you can look into **Usages** section.

*docker-compose.yml* contains next list of pre-configured hosts:
- `nameserver` as nameserver
- `alice`, `bob`, `carol`, `dave`, `eve`, `mellory`, `trent` as storages (7 storages with 1 MiB capacity)


### Install docker-compose locally with pip into the virtual environment
```
make venv
source venv/bin/activate
```
### Run/stop/maintain storage(s):
```
docker-compose up [one or more storages]
```
The one `nameserver` will be started automatically as dependency. With this command you can run one or more storages. After containers have started up you will see  their logs mixed single terminal. To stop them press `^D`.

As soon as you want to see behavior of system when some storages start and some stop, you will be interesting in starting storages in different terminals.

### Observe logs:
```
docker-compose logs -f [name of storage]
```
In particular, you will be interesting logs of nameserver
```
docker-compose logs -f nameserver
```

### Running client

Check that docker-compose create `verbose-goggles_main` network for our configuration.
If it has different name, you must correct it in the `Makefile`:
```
docker network ls

# Example of output
NETWORK ID          NAME                   DRIVER              SCOPE
...
6e1a490fe842        verbose-goggles_main   bridge              local
```

And now you should be able to run client:
```
make run_client
```

This command will pull `suhoy/vg_client` container and run it inside `verbose-goggles_main` with attached *./tmp* folder. So, with `local`-command you
will see content of *./tmp*.

## Usegaes
Example of using the scripts can be found in *.vscode/launch.json*, which is used for development and debug.
```
python vg_client.py [-h] [--local LOCAL] [--logfile LOGFILE]
                    [--loglevel LOGLEVEL] [--ns_hostname NS_HOSTNAME]
                    [--ns_port NS_PORT] [--ca_cert CA_CERT]
                    [--keyfile KEYFILE] [--certfile CERTFILE]
```

```
python vg_nameserver.py [-h] [--hostname HOSTNAME] [--port PORT]
                        [--treejson TREEJSON] [--ca_cert CA_CERT]
                        [--keyfile KEYFILE] [--certfile CERTFILE]
```

```
python vg_storage.py [-h] [--name NAME] [--hostname HOSTNAME] [--port PORT]
                     [--capacity CAPACITY] [--ca_cert CA_CERT]
                     [--keyfile KEYFILE] [--certfile CERTFILE]
                     [--ns_hostname NS_HOSTNAME] [--ns_port NS_PORT]
                     [--rootpath ROOTPATH]
```

### Common arguments
- `--hostname` - hostname of starting server
- `--port` - port of starting server
- `--ca_cert CA_CERT` - path to CA certificate(s)
- `--keyfile KEYFILE` - path to private key of peer
- `--certfile CERTFILE` - path to certificate of peer
- `--ns_hostname NS_HOSTNAME` - hostname/address of nameserver
- `--ns_port NS_PORT` - port of nameserver

To generate new **CA** and/or **keys/certificates for peer** look  into `certs/{Makefile,README.md}`.

### Nameserver-specific arguments

- `--treejson TREEJSON` - path to file which contains the data about dfs tree.
if file is empty or not exist will

### Storage-specific arguments

- `--name NAME` - name of storage (should be unique to not be confused)
- `--capacity CAPACITY` - number in bytes which define how much bytes storage can hold. This option does not consider size of directories and underlying filesystem at all. It is just information for nameserver to limit amount of data from client.
- `--rootpath ROOTPATH` - path where files must be placed

If you forgot specify several arguments for `vg_storage.py`, it will try extract them from **environment variables** and you can see Python's **KeyError** exception. That was made only to pass arguments into the docker-container and should not be considered as normal behavior.

### Client-specific arguments

- `--local LOCAL` - path to local directory from which you want to download/upload files
- `--logfile LOGFILE` - path to file for logs. If it is not specified logs will be printed on the terminal
- `--loglevel LOGLEVEL` - loglevel which will be passed directly to **logging.basicConfig** [[Python:logging-levels](https://docs.python.org/3/library/logging.html#logging-levels)]

## Architecture

### Overview and rpyc

As mention in assignment DFS combines from tree main program:
- nameserver
- storage
- client

To facilitate programming and especially programming of Inter-Process-Communication (IPC) the project has been performed with Python with standard libraries and rpyc - Remote-Procedure-Call (RPC) library for python. To make RPC communication
more secure all connections creates over SSL. For testing purpose all certificates
and keys was generated into *certs*.

To expose required functions from nameserver and storage we define services in
`src/nameserverService.py` and `src/storageService.py` respectively. The `src/dfs.py` contains helpers to work with Data structures. In `src/clientcmd.py` contain client handlers and checking the correctness of operation. And `vg_*.py` entry-points contain parsing arguments and combine it with all required elements from *src/*.

To eliminate corruption of data structures and racing condition while multi threading,
we have to use global mutex, which guarantees that block code associated with
some level will be executed completely and state of application won't be changed
in other threads. Hopefully, Python handles this gracefully:
```python
import threading

GlobalLock = threading.Lock()

with GlobalLock:
    # critical local
```

The `src/restoretree.py` was written for develop process, but also it can create `tree.json` from existing files.

The logs provides by `logging` package. Basically, the most useful command is raising
the logging:
```
logging.basicConfig(level=logging.DEBUG)
```
This command provides us logging about connection events such connect,
disconnect, exceptions inside the servers which caught by rpc, that keep server
a little bit robust (Actually, exception means that some logic was missed and
data can have inconsistent state and server should be restarted). And we need only print information about  required events implied by application logic.

In next section we consider the Data Structures holding in services and
the most comprehensive procedures such as restarting storages with checking
of current files, file replication and writing file from client side (`put`). Working with directories (`mkdir, rmdir, cd, ls, pwd`), receiving files (`get`),
removing files (`rm`) and observing state of storages (`du`) are considered as trivial and it should be easy to read the code directly to understand these
processes.

### Data Structures

#### Tyeps

**path**: string which describe place of the file or directory in DFS. In the
system must be absolute. Used as file  unique identificator.
```
pathType: str
```

```
File {
    path: pathType
    type: str("FILE") to distinguish File and Dir structure
    size: int, amount of bytes
    hash: str in hexdigest, currently sha256 of file. see src/dfs.py:filehash
}
```
```
Dir {
    path: pathType
    type: str("DIRECTORY")
    files: list([]) of basename. By join dirPath + basename you get the file's path
}
```

```
Storage {
    name: str, for verbosity
    addr: [hostname:str, port:int]
    free: int
    capacity: int
}
```
#### State

**Tree**: hashtable (or map) from path to file or directory structure. Tree describes
full state of DFS-file tree and nameserver should ensure that each change of structure are written to the json-file.
```
Tree: path -> [File(path)|Dir(path)]
```

**Location**: hashtable from path to set of active storages which holds this file.
Runtime information as soon as after start of nameserver we must consider all
storages in downstate (we do not support storage re-connection, they should be restarted manually).
```
Location: hash -> set(...Storage)
```

**ActiveStorages**: set of storages currently connected to the nameserver
```
ActiveStorages: set(...Storage)
```

**NeedReplication**: set of paths, which files we should replicate. It is not
possible in the every, so nameserver will keep this in mind and will try to replicate when appropriate case appears. Actually it could be obtained from **Location**
state with `len(Location) <= 1` condition, so this structure can be considered as
optimization.

```
NeedReplication: set(...pathType)
```

**Notes:** with this structures client will be able observe and control state of DFS even if only nameserver is up except the getting and putting the files to storages.

### Storage restarting

After failure or stop, storage server should be able to attach to the nameserver
again. But before it become active it should compare its files against actual
DFS tree. These procedure has 4 stages:

1. `nameserver.upgrade(Storage)` - tell nameserver that this connection with storage and provide required information. Field `free` must be equal to `capacity`, nameserver
will recalculate free space by itself.
1. `walkOnStorage` - check current files and directories. If file has the same path, size and hash that means that storage should keep it and nameserver should put
this storage into `Location[path]`.
1. `walkOnDfsTree` - recreate all dirs against the `Tree`. We implies that directory
exists on every ActiveStore
1. `nameserver.upgrade(Storage)` - tell nameserver that storage finish the
self-checking, and could be considered as Active. This event emits *Replication*
if is is needed

### Writing file from client

1. `nameserver.availableStorages(path, size)` - ask nameserver list of all available
storages, which can accept data with `size` to the `path`.
1. `storage.write_fileobj(path, fsrc)` - ask storage to write data from `fsrc` to `path`
1. From storage: `nameserver.write_notification(File)` - notify nameserver
that storage got new data from client. This data in single copy, that leads to replication - to be able handle it we should release `GlobalLock`
before sending notification to be able handle pulling the file.
1. Nameserver update Data Structures and starts replication if possible
1. return control to the client

### File replication

When nameserver should try to replicate file:
- Storage events:
    - storage activate - we maybe get new free space or some not-replicated file become available
    - storage disconnect - lost some file(s) or copies of file(s)
- File events:
    - writing file from client - it exists in one copy. At list it should be replicated
    - removing file - we get new free space

Other details in [src/nameserverService.py:tryReplicate](src/nameserverService.py)


## Client

The client has two implementations, but with single command SHell-like interface. For this purpose the standard library `cmd`. if it possible `cmd` will use GNU library `readline`, that give a lot of cool stuff with history, recursive search, autocomplete and hotkeys (e.y. `^E`, `^A`) and so on. And all that is required it write the appropriate handlers and appropriate doc-string in the inheritor of `cmd.Cmd`. Help command is provided as well: information will be extracted directly from Python's doc-string.

Overview of commands and DFS-specific information can be read with `usage` command. Pay attention, that even there are specified requirements to the filename, the code do not check it explicitly.
Deviation from this documentation is considered as client personal risk
and inappropriate usage of DFS.

### REST

Use `requests` library to send and process HTTP(s) request.

Each procedure split into two parts: one in SdfsCmd, which parse and convert argument(s) and, also, check the condition from local side, such as trying to upload directory instead of file. And in the second part we send requests and process the result. Since the HTTP-server should validate request, we can transmit validation of remote parameters to the server.

if *status_code* is 400, we implies that some validation has not passed, and we can
extract the nameserver error-message and print it to the client.

### RPC

All validation made directly inside the `ClientCmd` handlers. Since it is really
hard to work with rpc Exception, we should be ensure first that entered command
definitely valid.
