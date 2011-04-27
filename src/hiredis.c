#include "hiredis.h"
#include "reader.h"

// TODO: move into state
PyObject *HiErr_Base;
PyObject *HiErr_ProtocolError;
PyObject *HiErr_ReplyError;

#if IS_PY3K
static struct PyModuleDef hiredis_ModuleDef = {
        PyModuleDef_HEAD_INIT,
        MOD_HIREDIS,
        NULL,
        0,    /* sizeof state */
        NULL, /* Module methods*/
        NULL,
        NULL, /* GC traverse */
        NULL, /* GC clear */
        NULL
};
#endif

#if IS_PY3K
PyMODINIT_FUNC PyInit_hiredis(void)
#else
PyMODINIT_FUNC inithiredis(void)
#endif

{
    PyObject *mod_hiredis;

    if (PyType_Ready(&hiredis_ReaderType) < 0) {
#if IS_PY3K
        return NULL;
#else
        return;
#endif
    }

    /* Setup custom exceptions */
    HiErr_Base = PyErr_NewException(MOD_HIREDIS ".HiredisError", PyExc_Exception, NULL);
    HiErr_ProtocolError = PyErr_NewException(MOD_HIREDIS ".ProtocolError", HiErr_Base, NULL);
    HiErr_ReplyError = PyErr_NewException(MOD_HIREDIS ".ReplyError", HiErr_Base, NULL);

#if IS_PY3K
    mod_hiredis = PyModule_Create(&hiredis_ModuleDef);
#else
    mod_hiredis = Py_InitModule(MOD_HIREDIS, NULL);
#endif

    PyModule_AddObject(mod_hiredis, "HiredisError", HiErr_Base);
    PyModule_AddObject(mod_hiredis, "ProtocolError", HiErr_ProtocolError);
    PyModule_AddObject(mod_hiredis, "ReplyError", HiErr_ReplyError);

    Py_INCREF(&hiredis_ReaderType);
    PyModule_AddObject(mod_hiredis, "Reader", (PyObject *)&hiredis_ReaderType);

#if IS_PY3K
    return mod_hiredis;
#endif
}
