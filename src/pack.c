#include "pack.h"
#include <hiredis/hiredis.h>
#include <hiredis/sdsalloc.h>

PyObject *
pack_command(PyObject *cmd)
{
    assert(cmd);
    PyObject *result = NULL;

    if (cmd == NULL || !PyTuple_Check(cmd))
    {
        PyErr_SetString(PyExc_TypeError,
                        "The argument must be a tuple of str, int, float or bytes.");
        return NULL;
    }

    int tokens_number = PyTuple_Size(cmd);
    sds *tokens = s_malloc(sizeof(sds) * tokens_number);
    if (tokens == NULL)
    {
        return PyErr_NoMemory();
    }
    memset(tokens, 0, sizeof(sds) * tokens_number);

    size_t *lenghts = hi_malloc(sizeof(size_t) * tokens_number);
    Py_ssize_t len = 0;
    if (lenghts == NULL)
    {
        sds_free(tokens);
        return PyErr_NoMemory();
    }

    for (Py_ssize_t i = 0; i < PyTuple_Size(cmd); i++)
    {
        PyObject *item = PyTuple_GetItem(cmd, i);

        if (PyBytes_Check(item))
        {
            // Does it need to PyObject_CheckBuffer
            Py_buffer buffer;
            PyObject_GetBuffer(item, &buffer, PyBUF_SIMPLE);
            char *bytes = NULL;
            // check result?
            PyBytes_AsStringAndSize(item, &bytes, &len);
            tokens[i] = sdsempty();
            tokens[i] = sdscpylen(tokens[i], bytes, len);
            lenghts[i] = buffer.len;
            PyBuffer_Release(&buffer);
        }
        else if (PyUnicode_Check(item))
        {
            const char *bytes = PyUnicode_AsUTF8AndSize(item, &len);
            if (bytes == NULL)
            {
                // PyUnicode_AsUTF8AndSize sets an exception.
                goto cleanup;
            }

            tokens[i] = sdsnewlen(bytes, len);
            lenghts[i] = len;
        }
        // else if (PyByteArray_Check(item))
        // {
        //     //not tested. Is it supported
        //     tokens[i] = sdsnewlen(PyByteArray_AS_STRING(item), PyByteArray_GET_SIZE(item));
        //     lenghts[i] = PyByteArray_GET_SIZE(item);
        // }
        else if (PyMemoryView_Check(item))
        {
            Py_buffer *p_buf = PyMemoryView_GET_BUFFER(item);
            tokens[i] = sdsnewlen(p_buf->buf, p_buf->len);
            lenghts[i] = p_buf->len;
        }
        else
        {
            if (PyLong_CheckExact(item) || PyFloat_Check(item))
            {
                PyObject *repr = PyObject_Repr(item);
                const char *bytes = PyUnicode_AsUTF8AndSize(repr, &len);

                tokens[i] = sdsnewlen(bytes, len);
                lenghts[i] = len;
                Py_DECREF(repr);
            }
            else
            {
                PyErr_SetString(PyExc_TypeError,
                                "A tuple item must be str, int, float or bytes.");
                goto cleanup;
            }
        }
    }

    char *resp_bytes = NULL;

    len = redisFormatCommandArgv(&resp_bytes, tokens_number, tokens, lenghts);

    if (len == -1)
    {
        PyErr_SetString(PyExc_RuntimeError,
                        "Failed to serialize the command.");
        goto cleanup;
    }

    result = PyBytes_FromStringAndSize(resp_bytes, len);
    hi_free(resp_bytes);
cleanup:
    sdsfreesplitres(tokens, tokens_number);
    hi_free(lenghts);
    return result;
}

PyObject *
pack_bytes(PyObject *cmd)
{
    assert(cmd);
    if (cmd == NULL || !PyBytes_Check(cmd))
    {
        PyErr_SetString(PyExc_TypeError,
                        "The argument must be bytes.");
        return NULL;
    }

    char *obj_buf = NULL;
    Py_ssize_t obj_len = 0;

    if (PyBytes_AsStringAndSize(cmd, &obj_buf, &obj_len) == -1)
    {
        return NULL;
    }

    char *str_result = NULL;
    obj_len = redisFormatCommand(&str_result, obj_buf);

    PyObject *result = PyBytes_FromStringAndSize(str_result, obj_len);

    hi_free(str_result);

    return result;
}
