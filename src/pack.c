#include "pack.h"
#include <hiredis/hiredis.h>

static 
sds add_to_buffer(sds curr_buff, char *cmd, uint len)
{
    assert(curr_buff);
    assert(sds);
    sds newbuf = sdscatlen(curr_buff, cmd, len);
    if (newbuf ==  NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    return newbuf;
}

PyObject*
pack_command(PyObject* cmd)
{
    char *buf = sdsempty();
    assert(cmd);
    char *obj_buf =  NULL;
    Py_ssize_t obj_len = 0;
    
    if (cmd == NULL || !PyTuple_Check(cmd)) {
        PyErr_SetString(PyExc_TypeError, 
                        "The argument must be a tuple of str, int, float or bytes.");
        return NULL;
    }

    if (buf == NULL) {
        return PyErr_NoMemory();
    }

    for (Py_ssize_t i = 0; i < PyTuple_Size(cmd); i++) {
        PyObject *item = PyTuple_GetItem(cmd, i);
        sds temp_ptr =  NULL; 
        if (PyBytes_Check(item)) {
            // check result?
            PyBytes_AsStringAndSize(item, &obj_buf, &obj_len);
            temp_ptr = add_to_buffer(buf, obj_buf, obj_len);
            if (temp_ptr == NULL) {
                return NULL;
            }

            buf = temp_ptr;

        } else if (PyUnicode_Check(item)) {
            
            obj_buf = PyUnicode_AsUTF8AndSize(item, &obj_len);
            if (obj_buf == NULL) {
                sds_free(buf);
                return NULL;
            }

            temp_ptr = add_to_buffer(buf, obj_buf, obj_len);
            if (temp_ptr == NULL) {
                return NULL;
            }

            buf = temp_ptr;
        } else if PyLong_Check(item) {
        } else {
            printf("not yet\n");
        }

        temp_ptr = add_to_buffer(buf, " ", 1);
        if (temp_ptr == NULL) {
            return NULL;
        }
        buf = temp_ptr;
    }

    obj_len = redisFormatCommand(&obj_buf, buf);

    PyObject *result = PyBytes_FromStringAndSize(obj_buf, obj_len);

    hi_free(obj_buf);
    //sds_free(buf);

    return result;
}


PyObject*
pack_bytes(PyObject* cmd)
{
    assert(cmd);
    if (cmd == NULL || !PyBytes_Check(cmd)) {
        PyErr_SetString(PyExc_TypeError, 
                        "The argument must be bytes.");
        return NULL;
    }

    char *obj_buf =  NULL;
    Py_ssize_t obj_len = 0;

    if(PyBytes_AsStringAndSize(cmd, &obj_buf, &obj_len) == -1) {
        return NULL;
    }

    char * str_result = NULL;
    obj_len = redisFormatCommand(&str_result, obj_buf);

    PyObject *result = PyBytes_FromStringAndSize(str_result, obj_len);

    hi_free(str_result);

    return result;
}
