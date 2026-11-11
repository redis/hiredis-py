#include "reader.h"

#include <assert.h>
#include <Python.h>

static void Reader_dealloc(hiredis_ReaderObject *self);
static int Reader_traverse(hiredis_ReaderObject *self, visitproc visit, void *arg);
static int Reader_init(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds);
static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static PyObject *Reader_feed(hiredis_ReaderObject *self, PyObject *args);
static PyObject *Reader_gets(hiredis_ReaderObject *self, PyObject *args);
static PyObject *Reader_setmaxbuf(hiredis_ReaderObject *self, PyObject *arg);
static PyObject *Reader_getmaxbuf(hiredis_ReaderObject *self);
static PyObject *Reader_len(hiredis_ReaderObject *self);
static PyObject *Reader_has_data(hiredis_ReaderObject *self);
static PyObject *Reader_set_encoding(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds);

static int PushNotificationType_init(PushNotificationObject *self, PyObject *args, PyObject *kwds);
/* Create a new instance of PushNotificationType with preallocated number of elements */
static PyObject* PushNotificationType_New(Py_ssize_t size);

static PyMethodDef hiredis_ReaderMethods[] = {
    {"feed", (PyCFunction)Reader_feed, METH_VARARGS, NULL },
    {"gets", (PyCFunction)Reader_gets, METH_VARARGS, NULL },
    {"setmaxbuf", (PyCFunction)Reader_setmaxbuf, METH_O, NULL },
    {"getmaxbuf", (PyCFunction)Reader_getmaxbuf, METH_NOARGS, NULL },
    {"len", (PyCFunction)Reader_len, METH_NOARGS, NULL },
    {"has_data", (PyCFunction)Reader_has_data, METH_NOARGS, NULL },
    {"set_encoding", (PyCFunction)Reader_set_encoding, METH_VARARGS | METH_KEYWORDS, NULL },
    { NULL }  /* Sentinel */
};

PyTypeObject hiredis_ReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    MOD_HIREDIS ".Reader",        /*tp_name*/
    sizeof(hiredis_ReaderObject), /*tp_basicsize*/
    0,                            /*tp_itemsize*/
    (destructor)Reader_dealloc,   /*tp_dealloc*/
    0,                            /*tp_print*/
    0,                            /*tp_getattr*/
    0,                            /*tp_setattr*/
    0,                            /*tp_compare*/
    0,                            /*tp_repr*/
    0,                            /*tp_as_number*/
    0,                            /*tp_as_sequence*/
    0,                            /*tp_as_mapping*/
    0,                            /*tp_hash */
    0,                            /*tp_call*/
    0,                            /*tp_str*/
    0,                            /*tp_getattro*/
    0,                            /*tp_setattro*/
    0,                            /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    "Hiredis protocol reader",    /*tp_doc */
    (traverseproc)Reader_traverse,/*tp_traverse */
    0,                            /*tp_clear */
    0,                            /*tp_richcompare */
    0,                            /*tp_weaklistoffset */
    0,                            /*tp_iter */
    0,                            /*tp_iternext */
    hiredis_ReaderMethods,        /*tp_methods */
    0,                            /*tp_members */
    0,                            /*tp_getset */
    0,                            /*tp_base */
    0,                            /*tp_dict */
    0,                            /*tp_descr_get */
    0,                            /*tp_descr_set */
    0,                            /*tp_dictoffset */
    (initproc)Reader_init,        /*tp_init */
    0,                            /*tp_alloc */
    Reader_new,                   /*tp_new */
};

PyTypeObject PushNotificationType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = MOD_HIREDIS ".PushNotification",
    .tp_basicsize = sizeof(PushNotificationObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_doc = "Redis PUSH notification type",
    .tp_init = (initproc) PushNotificationType_init,
};

static void *tryParentize(const redisReadTask *task, PyObject *obj) {
    PyObject *parent;
    if (obj == NULL) {
        /* The caller failed to allocate; propagate so hiredis reports OOM. */
        return NULL;
    }
    if (task && task->parent) {
        parent = (PyObject*)task->parent->obj;
        switch (task->parent->type) {
            case REDIS_REPLY_MAP:
                if (task->idx % 2 == 0) {
                    /* Set a temporary item to save the object as a key. */
                    int res = PyDict_SetItem(parent, obj, Py_None);
                    Py_DECREF(obj);

                    if (res == -1) {
                        return NULL;
                    }
                } else {
                    /* Pop the temporary item and set proper key and value. */
                    PyObject *last_item = PyObject_CallMethod(parent, "popitem", NULL);
                    PyObject *last_key = PyTuple_GetItem(last_item, 0);
                    PyDict_SetItem(parent, last_key, obj);
                    Py_DECREF(last_item);
                    Py_DECREF(obj);
                }
                break;
            default:
                assert(PyList_Check(parent));
                PyList_SET_ITEM(parent, task->idx, obj);
        }
    }
    return obj;
}

