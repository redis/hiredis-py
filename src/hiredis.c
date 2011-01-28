#include "hiredis.h"
#include "reader.h"

#define MOD_HIREDIS "hiredis"
#define MOD_EXC MOD_HIREDIS ".exceptions"

PyObject *HiErr_Base;
PyObject *HiErr_ProtocolError;
PyObject *HiErr_ReplyError;

PyMODINIT_FUNC inithiredis(void) {
    PyObject *mod_hiredis;
    PyObject *mod_exc;

    if (PyType_Ready(&hiredis_ReaderType) < 0)
        return;

    /* Setup custom exceptions */
    HiErr_Base = PyErr_NewException(MOD_EXC ".HiredisError", PyExc_Exception, NULL);
    HiErr_ProtocolError = PyErr_NewException(MOD_EXC ".ProtocolError", HiErr_Base, NULL);
    HiErr_ReplyError = PyErr_NewException(MOD_EXC ".ReplyError", HiErr_Base, NULL);

    mod_exc = Py_InitModule(MOD_EXC, NULL);
    PyModule_AddObject(mod_exc, "HiredisError", HiErr_Base);
    PyModule_AddObject(mod_exc, "ProtocolError", HiErr_ProtocolError);
    PyModule_AddObject(mod_exc, "ReplyError", HiErr_ReplyError);

    mod_hiredis = Py_InitModule3("hiredis", NULL, NULL);
    PyModule_AddObject(mod_hiredis, "exceptions", mod_exc);

    Py_INCREF(&hiredis_ReaderType);
    PyModule_AddObject(mod_hiredis, "Reader", (PyObject *)&hiredis_ReaderType);
}
