#include "hiredis.h"
#include "reader.h"

static PyMethodDef hiredis_methods[] = {
    {NULL}  /* Sentinel */
};

PyMODINIT_FUNC inithiredis(void) {
    PyObject* module;

    if (PyType_Ready(&hiredis_ReaderType) < 0)
        return;

    module = Py_InitModule3("hiredis", hiredis_methods, NULL);
    Py_INCREF(&hiredis_ReaderType);
    PyModule_AddObject(module, "Reader", (PyObject *)&hiredis_ReaderType);
}
