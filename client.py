#!/usr/bin/env python

if __name__ == '__main__':
    import socket
    import threading
    import logging

    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s',)
    
    ip = '10.128.1.252'
    port = 10888
    logger = logging.getLogger('client')
    logger.info('Server on %s:%s', ip, port)
    
    # Connect to server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logger.debug('Connecting to server')
    s.connect((ip, port))
    
    # Send the data
    #message = 'This is the message that I am sending to the server!'
    message = "8675309"
    logger.debug('Sending data: "%s"', message)
    len_sent = s.send(message)
    
    # Receive a response
    logger.debug('Waiting for response')
    response = s.recv(1024)
    logger.debug('response from server: "%s"', response)
    
    # Clean up
    logger.debug('closing socket')
    s.close()
    logger.debug('done')