static PyObject *createDecodedString(hiredis_ReaderObject *self, const char *str, size_t len) {
    PyObject *obj;

    if (self->encoding == NULL || !self->shouldDecode) {
        obj = PyBytes_FromStringAndSize(str, len);
    } else {
        /* Decoding can run Python code (a codec or an error handler) that
         * replaces this Reader's encoding, so hold references to the names. */
        PyObject *encoding = self->encoding;
        PyObject *errors = self->errors;

        Py_INCREF(encoding);
        Py_XINCREF(errors);
        obj = PyUnicode_Decode(str, len, PyBytes_AsString(encoding),
                               errors ? PyBytes_AsString(errors) : NULL);
        Py_DECREF(encoding);
        Py_XDECREF(errors);
        if (obj == NULL) {
            /* Store error when this is the first. */
            if (self->error.ptype == NULL)
                PyErr_Fetch(&(self->error.ptype), &(self->error.pvalue),
                        &(self->error.ptraceback));

            /* Return Py_None as placeholder to let the error bubble up and
             * be used when a full reply in Reader#gets(). */
            obj = Py_None;
            Py_INCREF(obj);
            PyErr_Clear();
        }
    }

    assert(obj != NULL);
    return obj;
}

static void *createError(PyObject *errorCallable, char *errstr, size_t len) {
    PyObject *obj, *errmsg;

    errmsg = PyUnicode_DecodeUTF8(errstr, len, "replace");
    assert(errmsg != NULL); /* TODO: properly handle OOM etc */

    obj = PyObject_CallFunctionObjArgs(errorCallable, errmsg, NULL);
    Py_DECREF(errmsg);
    /* obj can be NULL if custom error class raised another exception */

    return obj;
}

static void *createStringObject(const redisReadTask *task, char *str, size_t len) {
    hiredis_ReaderObject *self = (hiredis_ReaderObject*)task->privdata;
    PyObject *obj;

    if (task->type == REDIS_REPLY_ERROR) {
        obj = createError(self->replyErrorClass, str, len);
        if (obj == NULL) {
            if (self->error.ptype == NULL)
                PyErr_Fetch(&(self->error.ptype), &(self->error.pvalue),
                        &(self->error.ptraceback));
            obj = Py_None;
            Py_INCREF(obj);
        }
    } else {
        if (task->type == REDIS_REPLY_VERB) {
            /* Skip 4 bytes of verbatim type header. */
            memmove(str, str+4, len);
            len -= 4;
        }
        obj = createDecodedString(self, str, len);
    }
    return tryParentize(task, obj);
}

static void *createArrayObject(const redisReadTask *task, size_t elements) {
    PyObject *obj;
    switch (task->type) {
        case REDIS_REPLY_MAP:
            obj = PyDict_New();
            break;
        case REDIS_REPLY_PUSH:
            obj = PushNotificationType_New(elements);
            break;
        default:
            obj = PyList_New(elements);
    }
    return tryParentize(task, obj);
}

static void *createIntegerObject(const redisReadTask *task, long long value) {
    PyObject *obj;
    obj = PyLong_FromLongLong(value);
    return tryParentize(task, obj);
}

static void *createDoubleObject(const redisReadTask *task, double value, char *str, size_t le) {
    PyObject *obj;
    obj = PyFloat_FromDouble(value);
    return tryParentize(task, obj);
}

static void *createNilObject(const redisReadTask *task) {
    PyObject *obj = Py_None;
    Py_INCREF(obj);
    return tryParentize(task, obj);
}

static void *createBoolObject(const redisReadTask *task, int bval) {
    PyObject *obj;
    obj = PyBool_FromLong((long)bval);
    return tryParentize(task, obj);
}

static void freeObject(void *obj) {
    Py_XDECREF(obj);
}

static int PushNotificationType_init(PushNotificationObject *self, PyObject *args, PyObject *kwds) {
    return PyList_Type.tp_init((PyObject *)self, args, kwds);
}

