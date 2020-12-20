import logging
from os import path


class DynPathFileHandler(logging.FileHandler):
    """A handler class which writes formatted logging records to disk files."""

    def __init__(self, filename, dirpath='.', mode='a', encoding=None, delay=False, errors=None):  # noqa: WPS211
        """Open the specified file and use it as the stream for logging."""  # noqa: DAR101
        super().__init__(
            path.join(path.expanduser(dirpath), filename),
            mode,
            encoding,
            delay,
            errors,
        )
