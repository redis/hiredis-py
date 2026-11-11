#ifndef __READER_H
#define __READER_H

#include "hiredis.h"

typedef struct {
    PyObject_HEAD
    redisReader *reader;
    /* Names for PyUnicode_Decode(), held in bytes objects owned by the Reader
     * (NULL means "no decoding" and "strict" respectively). They are replaced,
     * never modified, so that a decode in progress can keep its own reference
     * to the ones it uses. */
    PyObject *encoding;
    PyObject *errors;
    int shouldDecode;
    /* Set while gets() runs, so that the parser is not re-entered from a
     * callback or by another thread (see the note in reader.c). */
    int busy;
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
} hiredis_ReaderObject;

typedef struct {
    PyListObject list;
} PushNotificationObject;

extern PyTypeObject hiredis_ReaderType;
extern PyTypeObject PushNotificationType;
extern redisReplyObjectFunctions hiredis_ObjectFunctions;

#endif
