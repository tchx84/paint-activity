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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('PangoCairo', '1.0')

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
import logging
import json

from sugar3.graphics import style

from Area import Area
from toolbox import DrawToolbarBox
import dialogs

from sugarapp.helpers import PrimaryMonitor
from sugarapp.widgets import SugarCompatibleActivity


class OficinaActivity(SugarCompatibleActivity):

    def __init__(self, handle):
        """Initialize the OficinaActivity object.

            @param  self
            @param  handle

        """
        SugarCompatibleActivity.__init__(self, handle)
        self.max_participants = 1

        logging.debug('Starting Paint activity (Oficina)')

        self._journal_images = []
        self.fixed = Gtk.Fixed()
        self._width = PrimaryMonitor.width()
        self._height = PrimaryMonitor.height()
        self.fixed.modify_bg(Gtk.StateType.NORMAL,
                             style.COLOR_WHITE.get_gdk_color())

        self.textview = Gtk.TextView()

        self.textview.set_events(Gdk.EventMask.POINTER_MOTION_MASK |
                                 Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                                 Gdk.EventMask.BUTTON_PRESS_MASK |
                                 Gdk.EventMask.BUTTON_RELEASE_MASK |
                                 Gdk.EventMask.BUTTON_MOTION_MASK |
                                 Gdk.EventMask.TOUCH_MASK)

        self.textview.connect('event', self.__textview_event_cb)
        self.textview.connect("motion_notify_event",
                              self.__textview_mouse_move_cb)
        self.textview.hide()  # will be shown when text tool is used

        self.area = Area(self)
        self.area.setup(self._width, self._height - style.GRID_CELL_SIZE)
        self.area.show()
        self.fixed.put(self.area, 0, 0)
        self.fixed.put(self.textview, 0, 0)
        self.fixed.show()

        self._sw = Gtk.ScrolledWindow()
        self._sw.set_kinetic_scrolling(False)
        self._sw.show()
        self._sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_canvas(self._sw)

        self.toolset_intialize_from_journal()

        toolbar_box = DrawToolbarBox(self)

        toolbar_box.show_all()

        self.connect("key_press_event", self.key_press)

        # setup self.area only once

        def map_cp(widget):

            def size_allocate_cb(widget, allocation):
                widget.disconnect(self._setup_handle)
                self.area.setup(allocation.width, allocation.height)
                self.center_area()

            self.canvas.add_with_viewport(self.fixed)
            # to remove the border, we need set the shadowtype
            # in the viewport child of the scrolledwindow
            self.canvas.get_children()[0].set_shadow_type(Gtk.ShadowType.NONE)
            self.disconnect(self._setup_handle)
            self._setup_handle = self._sw.connect('size_allocate',
                                                  size_allocate_cb)

        self._setup_handle = self.connect('map', map_cp)

        # Handle screen rotation
        Gdk.Screen.get_default().connect('size-changed', self._configure_cb)

    def _configure_cb(self, event):
        ''' Rotate the drawing after a screen rotation '''
        width = PrimaryMonitor.width()
        height = PrimaryMonitor.height()
        if (self._width > self._height) != (width > height):
            GLib.timeout_add(100, self.area.rotate_right, self.area)
        self._width = width
        self._height = height

    def key_press(self, widget, event):
        if event.keyval == 45:
            self.area.change_line_size(-1)
        if event.keyval == 43:
            self.area.change_line_size(1)

    def read_file(self, file_path):
        self.area.setup(self._width, self._height - style.GRID_CELL_SIZE)
        self.area.load_from_file(file_path)
        if 'images' in self.metadata:
            self._journal_images = json.loads(self.metadata['images'])

    def write_file(self, file_path):
        self.area.end_selection()
        self.area.drawing_canvas.write_to_png(file_path)
        self.metadata['images'] = json.dumps(dialogs.get_journal_images())

    def _get_area_displacement(self):
        """Return the point to use as top left corner in order to move
        the drawing area and center it on the canvas.

        """
        canvas_width = self.canvas.get_allocation().width
        canvas_height = self.canvas.get_allocation().height
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

    def toolset_intialize_from_journal(self):
        try:
            self.area.tool = json.loads(self.metadata['state'])
            logging.debug('self.area.tool %s', self.area.tool)
        except Exception as e:
            logging.debug("exception %s", e)

    def __textview_event_cb(self, widget, event):
        if event.type in (Gdk.EventType.TOUCH_BEGIN,
                          Gdk.EventType.TOUCH_CANCEL, Gdk.EventType.TOUCH_END,
                          Gdk.EventType.BUTTON_PRESS,
                          Gdk.EventType.BUTTON_RELEASE):
            x = int(event.get_coords()[1])
            y = int(event.get_coords()[2])
            if event.type in (Gdk.EventType.TOUCH_BEGIN,
                              Gdk.EventType.BUTTON_PRESS):
                self._initial_textview_touch_x = x
                self._initial_textview_touch_y = y
            elif event.type in (Gdk.EventType.TOUCH_END,
                                Gdk.EventType.BUTTON_RELEASE):
                # be sure the textview don't have a selection pending
                # and put the cursor at the end of the text
                text_buf = self.textview.get_buffer()
                end_text_iter = text_buf.get_end_iter()
                text_buf.select_range(end_text_iter, end_text_iter)
        return False

    def __textview_mouse_move_cb(self, widget, event):
        x = event.x
        y = event.y
        if event.get_state() & Gdk.ModifierType.BUTTON1_MASK:
            dx = x - self._initial_textview_touch_x
            dy = y - self._initial_textview_touch_y
            tv_alloc = self.textview.get_allocation()
            self.move_textview(tv_alloc.x + dx, tv_alloc.y + dy)
        return False
