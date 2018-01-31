#!/usr/bin/env python

try:
    import logging
    import sys
    import SocketServer
    import MySQLdb
    import threading
    import time
    from daemon import *
    
except StandardError, e:
    import sys
    print "Error while loading libraries: "
    print e
    sys.exit()

logging.basicConfig(filename='/tmp/dbcheck.log', 
                    level=logging.DEBUG, 
                    format='%(asctime)s %(name)s: %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# -- EchoRequestHandler ------------------------------------------------- #
# Provides a request handler that the SocketServer dispatches requests to.
# The entry point into the class is the handle method.  
# ----------------------------------------------------------------------- #
class EchoRequestHandler(SocketServer.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('EchoRequestHandler')
        self.logger.debug('__init__')
	
	# All of the relevant configuration items are kept here
	self.HEALTH_UP = "SERVER_UP"
	self.HEALTH_DOWN = "SERVER_DN"
	self.HEALTH_CHECK = "8675309"	

	self.MYSQLSVR = "localhost"
	self.USER = "root"
	self.PWD = "default"
	self.DB = "intel_test"
	self.QUERY = "SELECT * FROM healthcheck"
	self.QUERYTEST = "DB_ALIVE"
	
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        return
    
    def setup(self):
        self.logger.debug('setup')
        return SocketServer.BaseRequestHandler.setup(self)
    
    def handle(self):
	# This is the threaded routine when the server gets a connection
	cur_thread = threading.currentThread()
        self.logger.debug('Thread %s started to handle client request', cur_thread.getName())
        status = self.HEALTH_DOWN
	
	# Strip data off the socket and get the Thread ID for debug purposes
        data = self.request.recv(1024)

	if data == self.HEALTH_CHECK:
	    # Proper request for health-check, ensure that bogus connections don't
	    # DOS the db server
	    self.logger.debug('Received valid health check request from %s', self.client_address)
	    if self.checkDB():
		self.logger.debug('Database Health Check:  DB Up')
		status = self.HEALTH_UP
	    else:
		self.logger.debug('Database Health Check:  DB Down')
	else:
	    # Received an improper request, log ip and port
	    self.logger.debug('WARNING: Received invalid health check request from %s: %s', self.client_address, data)
	
	# Build a response and send to client
        response = '%s' % status
        self.request.send(response)

        return
    
    def checkDB(self):
	dbhealth = False
	db = None
	
	try:
	    # Attempt to connect to the database.  If the login fails or the 
	    # DB doesn't exist the connect call will fail or raise an error
	    self.logger.debug('Attempting to connect to DB')
	    db = MySQLdb.connect(self.MYSQLSVR, self.USER, self.PWD, self.DB)
	    cursor = db.cursor()
	    
	    # If the query fails for whatever reason, this will also raise an error
	    self.logger.debug('Attempting DB Query, %s', self.QUERY)
	    cursor.execute(self.QUERY)
	    
	    self.logger.debug('Collecting result from query')
	    result = cursor.fetchone()
	    
	    # If it makes it this far, the db is up and the database exists.  If
	    # the table has a valid then the following check will succeed
	    if result[1] == self.QUERYTEST:
		dbhealth = True
		
	except Exception, err:
	    # if the db check fails anywhere, then dbhealth is its default - False
	    pass
	
	finally:
	    # Ensure that the db gets closed if it was connected at all
	    if db:
		self.logger.debug('Closing connection to DB')
		db.close()
		
	return dbhealth
    
    def finish(self):
        self.logger.debug('finish')
        return SocketServer.BaseRequestHandler.finish(self)
    
# -- EchoServer --------------------------------------------------------- #
# Adds the Threading mixin to implement a threaded TCP Server
# ----------------------------------------------------------------------- #    
class EchoServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

# -- dbCheckDaemon ------------------------------------------------------ #
# Inherits daemon_base and implements the run method.  This primarily
# starts a threaded TCP server which is implemented with the SocketServer
# mixin ThreadingMixIn passed to the EchoServer class above.  Once the
# main thread is created, it will wait for clients.  When a client connects,
# it will start a thread that is handled with the EchoRequestHandler class.
# Specifically the handle method.
# ----------------------------------------------------------------------- #
class dbCheckDaemon(daemon_base):
    def run(self):
	self.logger.debug('Starting TCP Server')
	address = ('10.128.1.252', 10888)
	server = EchoServer(address, EchoRequestHandler)
	ip, port = server.server_address
	
	self.logger.debug('Building main thread')
	t = threading.Thread(target=server.serve_forever)
	t.setDaemon(True)
	
	t.start()
	self.logger.debug('Server loop running in thread: ', t.getName())
	
	while True:
	    time.sleep(1)

if __name__ == '__main__':
	"""
	Main entry point
	
	Ensure this file is executable and the python path is correct.  You must
	provide an argument of start/stop/restart which will invoke the proper
	routine in the daemon_ctl object.  Logging is configured at the top of this
	file and passed into the daemon_ctl and daemon_base objects respectively.
	"""
	usage = 'Missing parameter, usage of test logic:\n' + \
	        ' % python3 daemon.py start|restart|stop\n'
	if len(sys.argv) < 2:
		sys.stderr.write(usage)
		sys.exit(2)

	pidfile = '/tmp/test_daemon.pid'
	dc = daemon_ctl(dbCheckDaemon, pidfile, logging)

	if sys.argv[1] == 'start':
		dc.start()
	elif sys.argv[1] == 'stop':
		dc.stop()
	elif sys.argv[1] == 'restart':
		dc.restart()