static PyObject* PushNotificationType_New(Py_ssize_t size) {
    /* Check for negative size */
    if (size < 0) {
        PyErr_SetString(PyExc_SystemError, "negative list size");
        return NULL;
    }

    /* Check for potential overflow */
    if ((size_t)size > PY_SSIZE_T_MAX / sizeof(PyObject*)) {
        return PyErr_NoMemory();
    }

#ifdef PYPY_VERSION
    PyObject* obj = PyObject_CallObject((PyObject *) &PushNotificationType, NULL);    
#else
    PyObject* obj = PyType_GenericNew(&PushNotificationType, NULL, NULL);
#endif
    if (obj == NULL) {
        return NULL;
    }

    /* Pre-sizes the notification, whose elements are filled in as they parse.
     * PyList_SetSlice does not steal a reference to the list it is handed, so
     * it has to be released here. */
    PyObject* items = PyList_New(size);
    if (items == NULL) {
        Py_DECREF(obj);
        return NULL;
    }

    int res = PyList_SetSlice(obj, PY_SSIZE_T_MAX, PY_SSIZE_T_MAX, items);
    Py_DECREF(items);

    if (res == -1) {
        Py_DECREF(obj);
        return NULL;
    }

    return obj;
}

redisReplyObjectFunctions hiredis_ObjectFunctions = {
    createStringObject,  // void *(*createString)(const redisReadTask*, char*, size_t);
    createArrayObject,   // void *(*createArray)(const redisReadTask*, size_t);
    createIntegerObject, // void *(*createInteger)(const redisReadTask*, long long);
    createDoubleObject,  // void *(*createDoubleObject)(const redisReadTask*, double, char*, size_t);
    createNilObject,     // void *(*createNil)(const redisReadTask*);
    createBoolObject,    // void *(*createBoolObject)(const redisReadTask*, int);
    freeObject           // void (*freeObject)(void*);
};

static void Reader_dealloc(hiredis_ReaderObject *self) {
    PyObject_GC_UnTrack(self);
    Py_CLEAR(self->encoding);
    Py_CLEAR(self->errors);
    redisReaderFree(self->reader);
    Py_CLEAR(self->protocolErrorClass);
    Py_CLEAR(self->replyErrorClass);
    Py_CLEAR(self->notEnoughDataObject);

    ((PyObject *)self)->ob_type->tp_free((PyObject*)self);
}

static int Reader_traverse(hiredis_ReaderObject *self, visitproc visit, void *arg) {
    Py_VISIT(self->protocolErrorClass);
    Py_VISIT(self->replyErrorClass);
    Py_VISIT(self->notEnoughDataObject);
    return 0;
}

static int _Reader_set_exception(PyObject **target, PyObject *value) {
    int callable;
    callable = PyCallable_Check(value);

    if (callable == 0) {
        PyErr_SetString(PyExc_TypeError, "Expected a callable");
        return 0;
    }

    Py_DECREF(*target);
    *target = value;
    Py_INCREF(*target);
    return 1;
}

/* Replaces *target with a copy of name in a bytes object, or clears it if name
 * is NULL. The "z" format of PyArg_Parse*() hands out a pointer into the
 * argument object, which can be freed as soon as the call returns, so the
 * Reader must not keep that pointer. */
static int _Reader_set_name(PyObject **target, const char *name) {
    PyObject *copy = NULL, *old;

    if (name) {
        copy = PyBytes_FromStringAndSize(name, strlen(name));
        if (!copy)
            return -1;
    }
    old = *target;
    *target = copy;
    Py_XDECREF(old);
    return 0;
}

static int _Reader_set_encoding(hiredis_ReaderObject *self, char *encoding, char *errors) {
    PyObject *codecs, *result;

    if (encoding) {  // validate that the encoding exists, raises LookupError if not
        codecs = PyImport_ImportModule("codecs");
        if (!codecs)
            return -1;
        result = PyObject_CallMethod(codecs, "lookup", "s", encoding);
        Py_DECREF(codecs);
        if (!result)
            return -1;
        Py_DECREF(result);
    }
    if (_Reader_set_name(&self->encoding, encoding) == -1)
        return -1;

    if (errors) {   // validate that the error handler exists, raises LookupError if not
        codecs = PyImport_ImportModule("codecs");
        if (!codecs)
            return -1;
        result = PyObject_CallMethod(codecs, "lookup_error", "s", errors);
        Py_DECREF(codecs);
        if (!result)
            return -1;
        Py_DECREF(result);
    }
    // NULL errors means "strict", which is what PyUnicode_Decode() assumes
    return _Reader_set_name(&self->errors, errors);
}

