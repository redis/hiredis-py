#include "reader.h"

static void Reader_dealloc(hiredis_ReaderObject *self);
static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static PyObject *Reader_feed(hiredis_ReaderObject *self, PyObject *args);

static PyMethodDef hiredis_ReaderMethods[] = {
    {"feed", (PyCFunction)Reader_feed, METH_VARARGS, NULL },
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

static void Reader_dealloc(hiredis_ReaderObject *self) {
    redisReplyReaderFree(self->reader);
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject *Reader_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    hiredis_ReaderObject *self;
    self = (hiredis_ReaderObject*)type->tp_alloc(type, 0);
    if (self != NULL)
        self->reader = redisReplyReaderCreate();
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
