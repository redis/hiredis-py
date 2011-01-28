#include "hiredis.h"
#include "reader.h"

#define MOD_HIREDIS "hiredis"

PyObject *HiErr_Base;
PyObject *HiErr_ProtocolError;
PyObject *HiErr_ReplyError;

PyMODINIT_FUNC inithiredis(void) {
    PyObject *mod_hiredis;

    if (PyType_Ready(&hiredis_ReaderType) < 0)
        return;

    /* Setup custom exceptions */
    HiErr_Base = PyErr_NewException(MOD_HIREDIS ".HiredisError", PyExc_Exception, NULL);
    HiErr_ProtocolError = PyErr_NewException(MOD_HIREDIS ".ProtocolError", HiErr_Base, NULL);
    HiErr_ReplyError = PyErr_NewException(MOD_HIREDIS ".ReplyError", HiErr_Base, NULL);

    mod_hiredis = Py_InitModule3("hiredis", NULL, NULL);
    PyModule_AddObject(mod_hiredis, "HiredisError", HiErr_Base);
    PyModule_AddObject(mod_hiredis, "ProtocolError", HiErr_ProtocolError);
    PyModule_AddObject(mod_hiredis, "ReplyError", HiErr_ReplyError);

    Py_INCREF(&hiredis_ReaderType);
    PyModule_AddObject(mod_hiredis, "Reader", (PyObject *)&hiredis_ReaderType);
}
