# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
"""Base Tasks for dealing with stuff running in python 3's asyncio event loop"""

import asyncio

from sparts.vtask import VTask


class AsyncIOLoopTask(VTask):
    """Runs the asycio IOLoop."""

    def _runloop(self):
        self.logger.info("AsyncIOLoopTask._runloop()!!!")
        try:
            self.loop.run_forever()
            self.logger.info("AsyncIOLoopTask.run_forever() DONE")
        finally:
            self.logger.info("AsyncIOLoopTask.close() BEGIN")
            self.loop.close()
            self.logger.info("AsyncIOLoopTask.close() END")

    def stop(self):
        super(AsyncIOLoopTask, self).stop()
        self.loop.call_soon_threadsafe(self.loop.stop)

    def initTask(self):
        super(AsyncIOLoopTask, self).initTask()
        self.loop = asyncio.get_event_loop()

        # Remove the default asyncio event loop from the main thread
        asyncio.set_event_loop(None)

    def initTaskThread(self):
        super(AsyncIOLoopTask, self).initTaskThread()

        # Set the event loop from the AsyncIOLoopTask's thread.
        asyncio.set_event_loop(self.loop)


class AsyncTask(VTask):
    DEPS = [AsyncIOLoopTask]
    LOOPLESS = True

    @property
    def loop(self):
        return self.service.requireTask(AsyncIOLoopTask).loop

    def start(self):
        self.loop.call_soon_threadsafe(
            asyncio.ensure_future,
            self._runloop(self.loop),
        )
