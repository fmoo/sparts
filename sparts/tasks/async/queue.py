# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
"""asyncio version of QueueTask"""

from sparts.tasks.async import AsyncTask
from sparts.sparts import option
from sparts.timer import Timer

import asyncio

class AsyncQueueTask(AsyncTask):
    CONCURRENCY = 4

    concurrency = option(type=float, metavar='items',
                         default=lambda cls: cls.CONCURRENCY,
                         help='Maximum number of concurrent execution contexts'
                              ' [%(default)s]')
    def initTask(self):
        super(AsyncQueueTask, self).initTask()
        self.queue = asyncio.Queue(maxsize=self.concurrency, loop=self.loop)

    async def _runloop(self, loop):
        num_running = 0
        sem = asyncio.Semaphore(self.concurrency, loop=loop)
        while not self.service._stop:
            await sem.acquire()
            work = await self.queue.get()
            t = asyncio.ensure_future(self.execute(work), loop=loop)
            t.add_done_callback(
                lambda f: sem.release()
            )

    async def execute(self, work):
        """Override this to perform some custom action periodically."""
        self.logger.info('execute[%s]' % work)
