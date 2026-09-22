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

    /* Map keys waiting for their value. A map is fed to us as a flat
     * key/value sequence, so the key has to be held somewhere until its value
     * arrives; holding it here rather than parking it in the dict under a
     * placeholder lets each pair cost a single dict insertion.
     *
     * A stack rather than a single slot: a container in value position is
     * parented as soon as its header is read, which takes the key it belongs
     * to back off the stack, so ordinary nesting never holds more than one
     * key. A map in *key* position is instead buffered from its header until
     * its own contents have been parsed, so each level of that nesting adds an
     * entry. Entries are owned references, and they survive across #feed /
     * #gets calls because a reply can be split over several reads. */
    PyObject **pendingKeys;
    Py_ssize_t pendingCount;
    Py_ssize_t pendingCapacity;

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
