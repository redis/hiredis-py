#ifndef __READER_H
#define __READER_H

#include "hiredis.h"

typedef struct {
    PyObject_HEAD
    redisReader *reader;
    char *encoding;
    char *errors;
    int shouldDecode;
    PyObject *protocolErrorClass;
    PyObject *replyErrorClass;
    PyObject *notEnoughDataObject;

    /* Stores error object in between incomplete calls to #gets, in order to
     * only set the error once a full reply has been read. Otherwise, the
     * reader could get in an inconsistent state. */
    struct {
        PyObject *ptype;
        PyObject *pvalue;
        PyObject *ptraceback;
    } error;

#ifdef Py_GIL_DISABLED
    /* Per-instance mutex protecting reader state under free-threaded Python.
     * Zero-initialized by tp_alloc and never deinitialized (PyMutex has no
     * destructor). */
    PyMutex lock;
#endif
} hiredis_ReaderObject;

#ifdef Py_GIL_DISABLED
#define HIREDIS_READER_LOCK(self)   PyMutex_Lock(&(self)->lock)
#define HIREDIS_READER_UNLOCK(self) PyMutex_Unlock(&(self)->lock)
#else
#define HIREDIS_READER_LOCK(self)   ((void)0)
#define HIREDIS_READER_UNLOCK(self) ((void)0)
#endif

typedef struct {
    PyListObject list;
} PushNotificationObject;

extern PyTypeObject hiredis_ReaderType;
extern PyTypeObject PushNotificationType;
extern redisReplyObjectFunctions hiredis_ObjectFunctions;

#endif
