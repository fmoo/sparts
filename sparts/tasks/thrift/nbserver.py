# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
"""Thrift Server task using TNonblockingServer"""
from __future__ import absolute_import


from sparts.sparts import option
from sparts.tasks.thrift.server import ThriftServerTask

from thrift.server.TNonblockingServer import TNonblockingServer
from thrift.transport.TSocket import TServerSocket

import time


class NBServerTask(ThriftServerTask):
    """Spin up a thrift TNonblockingServer in a sparts worker thread"""
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 0
    OPT_PREFIX = 'thrift'

    bound_host = bound_port = None

    host = option(default=lambda cls: cls.DEFAULT_HOST, metavar='HOST',
                  help='Address to bind server to [%(default)s]')
    port = option(default=lambda cls: cls.DEFAULT_PORT,
                  type=int, metavar='PORT',
                  help='Port to run server on [%(default)s]')
    num_threads = option(name='threads', default=10, type=int, metavar='N',
                         help='Server Worker Threads [%(default)s]')

    def initTask(self):
        """Overridden to bind sockets, etc"""
        super(NBServerTask, self).initTask()

        self._stopped = False

        # Construct TServerSocket this way for compatibility with fbthrift
        self.socket = TServerSocket(port=self.port)
        self.socket.host = self.host

        self.server = TNonblockingServer(self.processor, self.socket,
                                         threads=self.num_threads)
        self.server.prepare()

        self.bound_addrs = []
        for handle in self._get_socket_handles(self.server.socket):
            addrinfo = handle.getsockname()
            self.bound_host, self.bound_port = addrinfo[0:2]
            self.logger.info("%s Server Started on %s", self.name,
                self._fmt_hostport(self.bound_host, self.bound_port))

    def _get_socket_handles(self, tsocket):
        """Helper to retrieve the socket objects for a given TServerSocket"""
        handle = getattr(tsocket, 'handle', None)
        if handle is not None:
            return [tsocket.handle]

        # Some TServerSocket implementations support multiple handles per
        # TServerSocket (e.g., to support binding v4 and v6 without
        # v4-mapped addresses
        return tsocket.handles.values()

    def _fmt_hostport(self, host, port):
        if ':' in host:
            return '[%s]:%d' % (host, port)
        else:
            return '%s:%d' % (host, port)

    def stop(self):
        """Overridden to tell the thrift server to shutdown asynchronously"""
        self.server.stop()
        self.server.close()
        self._stopped = True

    def _runloop(self):
        """Overridden to execute TNonblockingServer's main loop"""
        while not self.server._stop:
            self.server.serve()
        while not self._stopped:
            time.sleep(0.1)
