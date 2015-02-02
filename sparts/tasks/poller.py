# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
from .periodic import PeriodicTask
from threading import Event

import os.path
import pickle
import tempfile
from sparts.fileutils import readfile, writefile


class PollerTask(PeriodicTask):
    """A PeriodicTask oriented around monitoring a single value.
    
    Simply override `fetch`, and the `onValueChanged()` method will be called
    with the old and new values.  Additionally, the `getValue()` method can
    be called by other tasks to block until the values are ready.
    """

    PERSIST = False
    PERSIST_DIR = None
    SERIALIZER = pickle

    def initTask(self):
        self.current_value = None
        self.fetched = Event()
        super(PollerTask, self).initTask()

        if self.PERSIST:
            self.initFromFile(self.state_file)

    def execute(self, context=None):
        new_value = self.fetch()
        if self.current_value != new_value:
            self.onValueChanged(self.current_value, new_value)
        self.current_value = new_value
        self.fetched.set()

        if self.PERSIST:
            self.saveToFile(self.state_file, new_value)

    def onValueChanged(self, old_value, new_value):
        self.logger.debug('onValueChanged(%s, %s)', old_value, new_value)

    def fetch(self):
        self.logger.debug('fetch')
        return None

    def getValue(self, timeout=None):
        self.fetched.wait(timeout)
        return self.current_value

    def initFromFile(self, path):
        if os.path.exists(path):
            data = self.SERIALIZER.loads(readfile(path))
            self.current_value = data
            self.fetched.set()

    def saveToFile(self, path, obj):
        data = self.SERIALIZER.dumps(obj)
        writefile(path, data)

    @property
    def state_file(self):
        state_dir = self.PERSIST_DIR
        if state_dir is None:
            state_dir = tempfile.gettempdir()
        return os.path.join(state_dir, '__' + self.name + '.state')
