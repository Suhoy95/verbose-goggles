import rpyc
import logging
logging.basicConfig(level=logging.DEBUG)

FirstConn = None

class MyService(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

    def exposed_route(self): # this is an exposed method
        import time
        time.sleep(100)
        print("Hello")

    def exposed_ping(self):
        logging.info("ping")

if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    t = ThreadedServer(MyService, port=18861)
    t.start()