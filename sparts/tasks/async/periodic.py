# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
"""asyncio version of PeriodicTask"""

from sparts.tasks.async import AsyncTask
from sparts.sparts import option
from sparts.timer import Timer

import asyncio

class AsyncPeriodicTask(AsyncTask):
    INTERVAL = None

    interval = option(type=float, metavar='SECONDS',
                      default=lambda cls: cls.INTERVAL,
                      help='How often this task should run [%(default)s] (s)')

    async def _runloop(self, loop):
        timer = Timer()
        timer.start()
        while not self.service._stop:
            result = await self.execute()
            to_sleep = self.interval - timer.elapsed
            if to_sleep > 0:
                await asyncio.sleep(to_sleep)
            timer.start()

    async def execute(self):
        """Override this to perform some custom action periodically."""
        self.logger.info('execute')
