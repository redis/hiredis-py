#ifndef __HIREDIS_PY_H
#define __HIREDIS_PY_H

#include <Python.h>
#include <hiredis/read.h>

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

/* Per-object critical sections (PEP 703). Python.h defines these on CPython
 * 3.13+, where they only do something in free-threaded builds. Elsewhere (older
 * CPython, PyPy) the GIL already serializes access, so they are no-ops. */
#ifndef Py_BEGIN_CRITICAL_SECTION
#define Py_BEGIN_CRITICAL_SECTION(op) {
#define Py_END_CRITICAL_SECTION() }
#endif

#ifndef MOD_HIREDIS
#define MOD_HIREDIS "hiredis"
#endif

struct hiredis_ModuleState {
    PyObject *HiErr_Base;
    PyObject *HiErr_ProtocolError;
    PyObject *HiErr_ReplyError;
};

#define GET_STATE(__s) ((struct hiredis_ModuleState*)PyModule_GetState(__s))

/* Keep pointer around for other classes to access the module state. */
extern PyObject *mod_hiredis;
#define HIREDIS_STATE (GET_STATE(mod_hiredis))

PyMODINIT_FUNC PyInit_hiredis(void);

#endif
