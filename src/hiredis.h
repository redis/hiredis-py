#ifndef __HIREDIS_PY_H
#define __HIREDIS_PY_H

#include <Python.h>
#include <hiredis/hiredis.h>

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

PyMODINIT_FUNC inithiredis(void);

#endif
