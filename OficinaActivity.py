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

import gtk
import logging

from sugar.activity import activity
from sugar.graphics import style

from Area import Area
from toolbox import DrawToolbarBox


class OficinaActivity(activity.Activity):

    def __init__(self, handle):
        """Initialize the OficinaActivity object.

            @param  self
            @param  handle

        """
        activity.Activity.__init__(self, handle)
        self.max_participants = 1

        logging.debug('Starting Paint activity (Oficina)')

        self.fixed = gtk.Fixed()
        self.fixed.show()
        self.fixed.modify_bg(gtk.STATE_NORMAL,
                style.COLOR_WHITE.get_gdk_color())

        # These attributes are used in other classes, so they should be public
        self.area = Area(self)
        self.area.show()
        self.fixed.put(self.area, 0, 0)

        self.textview = gtk.TextView()
        self.fixed.put(self.textview, 0, 0)

        sw = gtk.ScrolledWindow()
        sw.show()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_canvas(sw)

        toolbar_box = DrawToolbarBox(self)

        toolbar_box.show_all()

        self.connect("key_press_event", self.key_press)

        # setup self.area only once

        def map_cp(widget):

            def size_allocate_cb(widget, allocation):
                self.fixed.disconnect(self._setup_handle)
                self.area.setup(allocation.width, allocation.height)
                self.center_area()

            self.canvas.add_with_viewport(self.fixed)
            # to remove the border, we need set the shadowtype
            # in the viewport child of the scrolledwindow
            self.canvas.get_children()[0].set_shadow_type(gtk.SHADOW_NONE)
            self.disconnect(self._setup_handle)
            self._setup_handle = self.fixed.connect('size_allocate',
                    size_allocate_cb)

        self._setup_handle = self.connect('map', map_cp)

    def key_press(self, widget, event):
        print event.keyval
        if event.keyval == 45:
            self.area.change_line_size(-1)
        if event.keyval == 43:
            self.area.change_line_size(1)

    def read_file(self, file_path):
        '''Read file from Sugar Journal.'''
        logging.debug('reading file %s, mimetype: %s, title: %s',
            file_path, self.metadata['mime_type'], self.metadata['title'])

        pixbuf = gtk.gdk.pixbuf_new_from_file(file_path)

        def size_allocate_cb(widget, allocation):
            self.fixed.disconnect(self._setup_handle)
            self.area.setup(pixbuf.get_width(), pixbuf.get_height())
            # The scrolled window is confused with a image of the same size
            # of the canvas when the toolbars popup and the scrolls
            # keep visible.
            if pixbuf.get_height() > allocation.height or \
                    pixbuf.get_width() > allocation.width:
                self.canvas.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            else:
                self.canvas.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

            self.area.loadImageFromJournal(pixbuf)
            self.center_area()

        self.canvas.add_with_viewport(self.fixed)
        # to remove the border, we need set the shadowtype
        # in the viewport child of the scrolledwindow
        self.canvas.get_children()[0].set_shadow_type(gtk.SHADOW_NONE)
        self.canvas.get_children()[0].set_border_width(0)

        self.disconnect(self._setup_handle)
        self._setup_handle = self.fixed.connect('size_allocate',
                size_allocate_cb)

        # disassociate with journal entry to avoid overwrite (SL #1771)
        if self.metadata['mime_type'] != "image/png":
            self._jobject.object_id = None
            last_point_posi = self.metadata['title'].rfind('.')
            if last_point_posi > -1:
                title = self.metadata['title'][0:last_point_posi] + '.png'
                self.metadata['title'] = title
            logging.error('title: %s', self.metadata['title'])

    def write_file(self, file_path):
        '''Save file on Sugar Journal. '''

        width, height = self.area.get_size_request()

        logging.debug('writting %s w=%s h=%s' % (file_path, width, height))
        if self.area.text_in_progress:
            self.area.d.text(self.area, event=None)

        self.area.getout()
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
            width, height)
        pixbuf.get_from_drawable(self.area.pixmap,
            gtk.gdk.colormap_get_system(), 0, 0, 0, 0, -1, -1)
        self.metadata['mime_type'] = 'image/png'
        pixbuf.save(file_path, 'png', {})

    def _get_area_displacement(self):
        """Return the point to use as top left corner in order to move
        the drawing area and center it on the canvas.

        """
        canvas_width = self.canvas.allocation.width
        canvas_height = self.canvas.allocation.height
        area_width, area_height = self.area.get_size_request()

        # Avoid 'x' and 'y' to be outside the screen
        x = max(0, (canvas_width - area_width) / 2)
        y = max(0, (canvas_height - area_height) / 2)
        return x, y

    def center_area(self):
        x, y = self._get_area_displacement()
        self.fixed.move(self.area, x, y)

    def move_textview(self, dx, dy):
        x, y = self._get_area_displacement()
        self.fixed.move(self.textview, x + dx, y + dy)