/* Thread safety on free-threaded builds
 *
 * A Reader holds mutable state (the hiredis buffer and parse stack, the decode
 * settings and a stashed error) that must not be touched by two threads at
 * once. Every method that reads or writes it runs inside a critical section on
 * the Reader (Py_BEGIN_CRITICAL_SECTION), which makes each call atomic with
 * respect to the others. With a GIL these are no-ops.
 *
 * A critical section is released while its thread is paused: when it blocks, or
 * when the interpreter stops the world (a GC run started by any thread). That
 * can happen while Python code runs inside gets(): a protocolError/replyError
 * callable, a custom codec or an error handler. Another thread could then enter
 * the parser in the middle of a reply and take or corrupt it, as it can with a
 * GIL when the interpreter switches threads. The parser cannot be re-entered:
 * gets() would take the reply being built, feed() can move the buffer that a
 * decode is reading, and __init__() replaces the callables being called. So
 * gets() marks the Reader busy while it runs, and feed(), gets() and __init__()
 * raise RuntimeError if they are called in the meantime, from the callback
 * itself or from another thread. The other methods only read or replace single
 * fields, and a decode in progress holds its own references to the encoding and
 * errors names, so they stay safe. */

/* Raises RuntimeError if a gets() call is still running on this Reader. */
static int Reader_check_idle(hiredis_ReaderObject *self, const char *method) {
    if (self->busy) {
        PyErr_Format(PyExc_RuntimeError,
                     "Reader.%s() called while Reader.gets() is still running "
                     "on this Reader, from a callback or another thread",
                     method);
        return -1;
    }
    return 0;
}

static int Reader_init_impl(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = { "protocolError", "replyError", "encoding", "errors", "notEnoughData", NULL };
    PyObject *protocolErrorClass = NULL;
    PyObject *replyErrorClass = NULL;
    PyObject *notEnoughData = NULL;
    char *encoding = NULL;
    char *errors = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OOzzO", kwlist,
        &protocolErrorClass, &replyErrorClass, &encoding, &errors, &notEnoughData))
            return -1;

    if (protocolErrorClass)
        if (!_Reader_set_exception(&self->protocolErrorClass, protocolErrorClass))
            return -1;

    if (replyErrorClass)
        if (!_Reader_set_exception(&self->replyErrorClass, replyErrorClass))
            return -1;

    if (notEnoughData) {
        Py_DECREF(self->notEnoughDataObject);
        self->notEnoughDataObject = notEnoughData;

        Py_INCREF(self->notEnoughDataObject);
    }

    return _Reader_set_encoding(self, encoding, errors);
}

static int Reader_init(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds) {
    int res = -1;
    Py_BEGIN_CRITICAL_SECTION(self);
    if (Reader_check_idle(self, "__init__") == 0)
        res = Reader_init_impl(self, args, kwds);
    Py_END_CRITICAL_SECTION();
    return res;
}

static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    hiredis_ReaderObject *self;
    self = (hiredis_ReaderObject*)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->reader = redisReaderCreateWithFunctions(NULL);
        self->reader->fn = &hiredis_ObjectFunctions;
        self->reader->privdata = self;

        self->encoding = NULL;
        self->errors = NULL;  // NULL means "strict" to PyUnicode_Decode()
        self->notEnoughDataObject = Py_False;
        self->shouldDecode = 1;
        self->busy = 0;
        self->protocolErrorClass = HIREDIS_STATE->HiErr_ProtocolError;
        self->replyErrorClass = HIREDIS_STATE->HiErr_ReplyError;
        Py_INCREF(self->protocolErrorClass);
        Py_INCREF(self->replyErrorClass);
        Py_INCREF(self->notEnoughDataObject);

        self->error.ptype = NULL;
        self->error.pvalue = NULL;
        self->error.ptraceback = NULL;
    }
    return (PyObject*)self;
}

static PyObject *Reader_feed(hiredis_ReaderObject *self, PyObject *args) {
    Py_buffer buf;
    Py_ssize_t off = 0;
    Py_ssize_t len = -1;
    int refused;

    if (!PyArg_ParseTuple(args, "s*|nn", &buf, &off, &len)) {
        return NULL;
    }

    if (len == -1) {
      len = buf.len - off;
    }

    if (off < 0 || len < 0) {
      PyErr_SetString(PyExc_ValueError, "negative input");
      goto error;
    }

    if ((off + len) > buf.len) {
      PyErr_SetString(PyExc_ValueError, "input is larger than buffer size");
      goto error;
    }

    Py_BEGIN_CRITICAL_SECTION(self);
    refused = Reader_check_idle(self, "feed");
    if (!refused)
        redisReaderFeed(self->reader, (char *)buf.buf + off, len);
    Py_END_CRITICAL_SECTION();
    PyBuffer_Release(&buf);
    if (refused)
        return NULL;
    Py_RETURN_NONE;

error:
    PyBuffer_Release(&buf);
    return NULL;
}

