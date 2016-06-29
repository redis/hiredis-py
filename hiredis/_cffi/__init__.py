from __future__ import unicode_literals
from sys import version_info

from hiredis._cffi._hiredis import ffi, lib

REDIS_READER_MAX_BUF = 1024 * 16

if version_info[0] == 3:
    int_type = int
else:
    int_type = long


class HiredisError(Exception):
    pass


class ProtocolError(HiredisError):
    pass


class ReplyError(HiredisError):
    pass


class _GlobalHandles(object):
    def __init__(self):
        self._handles = set()

    def new(self, obj):
        obj_id = ffi.new_handle(obj)
        self._handles.add(obj_id)
        return obj_id

    def get(self, obj_id):
        return ffi.from_handle(obj_id)

    def free(self, obj_id):
        obj = ffi.from_handle(obj_id)
        self._handles.discard(obj_id)
        return obj


_global_handles = _GlobalHandles()


def _parentize(task, obj):
    if task and task.parent:
        parent = _global_handles.get(task.parent.obj)
        assert isinstance(parent, list)
        parent[task.idx] = obj


@ffi.def_extern()
def create_string(task, s, length):
    task = ffi.cast("redisReadTask*", task)
    self = ffi.from_handle(task.privdata)
    data = ffi.string(s, length)
    if task.type == lib.REDIS_REPLY_ERROR:
        data = self._reply_error(data)
    elif self._encoding is not None:
        try:
            data = data.decode(self._encoding)
        except ValueError:
            # for compatibility with hiredis
            pass
        except Exception as err:
            self._exception = err
            data = None
    _parentize(task, data)
    return _global_handles.new(data)


@ffi.def_extern()
def create_array(task, i):
    task = ffi.cast("redisReadTask*", task)
    data = [None] * i
    _parentize(task, data)
    return _global_handles.new(data)


@ffi.def_extern()
def create_integer(task, n):
    task = ffi.cast("redisReadTask*", task)
    data = int_type(n)
    _parentize(task, data)
    return _global_handles.new(data)


@ffi.def_extern()
def create_nil(task):
    task = ffi.cast("redisReadTask*", task)
    data = None
    _parentize(task, data)
    return _global_handles.new(data)


@ffi.def_extern()
def free_object(obj):
    _global_handles.free(obj)


class Reader(object):
    """Hiredis protocol reader"""

    def __init__(self, protocolError=None, replyError=None, encoding=None):
        self._protocol_error = ProtocolError
        self._reply_error = ReplyError
        self._encoding = encoding or None

        if protocolError:
            if not callable(protocolError):
                raise TypeError("Expected a callable")
            self._protocol_error = protocolError

        if replyError:
            if not callable(replyError):
                raise TypeError("Expected a callable")
            self._reply_error = replyError

        self._self_handle = ffi.new_handle(self)
        self._exception = None

        self._reader = lib.redisReaderCreate()
        self._reader.privdata = self._self_handle
        self._reader.fn.createString = lib.create_string
        self._reader.fn.createArray = lib.create_array
        self._reader.fn.createInteger = lib.create_integer
        self._reader.fn.createNil = lib.create_nil
        self._reader.fn.freeObject = lib.free_object

    def feed(self, buf, offset=None, length=None):
        if offset is None:
            offset = 0
        if length is None:
            length = len(buf) - offset

        if offset < 0 or length < 0:
            raise ValueError("negative input")

        if offset + length > len(buf):
            raise ValueError("input is larger than buffer size")

        if isinstance(buf, bytearray):
            c_buf = ffi.new("char[]", length)
            for i in range(length):
                c_buf[i] = chr(buf[offset + i])
        else:
            c_buf = ffi.new("char[]", buf[offset:offset + length])
        lib.redisReaderFeed(self._reader, c_buf, length)

    def gets(self):
        reply = ffi.new("void **")
        result = lib.redisReaderGetReply(self._reader, reply)

        if result != lib.REDIS_OK:
            errstr = ffi.string(self._reader.errstr)
            raise self._protocol_error(errstr)

        if reply[0] == ffi.NULL:
            return False

        if self._exception:
            err, self._exception = self._exception, None
            raise err

        return _global_handles.free(reply[0])

    def getmaxbuf(self):
        return self._reader.maxbuf

    def setmaxbuf(self, maxbuf):
        if maxbuf is None:
            maxbuf = REDIS_READER_MAX_BUF

        if maxbuf < 0:
            raise ValueError("maxbuf value out of range")

        self._reader.maxbuf = maxbuf
