from __future__ import unicode_literals
from glob import glob

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
    size_t maxbuf;
    ...;
} redisReader;

redisReader *redisReaderCreate(void);
void redisReaderFree(redisReader *r);
int redisReaderFeed(redisReader *r, const char *buf, size_t len);
int redisReaderGetReply(redisReader *r, void **reply);

extern "Python" void *create_string(const redisReadTask*, char*, size_t);
extern "Python" void *create_array(const redisReadTask*, int);
extern "Python" void *create_integer(const redisReadTask*, long long);
extern "Python" void *create_nil(const redisReadTask*);
extern "Python" void free_object(void*);
""")

c_files = ['read', 'sds', 'hiredis', 'net']

sources = """
#include <hiredis.h>
#include <read.h>
#include <sds.h>
"""

for c_file in c_files:
    path = os.path.join(vendored_hiredis, '%s.c' % c_file)
    with open(path, 'rb') as f:
        sources += f.read()

    sources += "\n"


ffi.set_source('hiredis._cffi._hiredis',
               sources, include_dirs=[vendored_hiredis])

if __name__ == "__main__":
    ffi.compile(verbose=True)
