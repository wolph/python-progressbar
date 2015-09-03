
def timedelta_to_seconds(delta):
    '''Convert a timedelta to seconds with the microseconds as fraction

    >>> from datetime import timedelta
    >>> timedelta_to_seconds(timedelta(days=1))
    86400
    >>> timedelta_to_seconds(timedelta(seconds=1))
    1
    >>> timedelta_to_seconds(timedelta(seconds=1, microseconds=1))
    1.000001
    >>> timedelta_to_seconds(timedelta(microseconds=1))
    1e-06
    '''
    # Only convert to float if needed
    if delta.microseconds:
        total = delta.microseconds * 1e-6
    else:
        total = 0
    total += delta.seconds
    total += delta.days * 60 * 60 * 24
    return total

