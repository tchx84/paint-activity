/* -- THIS FILE IS GENERATED - DO NOT EDIT *//* -*- Mode: C; c-basic-offset: 4 -*- */

#include <Python.h>



#line 3 "fill.override"
#include <Python.h>               
#include <gtk/gtk.h>
#include "pygobject.h"
#include "eggfill.h"
#line 13 "fill.c"


/* ---------- types from other modules ---------- */
static PyTypeObject *_PyGdkDrawable_Type;
#define PyGdkDrawable_Type (*_PyGdkDrawable_Type)
static PyTypeObject *_PyGdkGC_Type;
#define PyGdkGC_Type (*_PyGdkGC_Type)


/* ---------- forward type declarations ---------- */

#line 25 "fill.c"



/* ----------- functions ----------- */

static PyObject *
_wrap_fill(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "drawable", "gc", "x", "y", "width", "height", "color", NULL };
    PyGObject *drawable, *gc;
    int x, y, width, height, color;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"O!O!iiiii:fill", kwlist, &PyGdkDrawable_Type, &drawable, &PyGdkGC_Type, &gc, &x, &y, &width, &height, &color))
        return NULL;
    
    fill(GDK_DRAWABLE(drawable->obj), GDK_GC(gc->obj), x, y, width, height, color);
    
    Py_INCREF(Py_None);
    return Py_None;
}

const PyMethodDef fill_functions[] = {
    { "fill", (PyCFunction)_wrap_fill, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { NULL, NULL, 0, NULL }
};

/* initialise stuff extension classes */
void
fill_register_classes(PyObject *d)
{
    PyObject *module;

    if ((module = PyImport_ImportModule("gtk.gdk")) != NULL) {
        _PyGdkDrawable_Type = (PyTypeObject *)PyObject_GetAttrString(module, "Drawable");
        if (_PyGdkDrawable_Type == NULL) {
            PyErr_SetString(PyExc_ImportError,
                "cannot import name Drawable from gtk.gdk");
            return ;
        }
        _PyGdkGC_Type = (PyTypeObject *)PyObject_GetAttrString(module, "GC");
        if (_PyGdkGC_Type == NULL) {
            PyErr_SetString(PyExc_ImportError,
                "cannot import name GC from gtk.gdk");
            return ;
        }
    } else {
        PyErr_SetString(PyExc_ImportError,
            "could not import gtk.gdk");
        return ;
    }


#line 79 "fill.c"
}
