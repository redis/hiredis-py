#ifndef __READER_H
#define __READER_H

#include "hiredis.h"

typedef struct {
    PyObject_HEAD
    void *reader;
    PyObject *protocolErrorClass;
    PyObject *replyErrorClass;
} hiredis_ReaderObject;

extern PyTypeObject hiredis_ReaderType;
extern redisReplyObjectFunctions hiredis_ObjectFunctions;

#endif
