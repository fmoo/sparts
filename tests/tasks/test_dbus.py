# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
from sparts.tests.base import SingleTaskTestCase, Skip

try:
    from sparts.tasks.dbus import DBusServiceTask
except ImportError:
    raise Skip("Unable to run dbus tests without dbus")

class MyDBusService(DBusServiceTask):
    BUS_NAME = 'org.sparts.tests.tasks.test_dbus'
    pass


class DbusTests(SingleTaskTestCase):
    TASK = MyDBusService

    def testBusName(self):
        self.assertMatch('^:\d+.\d+$', self.task.bus.get_unique_name())
