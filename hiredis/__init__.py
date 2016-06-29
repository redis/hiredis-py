import platform

if platform.python_implementation() == 'PyPy':
  from hiredis._cffi import Reader, HiredisError, ProtocolError, ReplyError
else:
  from .hiredis import Reader, HiredisError, ProtocolError, ReplyError
from .version import __version__

__all__ = [
  "Reader", "HiredisError", "ProtocolError", "ReplyError",
  "__version__"]
