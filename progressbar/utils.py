
def timedelta_to_seconds(delta):
        return (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) *
                10 ** 6 / 10 ** 6)
