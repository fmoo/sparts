import logging
import threading


class VTask(object):
    OPT_PREFIX = None

    @property
    def name(self):
        return self.__class__.__name__

    def __init__(self, service):
        self.service = service
        self.logger = logging.getLogger('%s.%s' % (service.name, self.name))

    def initTask(self):
        self.thread = threading.Thread(target=self._runloop)

    def start(self):
        self.thread.start()

    def stop(self):
        pass

    def join(self):
        while self.thread.isAlive():
            self.thread.join(0.5)

    def _runloop(self):
        raise NotImplementedError()

    @classmethod
    def _loptName(self, *args):
        return '--' + self._optName(*args).replace('_', '-')

    @classmethod
    def _optName(cls, *args):
        name = cls.OPT_PREFIX or cls.__name__
        parts = [name]
        parts.extend((p.lower() for p in args))
        return '_'.join(parts)

    def getTaskOption(self, opt, default=None):
        return getattr(self.service.options,
                       self._optName(opt), default)

    @classmethod
    def _addArguments(cls, ap):
        pass


class SkipTask(Exception):
    pass
