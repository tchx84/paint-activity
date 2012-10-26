/*
Fill wrapper


Copyright 2007, NATE-LSI-EPUSP

Oficina is developed in Brazil at Escola Politécnica of 
Universidade de São Paulo. NATE is part of LSI (Integrable
Systems Laboratory) and stands for Learning, Work and Entertainment
Research Group. Visit our web page: 
www.lsi.usp.br/nate
Suggestions, bugs and doubts, please email oficina@lsi.usp.br

Oficina is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License 
as published by the Free Software Foundation version 2 of 
the License.

Oficina is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with Oficina; if not, write to the
Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, 
Boston, MA  02110-1301  USA.
The copy of the GNU General Public License is found in the 
COPYING file included in the source distribution.


Authors:

Joyce Alessandra Saul               (joycealess@gmail.com)
Andre Mossinato                     (andremossinato@gmail.com)
Nathalia Sautchuk Patrício          (nathalia.sautchuk@gmail.com)
Pedro Kayatt                        (pekayatt@gmail.com)
Rafael Barbolo Lopes                (barbolo@gmail.com)
Alexandre A. Gonçalves Martinazzo   (alexandremartinazzo@gmail.com)
Bruno Gola                          (brunogola@gmail.com)

Group Manager:
Irene Karaguilla Ficheman           (irene@lsi.usp.br)

Cientific Coordinator:
Roseli de Deus Lopes                (roseli@lsi.usp.br)

*/
#include <Python.h>
#include "eggfill.h"

static PyObject* fill(PyObject* self, PyObject* args)
{
    PyObject *mylist;
    unsigned int x, y, width, height, color;

    if (!PyArg_ParseTuple(args, "OIIIII", &mylist, &x, &y, &width, &height, &color))
        return NULL;

    /* from http://mail.python.org/pipermail/tutor/1999-November/000758.html */
    unsigned int *intarr, arrsize, index;
    PyObject *item;
    PyObject *pylist;

    /* how many elements are in the Python object */
    arrsize = PyObject_Length(mylist);
    /* create a dynamic C array of integers */
    intarr = (int *)malloc(sizeof(int)*arrsize);
    for (index = 0; index < arrsize; index++) {
        /* get the element from the list/tuple */
        item = PySequence_GetItem(mylist, index);
        /* assign to the C array */
        intarr[index] = PyInt_AsUnsignedLongMask(item);
    }

    /* now use intarr and arrsize in you extension */
    //printf("x %u y %u width %u height %u color %u", x, y, width, height, color);
    floodfill(intarr, x, y, width, height, color);

    pylist = PyTuple_New(arrsize);
    for (index = 0; index < arrsize; index++) {
           PyTuple_SetItem(pylist, index, PyInt_FromLong(intarr[index]));
    }

    return Py_BuildValue("O", pylist);
}


static PyMethodDef FillMethods[] = {
    {"fill", fill, METH_VARARGS, "do fill flood in a array with the image data"},
    {NULL, NULL, 0, NULL}
};
 
PyMODINIT_FUNC
init_fill(void)
{
    (void) Py_InitModule("_fill", FillMethods);
}
