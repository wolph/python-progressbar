import sys


class LineOffsetStreamWrapper:
    UP = '\033[F'
    DOWN = '\033[B'

    def __init__(self, lines=0, stream=sys.stderr):
        self.stream = stream
        self.lines = lines

    def write(self, data):
        # Move the cursor up
        self.stream.write(self.UP * self.lines)
        # Print a carriage return to reset the cursor position
        self.stream.write('\r')
        # Print the data without newlines so we don't change the position
        self.stream.write(data.rstrip('\n'))
        # Move the cursor down
        self.stream.write(self.DOWN * self.lines)

        self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)
