import os
from cffi import FFI

try:
    from setuptools import setup, Extension
    from setuptools.command import install_lib as _install_lib
except ImportError:
    from distutils.core import setup, Extension
    from distutils.command import install_lib as _install_lib

vendored_hiredis = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../vendor/hiredis')

ffi = FFI()

ffi.cdef("""
#define REDIS_OK ...
#define REDIS_ERR ...
#define REDIS_REPLY_ERROR ...

typedef struct redisReadTask {
    int type;
    int elements;
    int idx;
    void *obj;
    struct redisReadTask *parent;
void *privdata;
} redisReadTask;

typedef struct redisReplyObjectFunctions {
    void *(*createString)(const redisReadTask*, char*, size_t);
    void *(*createArray)(const redisReadTask*, int);
    void *(*createInteger)(const redisReadTask*, long long);
    void *(*createNil)(const redisReadTask*);
    void (*freeObject)(void*);
} redisReplyObjectFunctions;

typedef struct redisReader {
    int err;
    char errstr[...];
    redisReplyObjectFunctions *fn;
    void *privdata;
    ...;
} redisReader;

redisReader *redisReaderCreate(void);
void redisReaderFree(redisReader *r);
int redisReaderFeed(redisReader *r, const char *buf, size_t len);
int redisReaderGetReply(redisReader *r, void **reply);
""")


ffi.set_source('_cffi._hiredis',
"""
#include <hiredis.h>
""", include_dirs=[vendored_hiredis], libraries=['hiredis_for_hiredis_py'])

if __name__ == "__main__":
    ffi.compile()
