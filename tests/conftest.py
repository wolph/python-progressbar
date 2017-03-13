import progressbar
import logging


LOG_LEVELS = {
    '0': logging.ERROR,
    '1': logging.WARNING,
    '2': logging.INFO,
    '3': logging.DEBUG,
}


def pytest_configure(config):
    logging.basicConfig(
        level=LOG_LEVELS.get(config.option.verbose, logging.DEBUG))

    # Remove the update limit for tests by default
    progressbar.ProgressBar._MINIMUM_UPDATE_INTERVAL = 0.000001


