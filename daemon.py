# Originally posted here: 
# http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
# Modifications by Dan Holland from F5.com, Seth and Ader
try:
    import sys
    import os
    import time
    import atexit
    import signal
    
except StandardError, e:
    import sys
    print "Error while loading libraries: "
    print e
    sys.exit()

# -- daemon_base -------------------------------------------------------- #
# daemon_base provides a base class that provides daemonizing services
# for code.  The user needs to inherit this class and overide the run()
# method which should perform what tasks the daemon needs to perform.  The
# class is used in conjunction with the daemon_ctl class which provides
# services to start, stop and restart the daemon
# ----------------------------------------------------------------------- #
class daemon_base:
	"""
	A generic daemon base class.
	Usage: subclass this class and override the run() method.
	"""
	def __init__(self, pidfile, logging, workpath='/'):
		"""
		Constructor.
		The pidfile for the atexit cleanup method.  The workpath is the 
		path the daemon will operate in. Normally this is the root 
		directory, but can be some data directory too, just make sure 
		it exists.  Lastly, you need to provide a logging object.
		
		@param pidfile: daemon pid file
		@param logging: Python logging object
		@param workpath: daemon working directory
		"""
		self.pidfile = pidfile
		self.workpath = workpath
		self.logger = logging.getLogger('Daemon_base')
	
	def perror(self, msg, err):
		"""
		Print error message and exit.  Modified to use python logger
		"""
		self.logger.debug('Error: %s; %s', msg, err)
		sys.exit(1)
	
	def daemonize(self):
		"""
		Deamonize calss process. (UNIX double fork mechanism).
		"""
		self.logger.debug('daemonize')
		if not os.path.isdir(self.workpath):
			self.perror('workpath does not exist!', '')
	
		try:
			# exit first parent process
			self.logger.debug('Attempting to fork and then exit first process')
			pid = os.fork() 
			if pid > 0:
				sys.exit(0)
		except OSError as err:
			self.perror('fork #1 failed: {0}', err)
	
		# decouple from parent environment
		try:
			self.logger.debug('Attempting to decouple from parent environment')
			os.chdir(self.workpath)
		except OSError as err:
			self.perror('path change failed: {0}', err)
	
		os.setsid() 
		os.umask(0) 
	
		try:
			# exit from second parent
			self.logger.debug('Attempting to fork and exit second parent')
			pid = os.fork() 
			if pid > 0:
				sys.exit(0) 
		except OSError as err:
			self.perror('fork #2 failed: {0}', err)
	
		# redirect standard file descriptors
		self.logger.debug('Redirecting standard file descriptors')
		sys.stdout.flush()
		sys.stderr.flush()
		si = open(os.devnull, 'r')
		so = open(os.devnull, 'a+')
		se = open(os.devnull, 'a+')
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())
	
		# write pidfile
		atexit.register(os.remove, self.pidfile)
		pid = str(os.getpid())
		with open(self.pidfile,'w+') as f:
			f.write(pid + '\n')
			
		self.logger.debug('Daemonizing sucessful, entering run')
		self.run()
	
	def run(self):
		"""
		run()
		Worker method.  It will be called after the process has been 
		daemonized by start() or restart(). You'll have to overwrite this
		method with the daemon program logic.
		"""
		while True:
			time.sleep(1)

# -- daemon_ctl---------- ----------------------------------------------- #
# daemon_base provides a base class that provides daemonizing services
# for code.  The user needs to inherit this class and overide the run()
# method which should perform what tasks the daemon needs to perform.  The
# class is used in conjunction with the daemon_ctl class which provides
# services to start, stop and restart the daemon
# ----------------------------------------------------------------------- #
class daemon_ctl:
	"""
	Control class for a daemon.

	Usage:
	dc = daemon_ctl(daemon_base, '/tmp/foo.pid')
	dc.start()

	This class is the control wrapper for the daemon_base class. It adds
	start/stop/restart functionality for it with out creating a new daemon 
	every time.
	"""
	def __init__(self, daemon, pidfile, logging, workdir='/'):
		"""
		Constructor.

		@param daemon: daemon class (not instance)
		@param pidfile: daemon pid file
		@param logging: Python logging object
		@param workdir: daemon working directory
		"""
		self.daemon = daemon
		self.pidfile = pidfile
		self.logging = logging
		self.logger = logging.getLogger('Daemon_ctl')
		self.workdir = workdir
	
	def start(self):
		"""
		Start the daemon.
		"""
		self.logger.debug('start')
		try: # check for pidfile to see if the daemon already runs
			with open(self.pidfile, 'r') as pf:
				pid = int(pf.read().strip())
		except IOError:
			self.logger.debug('Pidfile not found, creating process')
			pid = None
	
		if pid:
			message = "pidfile {0} already exists. " + "Daemon already running?\n"
			#sys.stderr.write(message.format(self.pidfile))
			self.logger.debug('Error: %s', message)
			sys.exit(1)
		
		# Start the daemon
		self.logger.debug('Starting Daemon')
		d = self.daemon(self.pidfile, self.logging, self.workdir)
		d.daemonize()

	def stop(self):
		"""
		Stop the daemon.

		This is purely based on the pidfile / process control and does 
		not reference the daemon class directly.
		"""
		self.logger.debug('stop')
		try: 
			# get the pid from the pidfile
			with open(self.pidfile,'r') as pf:
				pid = int(pf.read().strip())
				self.logger.debug('Found pid %s', pid)
		except IOError:
			pid = None
	
		if not pid:
			message = "pidfile {0} does not exist. " + "Daemon not running?\n"
			#sys.stderr.write(message.format(self.pidfile))
			self.logger.debug('Error: %s', message)
			return # not an error in a restart
		
		
		try:# try killing the daemon process	
			while 1:
				self.logger.debug('Sending pid SIGTERM signal')
				os.kill(pid, signal.SIGTERM)
				time.sleep(0.1)
		except OSError as err:
			e = str(err.args)
			if e.find("No such process") > 0:
				self.logger.debug('Process killed, cleaning up pidfile')
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
			else:
				self.logger.debug('Error:  Problem while killing process, cleaning up: %s', str(err.args))
				sys.exit(1)

	def restart(self):
		"""Restart the daemon.
		"""
		self.logger.debug('restart')
		self.stop()
		time.sleep(3)
		self.start()