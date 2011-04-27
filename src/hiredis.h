#ifndef __HIREDIS_PY_H
#define __HIREDIS_PY_H

#include <Python.h>
#include <hiredis/hiredis.h>

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K 1
#endif

#ifndef MOD_HIREDIS
#define MOD_HIREDIS "hiredis"
#endif

extern PyObject *HiErr_Base;
extern PyObject *HiErr_ProtocolError;
extern PyObject *HiErr_ReplyError;

#ifdef IS_PY3K
PyMODINIT_FUNC PyInit_hiredis(void);
#else
PyMODINIT_FUNC inithiredis(void);
#endif

#endif