static PyObject *Reader_gets_impl(hiredis_ReaderObject *self, PyObject *args) {
    PyObject *obj;

    self->shouldDecode = 1;
    if (!PyArg_ParseTuple(args, "|i", &self->shouldDecode)) {
        return NULL;
    }

    if (redisReaderGetReply(self->reader, (void**)&obj) == REDIS_ERR) {
        PyObject *err = NULL;
        char *errstr = NULL;

        // Checking if there is no error during the call to redisReaderGetReply
        // to avoid getting a SystemError.
        if (PyErr_Occurred() == NULL) {
            errstr = redisReaderGetError(self->reader);
            /* protocolErrorClass might be a callable. call it, then use it's type */
            err = createError(self->protocolErrorClass, errstr, strlen(errstr));
        }

        if (err != NULL) {
            obj = PyObject_Type(err);
            PyErr_SetString(obj, errstr);
            Py_DECREF(obj);
            Py_DECREF(err);
        }
        return NULL;
    }

    if (obj == NULL) {
        Py_INCREF(self->notEnoughDataObject);
        return self->notEnoughDataObject;
    } else {
        /* Restore error when there is one. */
        if (self->error.ptype != NULL) {
            Py_DECREF(obj);
            PyErr_Restore(self->error.ptype, self->error.pvalue,
                    self->error.ptraceback);
            self->error.ptype = NULL;
            self->error.pvalue = NULL;
            self->error.ptraceback = NULL;
            return NULL;
        }
        return obj;
    }
}

static PyObject *Reader_gets(hiredis_ReaderObject *self, PyObject *args) {
    PyObject *res = NULL;
    Py_BEGIN_CRITICAL_SECTION(self);
    if (Reader_check_idle(self, "gets") == 0) {
        self->busy = 1;
        res = Reader_gets_impl(self, args);
        self->busy = 0;
    }
    Py_END_CRITICAL_SECTION();
    return res;
}

static PyObject *Reader_setmaxbuf(hiredis_ReaderObject *self, PyObject *arg) {
    long maxbuf;

    if (arg == Py_None)
        maxbuf = REDIS_READER_MAX_BUF;
    else {
        maxbuf = PyLong_AsLong(arg);
        if (maxbuf < 0) {
            if (!PyErr_Occurred())
                PyErr_SetString(PyExc_ValueError,
                                "maxbuf value out of range");
            return NULL;
        }
    }
    Py_BEGIN_CRITICAL_SECTION(self);
    self->reader->maxbuf = maxbuf;
    Py_END_CRITICAL_SECTION();

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *Reader_getmaxbuf(hiredis_ReaderObject *self) {
    size_t maxbuf;
    Py_BEGIN_CRITICAL_SECTION(self);
    maxbuf = self->reader->maxbuf;
    Py_END_CRITICAL_SECTION();
    return PyLong_FromSize_t(maxbuf);
}

static PyObject *Reader_len(hiredis_ReaderObject *self) {
    size_t len;
    Py_BEGIN_CRITICAL_SECTION(self);
    len = self->reader->len;
    Py_END_CRITICAL_SECTION();
    return PyLong_FromSize_t(len);
}

static PyObject *Reader_has_data(hiredis_ReaderObject *self) {
    int has_data;
    Py_BEGIN_CRITICAL_SECTION(self);
    has_data = self->reader->pos < self->reader->len;
    Py_END_CRITICAL_SECTION();
    if (has_data)
        Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

static PyObject *Reader_set_encoding_impl(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = { "encoding", "errors", NULL };
    char *encoding = NULL;
    char *errors = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|zz", kwlist, &encoding, &errors))
        return NULL;

    if(_Reader_set_encoding(self, encoding, errors) == -1)
        return NULL;

    Py_RETURN_NONE;

}

static PyObject *Reader_set_encoding(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds) {
    PyObject *res;
    Py_BEGIN_CRITICAL_SECTION(self);
    res = Reader_set_encoding_impl(self, args, kwds);
    Py_END_CRITICAL_SECTION();
    return res;
}
