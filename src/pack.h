#ifndef __PACK_H
#define __PACK_H

#include <Python.h>

extern PyObject* pack_command(PyObject* cmd);
extern PyObject* pack_bytes(PyObject* bytes);

#endif