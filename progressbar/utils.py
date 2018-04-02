from __future__ import absolute_import
import io
import os
import sys
import logging
from python_utils.time import timedelta_to_seconds, epoch, format_time
from python_utils.converters import scale_1024
from python_utils.terminal import get_terminal_size

import six


assert timedelta_to_seconds
assert get_terminal_size
assert format_time
assert scale_1024
assert epoch


class WrappingIO:

    def __init__(self, target, capturing=False, listeners=set()):
        self.buffer = six.StringIO()
        self.target = target
        self.capturing = capturing
        self.listeners = listeners

    def write(self, value):
        if self.capturing:
            self.buffer.write(value)
            if '\n' in value:
                for listener in self.listeners:  # pragma: no branch
                    listener.update()
        else:
            self.target.write(value)

    def flush(self):
        self.buffer.flush()

    def _flush(self):
        value = self.buffer.getvalue()
        if value:
            self.flush()
            self.target.write(value)
            self.buffer.seek(0)
            self.buffer.truncate(0)


class StreamWrapper(object):
    '''Wrap stdout and stderr globally'''

    def __init__(self):
        self.stdout = self.original_stdout = sys.stdout
        self.stderr = self.original_stderr = sys.stderr
        self.original_excepthook = sys.excepthook
        self.wrapped_stdout = 0
        self.wrapped_stderr = 0
        self.wrapped_excepthook = 0
        self.capturing = 0
        self.listeners = set()

        if os.environ.get('WRAP_STDOUT'):  # pragma: no cover
            self.wrap_stdout()

        if os.environ.get('WRAP_STDERR'):  # pragma: no cover
            self.wrap_stderr()

    def start_capturing(self, bar=None):
        if bar:  # pragma: no branch
            self.listeners.add(bar)

        self.capturing += 1
        self.update_capturing()

    def stop_capturing(self, bar=None):
        if bar:  # pragma: no branch
            try:
                self.listeners.remove(bar)
            except KeyError:
                pass

        self.capturing -= 1
        self.update_capturing()

    def update_capturing(self):  # pragma: no cover
        if isinstance(self.stdout, WrappingIO):
            self.stdout.capturing = self.capturing > 0

        if isinstance(self.stderr, WrappingIO):
            self.stderr.capturing = self.capturing > 0

        if self.capturing <= 0:
            self.flush()

    def wrap(self, stdout=False, stderr=False):
        if stdout:
            self.wrap_stdout()

        if stderr:
            self.wrap_stderr()

    def wrap_stdout(self):
        self.wrap_excepthook()

        if not self.wrapped_stdout:
            self.stdout = sys.stdout = WrappingIO(self.original_stdout,
                                                  listeners=self.listeners)
        self.wrapped_stdout += 1

        return sys.stdout

    def wrap_stderr(self):
        self.wrap_excepthook()

        if not self.wrapped_stderr:
            self.stderr = sys.stderr = WrappingIO(self.original_stderr,
                                                  listeners=self.listeners)
        self.wrapped_stderr += 1

        return sys.stderr

    def unwrap_excepthook(self):
        if self.wrapped_excepthook:
            self.wrapped_excepthook -= 1
            sys.excepthook = self.original_excepthook

    def wrap_excepthook(self):
        if not self.wrapped_excepthook:
            logger.debug('wrapping excepthook')
            self.wrapped_excepthook += 1
            sys.excepthook = self.excepthook

    def unwrap(self, stdout=False, stderr=False):
        if stdout:
            self.unwrap_stdout()

        if stderr:
            self.unwrap_stderr()

    def unwrap_stdout(self):
        if self.wrapped_stdout > 1:
            self.wrapped_stdout -= 1
        else:
            sys.stdout = self.original_stdout
            self.wrapped_stdout = 0

    def unwrap_stderr(self):
        if self.wrapped_stderr > 1:
            self.wrapped_stderr -= 1
        else:
            sys.stderr = self.original_stderr
            self.wrapped_stderr = 0

    def flush(self):
        if self.wrapped_stdout:  # pragma: no branch
            try:
                self.stdout._flush()
            except (io.UnsupportedOperation,
                    AttributeError):  # pragma: no cover
                self.wrapped_stdout = False
                logger.warn('Disabling stdout redirection, %r is not seekable',
                            sys.stdout)

        if self.wrapped_stderr:  # pragma: no branch
            try:
                self.stderr._flush()
            except (io.UnsupportedOperation,
                    AttributeError):  # pragma: no cover
                self.wrapped_stderr = False
                logger.warn('Disabling stderr redirection, %r is not seekable',
                            sys.stderr)

    def excepthook(self, exc_type, exc_value, exc_traceback):
        self.original_excepthook(exc_type, exc_value, exc_traceback)
        self.flush()


streams = StreamWrapper()
logger = logging.getLogger(__name__)
