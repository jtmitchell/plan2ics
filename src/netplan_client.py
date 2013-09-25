# -*- coding: utf-8 -*-
import socket
import os
import re

open_rx = re.compile(r'^o(?P<status>[tf])(?P<mode>[rw])(?P<file>\d+)$')
rowcount_rx = re.compile(r'^n(?P<file>\d+)\s+(?P<rows>\d+)$')
read_rx = re.compile(r'^[rR](?P<status>[tf])(?P<file>\d+)\s+(?P<row_number>\d+)\s+(?P<row_data>.+)$')
write_rx = re.compile(r'w(?P<status>[tf])(?P<row_number>\d+)')

CR = '\r'
LF = '\n'
CRLF = CR + LF


class NetplanClient(object):

    '''Class to connect to a netplan server to read and write calendar files.
    '''
    plan_calendar = None
    filenumber = None

    def __init__(self, host=None, port=2983):
        if host:
            self.connect(host, port)

    def connect(self, host, port=2983):
        self.sock = socket.create_connection((host, port))
        self.file = self.sock.makefile('rb')
        self.send('=' + self.client_id)
        self.send('t0')     # tell netplan we are plan
        self.receive()

    def disconnect(self):
        self.send('q')
        self.sock.shutdown()
        self.sock.close()

    def send(self, msg):
        self.sock.sendall('%s%s' % (msg, CRLF))
        return

    def receive(self):
        return self.file.readline()

    @property
    def client_id(self):
        return '%s<uid=%s,gid=%s,pid=%s>' % (self.__module__, os.getuid(),
                                             os.getgid(), os.getpid())

    def get_calendar(self, calendar):
        self.send('o' + calendar)
        response = self.receive()
        m = open_rx.match(response)
        if m:
            status = m.group('status')
            self.filenumber = m.group('file')
        if self.filenumber:
            self.send('r%s 0' % self.filenumber)
            for response in self.receive():
                print response
