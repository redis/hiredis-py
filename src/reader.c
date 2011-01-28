#include <assert.h>
#include "reader.h"

static void Reader_dealloc(hiredis_ReaderObject *self);
static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static PyObject *Reader_feed(hiredis_ReaderObject *self, PyObject *args);
static PyObject *Reader_gets(hiredis_ReaderObject *self);

static PyMethodDef hiredis_ReaderMethods[] = {
    {"feed", (PyCFunction)Reader_feed, METH_VARARGS, NULL },
    {"gets", (PyCFunction)Reader_gets, METH_NOARGS, NULL },
    { NULL }  /* Sentinel */
};

PyTypeObject hiredis_ReaderType = {
    PyObject_HEAD_INIT(NULL)
    0,                            /*ob_size*/
    "hiredis.Reader",             /*tp_name*/
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
    Py_TPFLAGS_DEFAULT,           /*tp_flags*/
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
    0,                            /*tp_init */
    0,                            /*tp_alloc */
    Reader_new,                   /*tp_new */
};

static void *tryParentize(const redisReadTask *task, PyObject *obj) {
    PyObject *parent;
    if (task && task->parent) {
        parent = (PyObject*)task->parent->obj;
        assert(parent->ob_type == PyList_Type);
        PyList_SET_ITEM(parent, task->idx, obj);
    }
    return obj;
}

static void *createStringObject(const redisReadTask *task, char *str, size_t len) {
    PyObject *obj;

    if (task->type == REDIS_REPLY_ERROR) {
        PyObject *args = Py_BuildValue("(s#)", str, len);
        assert(args != NULL); /* TODO: properly handle OOM etc */
        obj = PyObject_CallObject(HiErr_ReplyError, args);
        assert(obj != NULL);
        Py_DECREF(args);
    } else {
        obj = PyString_FromStringAndSize(str, len);
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
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    hiredis_ReaderObject *self;
    self = (hiredis_ReaderObject*)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->reader = redisReplyReaderCreate();
        redisReplyReaderSetReplyObjectFunctions(self->reader, &hiredis_ObjectFunctions);
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
        PyErr_SetString(HiErr_ProtocolError, err);
        return NULL;
    }

    if (obj == NULL) {
        Py_RETURN_FALSE;
    } else {
        return obj;
    }
}
