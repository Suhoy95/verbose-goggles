import rpyc
import logging
logging.basicConfig(level=logging.DEBUG)


class MyService(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

    def exposed_get_answer(self):  # this is an exposed method
        return 42


Conn = rpyc.connect("localhost", port=18861)


def send_ping():
    global Conn
    import time
    while True:
        Conn.root.ping()
        time.sleep(5)

import threading

t = threading.Thread(target=send_ping)
t.start()


from rpyc.utils.server import ThreadedServer
t = ThreadedServer(MyService, port=18862)
t.start()
