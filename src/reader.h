#ifndef __READER_H
#define __READER_H

#include "hiredis.h"

typedef struct {
    PyObject_HEAD
    redisReader *reader;
    char *encoding;
    char *errors;
    int shouldDecode;
    /* Whether #encoding resolves to the UTF-8 codec, decided once by
     * _Reader_set_encoding rather than per decoded string. */
    int isUtf8;
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
