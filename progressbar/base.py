# -*- mode: python; coding: utf-8 -*-

class FalseMeta(type):
    def __bool__(self):  # pragma: no cover
        return False

    def __cmp__(self, other):  # pragma: no cover
        return -1

    __nonzero__ = __bool__


class UnknownLength(metaclass=FalseMeta):
    pass


class Undefined(metaclass=FalseMeta):
    pass
