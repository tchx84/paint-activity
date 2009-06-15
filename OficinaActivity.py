# -*- coding: utf-8 -*-
"""
OficinaActivity.py

Create Oficina Activity


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

Colaborators:
Bruno Gola                          (brunogola@gmail.com)

Group Manager:
Irene Karaguilla Ficheman           (irene@lsi.usp.br)

Cientific Coordinator:
Roseli de Deus Lopes                (roseli@lsi.usp.br)

UI Design (OLPC):
Eben Eliason                        (eben@laptop.org)

Project Coordinator (OLPC):
Manusheel Gupta                     (manu@laptop.org)

Project Advisor (OLPC):
Walter Bender                       (walter@laptop.org)

"""


import os
from gettext import gettext as _

import gtk

from sugar.activity import activity
from sugar.graphics import style

from toolbox import Toolbox
from Area import Area
import logging

class OficinaActivity(activity.Activity):

    def __init__(self, handle):
        """Initialize the OficinaActivity object.

            @param  self
            @param  handle

        """
        activity.Activity.__init__(self, handle)

        logging.debug('Starting Paint activity (Oficina)')

        self.fixed = gtk.Fixed()
        self.fixed.show()
        self.fixed.modify_bg(gtk.STATE_NORMAL,
                style.COLOR_WHITE.get_gdk_color())

        #self._bg = gtk.Image()
        #self._bg.set_from_file('./icons/bg.svg')
        #self.fixed.put(self._bg, 200, 100)
        #self._bg.show

        # These attributes are used in other classes, so they should be public
        self.area = Area(self)
        self.area.show()
        self.fixed.put(self.area, 0 , 0)

        self.textview = gtk.TextView()
        # If we use this, text viewer will have constant size, we don't want that
        #self.textview.set_size_request(100,100)
        self.fixed.put(self.textview, 0, 0)

        sw = gtk.ScrolledWindow()
        sw.show()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_canvas(sw)

        toolbox = Toolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        # setup self.area only once

        def map_cp(widget):
            def size_allocate_cb(widget, allocation):
                self.fixed.disconnect(self._setup_handle)
                self.area.setup(allocation.width, allocation.height)

            self.canvas.add_with_viewport(self.fixed)
            self.disconnect(self._setup_handle)
            self._setup_handle = self.fixed.connect('size_allocate',
                    size_allocate_cb)

        self._setup_handle = self.connect('map', map_cp)

    def read_file(self, file_path):
        '''Read file from Sugar Journal.'''

        logging.debug('reading file %s', file_path)

        pixbuf = gtk.gdk.pixbuf_new_from_file(file_path)

        def size_allocate_cb(widget, allocation):
            self.fixed.disconnect(self._setup_handle)
            self.area.setup(pixbuf.get_width(), pixbuf.get_height())
            self.area.loadImageFromJournal(pixbuf)

        self.canvas.add_with_viewport(self.fixed)
        self.disconnect(self._setup_handle)
        self._setup_handle = self.fixed.connect('size_allocate',
                size_allocate_cb)

    def write_file(self, file_path):
        '''Save file on Sugar Journal. '''

        width, height = self.area.get_size_request()

        logging.debug('writting file=%s w=%s h=%s' % (file_path, width, height))

        self.area.getout()
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, width, height)
        pixbuf.get_from_drawable(self.area.pixmap, gtk.gdk.colormap_get_system(), 0, 0, 0, 0, -1, -1)
        self.metadata['mime_type'] = 'image/png'
        pixbuf.save(file_path, 'png', {})
