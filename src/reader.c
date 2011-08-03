#include <assert.h>
#include "reader.h"

static void Reader_dealloc(hiredis_ReaderObject *self);
static int Reader_init(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds);
static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static PyObject *Reader_feed(hiredis_ReaderObject *self, PyObject *args);
static PyObject *Reader_gets(hiredis_ReaderObject *self);

static PyMethodDef hiredis_ReaderMethods[] = {
    {"feed", (PyCFunction)Reader_feed, METH_VARARGS, NULL },
    {"gets", (PyCFunction)Reader_gets, METH_NOARGS, NULL },
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
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "Hiredis protocol reader",    /*tp_doc */
    0,                            /*tp_traverse */
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

static void *tryParentize(const redisReadTask *task, PyObject *obj) {
    PyObject *parent;
    if (task && task->parent) {
        parent = (PyObject*)task->parent->obj;
        assert(PyList_CheckExact(parent));
        PyList_SET_ITEM(parent, task->idx, obj);
    }
    return obj;
}

static PyObject *createDecodedString(hiredis_ReaderObject *self, const char *str, size_t len) {
    PyObject *obj;

    if (self->encoding == NULL) {
        obj = PyBytes_FromStringAndSize(str, len);
    } else {
        obj = PyUnicode_Decode(str, len, self->encoding, NULL);
        if (obj == NULL) {
            if (PyErr_ExceptionMatches(PyExc_ValueError)) {
                /* Ignore encoding and simply return plain string. */
                obj = PyBytes_FromStringAndSize(str, len);
            } else {
                assert(PyErr_ExceptionMatches(PyExc_LookupError));

                /* Store error when this is the first. */
                if (self->error.ptype == NULL)
                    PyErr_Fetch(&(self->error.ptype), &(self->error.pvalue),
                            &(self->error.ptraceback));

                /* Return Py_None as placeholder to let the error bubble up and
                 * be used when a full reply in Reader#gets(). */
                obj = Py_None;
                Py_INCREF(obj);
            }

            PyErr_Clear();
        }
    }

    assert(obj != NULL);
    return obj;
}

static void *createStringObject(const redisReadTask *task, char *str, size_t len) {
    hiredis_ReaderObject *self = (hiredis_ReaderObject*)task->privdata;
    PyObject *obj;

    if (task->type == REDIS_REPLY_ERROR) {
        PyObject *args = Py_BuildValue("(s#)", str, len);
        assert(args != NULL); /* TODO: properly handle OOM etc */
        obj = PyObject_CallObject(self->replyErrorClass, args);
        assert(obj != NULL);
        Py_DECREF(args);
    } else {
        obj = createDecodedString(self, str, len);
    }

    return tryParentize(task, obj);
}

static void *createArrayObject(const redisReadTask *task, int elements) {
    PyObject *obj;
    obj = PyList_New(elements);
    return tryParentize(task, obj);
}

static void *createIntegerObject(const redisReadTask *task, long long value) {
    PyObject *obj;
    obj = PyLong_FromLongLong(value);
    return tryParentize(task, obj);
}

static void *createNilObject(const redisReadTask *task) {
    PyObject *obj = Py_None;
    Py_INCREF(obj);
    return tryParentize(task, obj);
}

static void freeObject(void *obj) {
    Py_XDECREF(obj);
}

redisReplyObjectFunctions hiredis_ObjectFunctions = {
    createStringObject,  // void *(*createString)(const redisReadTask*, char*, size_t);
    createArrayObject,   // void *(*createArray)(const redisReadTask*, int);
    createIntegerObject, // void *(*createInteger)(const redisReadTask*, long long);
    createNilObject,     // void *(*createNil)(const redisReadTask*);
    freeObject           // void (*freeObject)(void*);
};

static void Reader_dealloc(hiredis_ReaderObject *self) {
    redisReplyReaderFree(self->reader);
    if (self->encoding)
        free(self->encoding);

    ((PyObject *)self)->ob_type->tp_free((PyObject*)self);
}

static int _Reader_set_exception(PyObject **target, PyObject *value) {
    int subclass;
    subclass = PyObject_IsSubclass(value, PyExc_Exception);

    if (subclass == -1) {
        return 0;
    }

    if (subclass == 0) {
        PyErr_SetString(PyExc_TypeError, "Expected subclass of Exception");
        return 0;
    }

    Py_DECREF(*target);
    *target = value;
    Py_INCREF(*target);
    return 1;
}

static int Reader_init(hiredis_ReaderObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = { "protocolError", "replyError", "encoding", NULL };
    PyObject *protocolErrorClass = NULL;
    PyObject *replyErrorClass = NULL;
    PyObject *encodingObj = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OOO", kwlist,
        &protocolErrorClass, &replyErrorClass, &encodingObj))
            return -1;

    if (protocolErrorClass)
        if (!_Reader_set_exception(&self->protocolErrorClass, protocolErrorClass))
            return -1;

    if (replyErrorClass)
        if (!_Reader_set_exception(&self->replyErrorClass, replyErrorClass))
            return -1;

    if (encodingObj) {
        PyObject *encbytes;
        char *encstr;
        int enclen;

        if (PyUnicode_Check(encodingObj))
            encbytes = PyUnicode_AsASCIIString(encodingObj);
        else
            encbytes = PyObject_Bytes(encodingObj);

        if (encbytes == NULL)
            return -1;

        enclen = PyBytes_Size(encbytes);
        encstr = PyBytes_AsString(encbytes);
        self->encoding = (char*)malloc(enclen+1);
        memcpy(self->encoding, encstr, enclen);
        self->encoding[enclen] = '\0';
        Py_DECREF(encbytes);
    }

    return 0;
}

static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    hiredis_ReaderObject *self;
    self = (hiredis_ReaderObject*)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->reader = redisReplyReaderCreate();
        self->reader->fn = &hiredis_ObjectFunctions;
        self->reader->privdata = self;

        self->encoding = NULL;
        self->protocolErrorClass = HIREDIS_STATE->HiErr_ProtocolError;
        self->replyErrorClass = HIREDIS_STATE->HiErr_ReplyError;
        Py_INCREF(self->protocolErrorClass);
        Py_INCREF(self->replyErrorClass);

        self->error.ptype = NULL;
        self->error.pvalue = NULL;
        self->error.ptraceback = NULL;
    }
    return (PyObject*)self;
}

static PyObject *Reader_feed(hiredis_ReaderObject *self, PyObject *args) {
    const char *str;
    int len;

    if (!PyArg_ParseTuple(args, "s#", &str, &len))
        return NULL;

    redisReplyReaderFeed(self->reader, str, len);
    Py_RETURN_NONE;
}

static PyObject *Reader_gets(hiredis_ReaderObject *self) {
    PyObject *obj;
    char *err;

    if (redisReplyReaderGetReply(self->reader, (void**)&obj) == REDIS_ERR) {
        err = redisReplyReaderGetError(self->reader);
        PyErr_SetString(self->protocolErrorClass, err);
        return NULL;
    }

    if (obj == NULL) {
        Py_RETURN_FALSE;
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
