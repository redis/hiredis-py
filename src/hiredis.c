#include "hiredis.h"
#include "reader.h"

#define MOD_HIREDIS "hiredis"

// TODO: move into state
PyObject *HiErr_Base;
PyObject *HiErr_ProtocolError;
PyObject *HiErr_ReplyError;

#if PY_MAJOR_VERSION >= 3
struct hiredis_state {
};

static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        MOD_HIREDIS,
        NULL,
        sizeof(struct hiredis_state),
        NULL, // methods
        NULL,
        NULL, // GC traverse
        NULL, // GC clear
        NULL
};
#endif

#if PY_MAJOR_VERSION >=3
PyMODINIT_FUNC PyInit_hiredis(void) {
#else
PyMODINIT_FUNC inithiredis(void) {
#endif
    PyObject *mod_hiredis;

    if (PyType_Ready(&hiredis_ReaderType) < 0) {
#if PY_MAJOR_VERSION >= 3
        return NULL;
#else
	return;
#endif
    }

    /* Setup custom exceptions */
    HiErr_Base = PyErr_NewException(MOD_HIREDIS ".HiredisError", PyExc_Exception, NULL);
    HiErr_ProtocolError = PyErr_NewException(MOD_HIREDIS ".ProtocolError", HiErr_Base, NULL);
    HiErr_ReplyError = PyErr_NewException(MOD_HIREDIS ".ReplyError", HiErr_Base, NULL);

#if PY_MAJOR_VERSION >= 3
    mod_hiredis = PyModule_Create(&moduledef);
#else
    mod_hiredis = Py_InitModule("hiredis", NULL);
#endif

    PyModule_AddObject(mod_hiredis, "HiredisError", HiErr_Base);
    PyModule_AddObject(mod_hiredis, "ProtocolError", HiErr_ProtocolError);
    PyModule_AddObject(mod_hiredis, "ReplyError", HiErr_ReplyError);
    

    Py_INCREF(&hiredis_ReaderType);
    PyModule_AddObject(mod_hiredis, "Reader", (PyObject *)&hiredis_ReaderType);
#if PY_MAJOR_VERSION >= 3
    return mod_hiredis;
#endif
}
