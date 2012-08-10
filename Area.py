# -*- coding: utf-8 -*-

"""
@namespace Area

    Tools and events manipulation


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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Pango

import logging
import os
import tempfile
import math
import cairo
import StringIO
import array

from Desenho import Desenho
from urlparse import urlparse
from sugar3.graphics.style import zoom

FALLBACK_FILL = True

#try:
#    from fill import fill
#    FALLBACK_FILL = False
#except:
#    logging.debug('No valid fill binaries. Using slower python code')
#    pass

##Tools and events manipulation are handle with this class.

TARGET_URI = 0
MAX_UNDO_STEPS = 12


class Area(Gtk.DrawingArea):

    __gsignals__ = {
        'undo': (GObject.SignalFlags.ACTION, None, ([])),
        'redo': (GObject.SignalFlags.ACTION, None, ([])),
        'action-saved': (GObject.SignalFlags.ACTION, None, ([])),
        'select': (GObject.SignalFlags.ACTION, None, ([])),
    }

    def __init__(self, activity):
        """ Initialize the object from class Area which is derived
            from Gtk.DrawingArea.

            @param  self -- the Area object (GtkDrawingArea)
            @param  activity -- the parent window

        """
        GObject.GObject.__init__(self)

        self.set_events(Gdk.EventMask.POINTER_MOTION_MASK |
                Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                Gdk.EventMask.BUTTON_PRESS_MASK |
                Gdk.EventMask.BUTTON_RELEASE_MASK |
                Gdk.EventMask.EXPOSURE_MASK |
                Gdk.EventMask.LEAVE_NOTIFY_MASK |
                Gdk.EventMask.ENTER_NOTIFY_MASK |
                Gdk.EventMask.KEY_PRESS_MASK)

        self.connect("draw", self.draw)
        self.connect("motion_notify_event", self.mousemove)
        self.connect("button_press_event", self.mousedown)
        self.connect("button_release_event", self.mouseup)
        self.connect("key_press_event", self.key_press)
        self.connect("leave_notify_event", self.mouseleave)
        self.connect("enter_notify_event", self.mouseenter)

        target = [Gtk.TargetEntry.new('text/uri-list', 0, TARGET_URI)]
        self.drag_dest_set(Gtk.DestDefaults.ALL, target,
                Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.connect('drag_data_received', self.drag_data_received)

        self.set_can_focus(True)
        self.grab_focus()
        # TODO gtk3
        # self.set_extension_events(Gdk.EXTENSION_EVENTS_CURSOR)

        ## Define which tool is been used.
        ## It is now described as a dictionnary,
        ## with the following keys:
        ## - 'name'          : a string
        ## - 'line size'     : a integer
        ## - 'stamp size'    : a integer
        ## - 'line shape'    : a string - 'circle' or 'square', for now
        ## - 'fill'          : a Boolean value
        ## - 'vertices'      : a integer
        ## All values migth be None, execept in 'name' key.
        self.tool = {
            'name': 'brush',
            'line size': 4,
            'stamp size': self._get_stamp_size(),
            'line shape': 'circle',
            'fill': True,
            'cairo_stroke_color': (0.0, 0.0, 0.0, 1.0),
            'cairo_fill_color': (0.0, 0.0, 0.0, 1.0),
            'alpha': 1.0,
            'vertices': 6.0,
            'font_description': 'Sans 12'}

        self.desenha = False
        self._selmove = False
        self.oldx = 0
        self.oldy = 0
        self.drawing_canvas = None
        self.textos = []
        self.text_in_progress = False
        self.activity = activity
        self.d = Desenho(self)
        self.last = []
        self.keep_aspect_ratio = False
        self.keep_shape_ratio = False

        self._font_description = None
        self.set_font_description(
                Pango.FontDescription(self.tool['font_description']))

        # selection properties
        self.clear_selection()
        self.pending_clean_selection_background = False

        # List of pixbuf for the Undo function:
        self._undo_list = []
        self._undo_index = None

        # variables to show the tool shape
        self.drawing = False
        self.x_cursor = 0
        self.y_cursor = 0

    def set_font_description(self, fd):
        self._font_description = fd
        self.activity.textview.modify_font(fd)
        self.tool['font_description'] = fd.to_string()

    def get_font_description(self):
        return Pango.FontDescription(self.tool['font_description'])

    def _get_stamp_size(self):
        """Set the stamp initial size, based on the display DPI."""
        return zoom(44)

    def load_from_file(self, file_path):
        self.drawing_canvas = cairo.ImageSurface.create_from_png(file_path)

    def setup(self, width, height):
        """Configure the Area object."""

        logging.debug('Area.setup: w=%s h=%s', width, height)

        self.set_size_request(width, height)

        ##It is the main canvas, who is display most of the time
        # if is not None was read from a file
        if self.drawing_canvas is None:
            self.drawing_canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                      width, height)
            self.drawing_ctx = cairo.Context(self.drawing_canvas)
            # paint background white
            self.drawing_ctx.rectangle(0, 0, width, height)
            self.drawing_ctx.set_source_rgb(1.0, 1.0, 1.0)
            self.drawing_ctx.fill()
        else:
            self.drawing_ctx = cairo.Context(self.drawing_canvas)

        ##This canvas is showed when we need show something and not draw it.
        self.temp_canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                  width, height)
        self.temp_ctx = cairo.Context(self.temp_canvas)
        self._init_temp_canvas()

        self.enable_undo()

        # Setting a initial tool
        self.set_tool(self.tool)

        return True

    def get_size(self):
        rect = self.get_allocation()
        return rect.width, rect.height

    def _init_temp_canvas(self, area=None):
        #logging.error('init_temp_canvas.')
        #self.drawing_canvas.flush()
        if area == None:
            width, height = self.get_size()
            self.temp_ctx.rectangle(0, 0, width, height)
        else:
            self.temp_ctx.rectangle(area.x, area.y, area.width, area.height)
        self.temp_ctx.set_source_surface(self.drawing_canvas)
        self.temp_ctx.paint()

    def display_selection_border(self, ctx):
        if not self.is_selected():
            return
        x, y, width, height = self.get_selection_bounds()

        ctx.save()
        ctx.set_line_width(1)
        ctx.set_source_rgba(1., 1., 1., 1.)
        ctx.rectangle(x, y, width, height)
        ctx.stroke_preserve()

        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_dash([5, 5], 0)
        ctx.set_source_rgba(0., 0., 0., 1.)
        ctx.stroke()
        ctx.restore()

    def configure_line(self, size):
        """Configure the new line's size.

            @param  self -- the Area object (GtkDrawingArea)
            @param  size -- the size of the new line

        """
        self.drawing_ctx.set_line_width(size)

    def draw(self, widget, context):
        """ This function define which canvas will be showed to the user.
            Show up the Area object (GtkDrawingArea).

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
            @param  event -- GdkEvent

        """
#        area = event.area

#        context = self.get_window().cairo_create()
#        context.rectangle(area.x, area.y, area.width, area.height)
#        context.clip()

        if self.desenha:
            #logging.error('Expose use temp canvas area %s', area)
            # Paint the canvas in the widget:
            context.set_source_surface(self.temp_canvas)
            context.paint()
        else:
            #logging.error('Expose use drawing canvas area %s', area)
            context.set_source_surface(self.drawing_canvas)
            context.paint()
            self.show_tool_shape(context)
        # TODO: gtk3 how get the area to avoid redrawing all ?
        self._init_temp_canvas()  # area)
        self.display_selection_border(context)

    def show_tool_shape(self, context):
        """
        Show the shape of the tool selected for pencil, brush,
        rainbow and eraser
        """
        if self.tool['name'] in ['pencil', 'eraser', 'brush', 'rainbow',
                                 'stamp']:
            if not self.drawing:
                context.set_source_rgba(*self.tool['cairo_stroke_color'])
                context.set_line_width(1)
                # draw stamp border in widget.window
                if self.tool['name'] == 'stamp':
                    wr, hr = self.stamp_dimentions
                    context.rectangle(self.x_cursor - wr / 2,
                            self.y_cursor - hr / 2, wr, hr)
                    context.stroke()

                # draw shape of the brush, square or circle
                elif self.tool['line shape'] == 'circle':
                    size = self.tool['line size']
                    context.arc(self.x_cursor,
                            self.y_cursor, size / 2, 0.,
                            2 * math.pi)
                    context.stroke()
                else:
                    size = self.tool['line size']
                    context.move_to(self.x_cursor - size / 2,
                            self.y_cursor - size / 2)
                    context.rectangle(self.x_cursor - size / 2,
                            self.y_cursor - size / 2, size, size)
                    context.stroke()
                self.last_x_cursor = self.x_cursor
                self.last_y_cursor = self.y_cursor

    def mousedown(self, widget, event):
        """Make the Area object (GtkDrawingArea) recognize
           that the mouse button has been pressed.

            @param self -- the Area object (GtkDrawingArea)
            @param widget -- the Area object (GtkDrawingArea)
            @param event -- GdkEvent

        """
        width, height = self.get_size()
        coords = int(event.x), int(event.y)

        # text
        design_mode = True
        if self.tool['name'] == 'text':
            self.d.text(widget, event)
            design_mode = False

        # This fixes a bug that made the text viewer get stuck in the canvas
        elif self.text_in_progress:
            design_mode = False
            try:
            # This works for a Gtk.Entry
                text = self.activity.textview.get_text()
            except AttributeError:
            # This works for a Gtk.TextView
                buf = self.activity.textview.get_buffer()
                start, end = buf.get_bounds()
                text = buf.get_text(start, end, True)

            if text is not None:
                self.d.text(widget, event)
            self.text_in_progress = False
            self.activity.textview.hide()

        self.oldx, self.oldy = coords

        # TODO: get_pointer is deprecated
# http://developer.gnome.org/gtk3/3.4/GtkWidget.html#gtk-widget-get-pointer
        _pointer, x, y, state = event.window.get_pointer()

        if self.tool['name'] == 'picker':
            self.pick_color(x, y)

        if state & Gdk.ModifierType.BUTTON1_MASK:
            #Handle with the left button click event.
            if self.tool['name'] == 'eraser':
                self.last = []
                self.d.eraser(widget, coords, self.last)
                self.last = coords
                self.drawing = True
            elif self.tool['name'] == 'brush':
                self.last = []
                self.d.brush(widget, coords, self.last)
                self.last = coords
                self.drawing = True
            elif self.tool['name'] == 'stamp':
                self.last = []
                self.d.stamp(widget, coords, self.last)
                self.last = coords
                self.drawing = True
            elif self.tool['name'] == 'rainbow':
                self.last = []
                self.d.rainbow(widget, coords, self.last)
                self.last = coords
                self.drawing = True
            elif self.tool['name'] == 'freeform':
                self.configure_line(self.tool['line size'])
                self.d.freeform(widget, coords, True,
                    self.tool['fill'], "motion")
            if self.tool['name'] == 'marquee-rectangular':
                if self.is_selected():
                    xi, yi, width, height = self.get_selection_bounds()
                    xf = xi + width
                    yf = yi + height
                    # verify is out of the selected area
                    if (coords[0] < xi) or (coords[0] > xf) or \
                        (coords[1] < yi) or (coords[1] > yf):
                        self.getout()
                        self._selmove = False
                        design_mode = False
                    else:
                        # if is inside the selected area move the selection
                        self.d.move_selection(widget, coords)
                        self._selmove = True
                else:
                    self._selmove = False

            if design_mode:
                self.desenha = True

    def calculate_damaged_area(self, points):
        min_x = points[0][0]
        min_y = points[0][1]
        max_x = 0
        max_y = 0
        for point in points:
            if point[0] < min_x:
                min_x = point[0]
            if point[0] > max_x:
                max_x = point[0]
            if point[1] < min_y:
                min_y = point[1]
            if point[1] > max_y:
                max_y = point[1]
        # add the tool size
        if self.tool['name'] == 'stamp':
            wr, hr = self.stamp_dimentions
            min_x = min_x - wr
            min_y = min_y - wr
            max_x = max_x + hr
            max_y = max_y + hr
        else:
            size = self.tool['line size']
            min_x = min_x - size
            min_y = min_y - size
            max_x = max_x + size
            max_y = max_y + size
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def mousemove(self, widget, event):
        """Make the Area object (GtkDrawingArea)
           recognize that the mouse is moving.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
            @param  event -- GdkEvent
        """
        x = event.x
        y = event.y
        state = event.get_state()

        self.x_cursor, self.y_cursor = int(x), int(y)

        coords = int(x), int(y)
        if self.tool['name'] in ['rectangle', 'ellipse', 'line']:
            if (state & Gdk.ModifierType.SHIFT_MASK) or \
                self.keep_shape_ratio:
                if self.tool['name'] in ['rectangle', 'ellipse']:
                    coords = self._keep_selection_ratio(coords)
                elif self.tool['name'] == 'line':
                    coords = self._keep_line_ratio(coords)

        if state & Gdk.ModifierType.BUTTON1_MASK:
            if self.tool['name'] == 'eraser':
                self.d.eraser(widget, coords, self.last)
                self.last = coords

            elif self.tool['name'] == 'brush':
                self.d.brush(widget, coords, self.last)
                self.last = coords

            elif self.tool['name'] == 'stamp':
                self.d.stamp(widget, coords, self.last,
                             self.tool['stamp size'])
                self.last = coords

            elif self.tool['name'] == 'rainbow':
                self.d.rainbow(widget, coords, self.last)
                self.last = coords

            if self.desenha:
                if self.tool['name'] == 'line':
                    self.d.line(widget, coords, True)

                elif self.tool['name'] == 'ellipse':
                    self.d.circle(widget, coords, True, self.tool['fill'])

                elif self.tool['name'] == 'rectangle':
                    self.d.square(widget, event, coords, True,
                        self.tool['fill'])

                elif self.tool['name'] == 'marquee-rectangular':
                    if self._selmove:
                        # is inside a selected area, move it
                        self.d.move_selection(widget, coords)
                    else:
                        # create a selected area
                        if (state & Gdk.ModifierType.CONTROL_MASK) or \
                            self.keep_aspect_ratio:
                            coords = self._keep_selection_ratio(coords)
                        self.d.selection(widget, coords)

                elif self.tool['name'] == 'freeform':
                    self.configure_line(self.tool['line size'])
                    self.d.freeform(widget, coords, True,
                        self.tool['fill'], "motion")

                elif self.tool['name'] == 'triangle':
                    self.d.triangle(widget, coords, True, self.tool['fill'])

                elif self.tool['name'] == 'trapezoid':
                    self.d.trapezoid(widget, coords, True, self.tool['fill'])

                elif self.tool['name'] == 'arrow':
                    self.d.arrow(widget, coords, True, self.tool['fill'])

                elif self.tool['name'] == 'parallelogram':
                    self.d.parallelogram(widget, coords, True,
                        self.tool['fill'])

                elif self.tool['name'] == 'star':
                    self.d.star(widget, coords, self.tool['vertices'],
                        True, self.tool['fill'])

                elif self.tool['name'] == 'polygon_regular':
                    self.d.polygon_regular(widget, coords,
                        self.tool['vertices'], True, self.tool['fill'])

                elif self.tool['name'] == 'heart':
                    self.d.heart(widget, coords, True, self.tool['fill'])
        else:
            if self.tool['name'] in ['brush', 'eraser', 'rainbow', 'pencil',
                                     'stamp']:
                # define area to update
                last_coords = (self.last_x_cursor, self.last_y_cursor)
                area = self.calculate_damaged_area([last_coords, coords])
                widget.queue_draw_area(*area)
            if self.tool['name'] == 'marquee-rectangular':
                sel_x, sel_y, sel_width, sel_height = \
                        self.get_selection_bounds()
                # show appropiate cursor
                if (coords[0] < sel_x) or (coords[0] > sel_x + sel_width) or \
                    (coords[1] < sel_y) or (coords[1] > sel_y + sel_height):
                    self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorType.CROSS))
                else:
                    self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorType.FLEUR))

            elif self.tool['name'] == 'freeform':
                self.desenha = True
                self.configure_line(self.tool['line size'])
                self.d.freeform(widget, coords, True,
                    self.tool['fill'], "moving")

        Gdk.event_request_motions(event)

    def mouseup(self, widget, event):
        """Make the Area object (GtkDrawingArea)
           recognize that the mouse was released.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
            @param  event -- GdkEvent
        """
        coords = int(event.x), int(event.y)
        if self.tool['name'] in ['rectangle', 'ellipse', 'line']:
            if (event.get_state() & Gdk.ModifierType.SHIFT_MASK) or \
                self.keep_shape_ratio:
                if self.tool['name'] in ['rectangle', 'ellipse']:
                    coords = self._keep_selection_ratio(coords)
                if self.tool['name'] == 'line':
                    coords = self._keep_line_ratio(coords)

        width, height = self.get_size()

        private_undo = False
        if self.desenha:
            if self.tool['name'] == 'line':
                self.d.line(widget, coords, False)

            elif self.tool['name'] == 'ellipse':
                self.d.circle(widget, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'rectangle':
                self.d.square(widget, event, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'marquee-rectangular':
                if self.is_selected() and not self._selmove:
                    self.create_selection_surface()
                    self.emit('select')
                    private_undo = True

            elif self.tool['name'] == 'freeform':
                self.d.freeform(widget, coords, False,
                    self.tool['fill'], 'release')
                private_undo = True

            elif self.tool['name'] == 'bucket':
                if FALLBACK_FILL:
                    self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorType.WATCH))
                    GObject.idle_add(self.flood_fill, coords[0], coords[1])
                else:
                    width, height = self.get_size()
                    self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorType.WATCH))
                    GObject.idle_add(self.fast_flood_fill, widget, coords[0],
                            coords[1], width, height)

            elif self.tool['name'] == 'triangle':
                self.d.triangle(widget, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'trapezoid':
                self.d.trapezoid(widget, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'arrow':
                self.d.arrow(widget, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'parallelogram':
                self.d.parallelogram(widget, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'star':
                self.d.star(widget, coords, self.tool['vertices'], False,
                    self.tool['fill'])

            elif self.tool['name'] == 'polygon_regular':
                self.d.polygon_regular(widget, coords, self.tool['vertices'],
                    False, self.tool['fill'])

            elif self.tool['name'] == 'heart':
                self.d.heart(widget, coords, False, self.tool['fill'])

        if self.tool['name'] in ['brush', 'eraser', 'rainbow', 'pencil',
                                 'stamp']:
            self.last = []
            self.d.finish_trace(self)
            self.drawing = False
        self.desenha = False
        if not private_undo and self.tool['name'] != 'bucket':
            # We have to avoid saving an undo state if the bucket tool
            # is selected because this undo state is called before the
            # GObject.idle_add (with the fill_flood function) finishes
            # and an unconsistent undo state is saved
            self.enable_undo()
        widget.queue_draw()
        self.d.clear_control_points()

    def fast_flood_fill(self, widget, x, y, width, height):
        fill(self.pixmap, self.gc, x, y, width,
                height, self.gc_line.foreground.pixel)
        widget.queue_draw()
        self.enable_undo()
        display = Gdk.Display.get_default()
        cursor = Gdk.Cursor.new_from_name(display, 'paint-bucket')
        self.get_window().set_cursor(cursor)

    def flood_fill(self, x, y):
        stroke_color = self.tool['cairo_stroke_color']
        r, g, b = stroke_color[0], stroke_color[1], stroke_color[2]

        # pack the color in a int as 0xAARRGGBB
        fill_color = 0xff000000 + \
                (int(r * 255 * 65536) + \
                int(g * 255 * 256) + \
                int(b * 255))
        logging.error('fill_color %d', fill_color)

        # load a array with the surface data
        for array_type in ['H', 'I', 'L']:
            pixels = array.array(array_type)
            if pixels.itemsize == 4:
                break
        else:
            raise AssertionError()
        pixels.fromstring(self.drawing_canvas.get_data())

        # process the pixels in the array
        width = self.drawing_canvas.get_width()
        height = self.drawing_canvas.get_height()

        def within(x, y):
            if x < 0 or x >= width:
                return False
            if y < 0 or y >= height:
                return False
            return True

        if not within(x, y):
            return
        edge = [(x, y)]

        old_color = pixels[x + y * width]
        if old_color == fill_color:
            logging.debug('Already filled')
            return

        pixels[x + y * width] = fill_color

        while len(edge) > 0:
            newedge = []
            for (x, y) in edge:
                for (s, t) in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if within(s, t) and \
                            pixels[s + t * width] == old_color:
                        pixels[s + t * width] = fill_color
                        newedge.append((s, t))
            edge = newedge

        # create a updated drawing_canvas
        self.drawing_canvas = cairo.ImageSurface.create_for_data(pixels,
                cairo.FORMAT_ARGB32, width, height)
        self.setup(width, height)

        self.queue_draw()
        self.enable_undo()

        display = Gdk.Display.get_default()
        cursor = Gdk.Cursor.new_from_name(display, 'paint-bucket')
        self.get_window().set_cursor(cursor)

    def pick_color(self, x, y):
        # create a new 1x1 cairo surface
        cairo_surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 1, 1)
        cairo_context = cairo.Context(cairo_surface)
        # translate xlib_surface so that target pixel is at 0, 0
        cairo_context.set_source_surface(self.drawing_canvas, -x, -y)
        cairo_context.rectangle(0, 0, 1, 1)
        cairo_context.set_operator(cairo.OPERATOR_SOURCE)
        cairo_context.fill()
        cairo_surface.flush()
        # Read the pixel
        pixels = cairo_surface.get_data()
        red = ord(pixels[2]) * 256
        green = ord(pixels[1]) * 256
        blue = ord(pixels[0]) * 256

        stroke_color = Gdk.Color(red, green, blue)

        # set in the area
        self.set_stroke_color(stroke_color)

        # update the stroke_color in the button
        self.activity.get_toolbar_box().brush_button.set_color(stroke_color)
        self.activity.get_toolbar_box().brush_button.stop_stamping()

    def mouseleave(self, widget, event):
        if self.tool['name'] in ['pencil', 'eraser', 'brush', 'rainbow',
                                 'stamp']:
            self.drawing = True
            size = self.tool['line size']
            widget.queue_draw_area(self.x_cursor - size, self.y_cursor - size,
                size * 2, size * 2)

    def mouseenter(self, widget, event):
        if self.tool['name'] in ['pencil', 'eraser', 'brush', 'rainbow',
                                 'stamp']:
            self.drawing = False
            size = self.tool['line size']
            widget.queue_draw_area(self.x_cursor - size, self.y_cursor - size,
                size * 2, size * 2)

    def setup_stamp(self):
        """Prepare for stamping from the selected area.

            @param  self -- the Area object (GtkDrawingArea)
        """
        if self.is_selected():
            # Change stamp, get it from selection:
            pixbuf_data = StringIO.StringIO()
            self.get_selection().write_to_png(pixbuf_data)
            pxb_loader = GdkPixbuf.PixbufLoader.new_with_type('png')
            pxb_loader.write(pixbuf_data.getvalue())

            self.pixbuf_stamp = pxb_loader.get_pixbuf()
            self.stamp_size = 0
            # Set white color as transparent:
            stamp_alpha = self.pixbuf_stamp.add_alpha(True, 255, 255, 255)
            self.pixbuf_stamp = stamp_alpha

        return self.resize_stamp(self.tool['stamp size'])

    def resize_stamp(self, stamp_size):
        """Change stamping pixbuffer from the given size.

            @param  self -- the Area object (GtkDrawingArea)
            @param  stamp_size -- the stamp will be inscripted in this size
        """

        # Area.setup_stamp needs to be called first:
        assert self.pixbuf_stamp

        self.stamp_size = stamp_size
        w = self.pixbuf_stamp.get_width()
        h = self.pixbuf_stamp.get_height()
        if w >= h:
            wr, hr = stamp_size, int(stamp_size * h * 1.0 / w)
        else:
            wr, hr = int(stamp_size * w * 1.0 / h), stamp_size
        self.stamp_dimentions = wr, hr
        self.resized_stamp = self.pixbuf_stamp.scale_simple(wr, hr,
                                 GdkPixbuf.InterpType.HYPER)

        # Remove selected area
        self.getout()

        return self.resized_stamp

    def undo(self):
        """Undo the last drawing change.

            @param  self -- the Area object (GtkDrawingArea)
        """
        logging.debug('Area.undo(self)')

        if self.is_selected():
            self.getout(undo=True)

        if self.text_in_progress:
            self.d.text(self, None)
            self.activity.textview.hide()

        if self._undo_index > 0:
            self._undo_index -= 1

        undo_surface = self._undo_list[self._undo_index]
        self.drawing_ctx.set_source_surface(undo_surface, 0, 0)
        self.drawing_ctx.set_operator(cairo.OPERATOR_SOURCE)
        self.drawing_ctx.paint()
        self.queue_draw()

        self.emit('undo')

    def redo(self):
        """Redo the last undo operation.

            @param  self -- the Area object (GtkDrawingArea)
        """
        logging.debug('Area.redo(self)')

        if self.is_selected():
            self.getout()

        if self._undo_index < len(self._undo_list) - 1:
            self._undo_index += 1

        undo_surface = self._undo_list[self._undo_index]
        self.drawing_ctx.set_source_surface(undo_surface, 0, 0)
        self.drawing_ctx.set_operator(cairo.OPERATOR_SOURCE)
        self.drawing_ctx.paint()
        self.queue_draw()

        self.emit('redo')

    def enable_undo(self, overrite=False):
        """Keep the last change in a list for Undo/Redo commands.

        """
        if len(self._undo_list) == 0:
            # first undo pix, start index:
            self._undo_index = 0
        elif len(self._undo_list) == MAX_UNDO_STEPS:
            # drop the oldest undo pix:
            self._undo_list.pop(0)

            # it could be at the middle of the list (clicked many
            # times undo) and after that draw anything, so we should
            # discart the next redos because they are obsolete now.
            self._undo_list = self._undo_list[:self._undo_index]
        else:
            self._undo_index += 1
            # Forget the redos after this one:
            self._undo_list = self._undo_list[:self._undo_index]

        # If a tool needs to do several drawings, uses overrite to
        # undo them in only one step.  In that case, the index is not
        # changed:
        if overrite and self._undo_index != 0:
            self._undo_index -= 1

        # copy the drawing surface in a new surface
        width = self.drawing_canvas.get_width()
        height = self.drawing_canvas.get_height()
        undo_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        undo_ctx = cairo.Context(undo_surface)
        undo_ctx.set_source_surface(self.drawing_canvas, 0, 0)
        undo_ctx.set_operator(cairo.OPERATOR_SOURCE)
        undo_ctx.paint()
        undo_surface.flush()

        self._undo_list.append(undo_surface)

        self.emit('action-saved')

    def copy(self):
        """ Copy Image.
            When the tool selection is working make the change
            the copy of selectioned area

            @param  self -- the Area object (GtkDrawingArea)
        """
        clipBoard = Gtk.Clipboard()
        if 'SUGAR_ACTIVITY_ROOT' in os.environ:
            temp_dir = os.path.join(os.environ.get('SUGAR_ACTIVITY_ROOT'),
                'instance')
        else:
            temp_dir = '/tmp'

        f, tempPath = tempfile.mkstemp(suffix='.png', dir=temp_dir)
        del f

        selection_surface = self.get_selection()
        if selection_surface is None:
            selection_surface = self.drawing_canvas
        logging.error('Saving file %s', tempPath)
        selection_surface.write_to_png(tempPath)
        os.chmod(tempPath, 0604)

        clipBoard.set_with_data([('text/uri-list', 0, 0)],
            self._copy_get_func, self._copy_clear_func, tempPath)

    def _copy_get_func(self, clipboard, selection_data, info, data):
        """  Determine type data to put in clipboard

            @param  self -- the Area object (GtkDrawingArea)
            @param  clipboard -- a Gtk.Clipboard object
            @param  selection_data -- data of selection
            @param  info -- the app assigned integer associated with a target
            @param  data -- user data (tempPath)
        """
        tempPath = data

        if selection_data.target == "text/uri-list":
            selection_data.set_uris(['file://' + tempPath])

    def _copy_clear_func(self, clipboard, data):
        """ Clear the clipboard

            @param  self -- the Area object (GtkDrawingArea)
            @param  clipboard -- a Gtk.Clipboard object
            @param  data -- user data (tempPath)
        """
        if (data != None):
            if (os.path.exists(data)):
                os.remove(data)
        data = None

    def drag_data_received(self, w, context, x, y, data, info, time):
        if data and data.format == 8:
            self.load_image(urlparse(data.data).path, self)
            context.finish(True, False, time)
        else:
            context.finish(False, False, time)

    def paste(self, widget):
        """ Paste image.
        Paste image that is in canvas

            @param  self -- the Area object (GtkDrawingArea)
        """
        width, height = self.get_size()

        tempPath = os.path.join("/tmp", "tempFile")
        tempPath = os.path.abspath(tempPath)

        clipBoard = Gtk.Clipboard()

        if clipBoard.wait_is_image_available():
            logging.debug('Area.paste(self): Wait is image available')
            self.getout(True)
            pixbuf_sel = clipBoard.wait_for_image()
            width, height = pixbuf_sel.get_width(), pixbuf_sel.get_height()

            self.temp_ctx.rectangle(0, 0, width, height)
            Gdk.cairo_set_source_pixbuf(self.temp_ctx, pixbuf_sel, 0, 0)
            self.temp_ctx.paint()
            self.set_selection_bounds(0, 0, width, height)
            self.desenha = True
            self.tool['name'] = 'marquee-rectangular'  # TODO: change toolbar?
            self.emit('select')
        elif clipBoard.wait_is_uris_available():
            logging.debug('Area.paste(self): is uris available')
            selection = clipBoard.wait_for_contents('text/uri-list')
            if selection != None:
                for uri in selection.get_uris():
                    self.load_image(urlparse(uri).path, self)
        else:
            self.load_image(tempPath, self)
            logging.debug('Area.paste(self): Load from clipboard fails')
            logging.debug('loading from tempPath')

        self.queue_draw()

    def set_fill_color(self, color):
        """Set fill color.

            @param  self -- the Area object (GtkDrawingArea)
            @param  color -- a Gdk.Color object

        """
        alpha = self.tool['alpha']
        red = color.red / 65535.0
        green = color.green / 65535.0
        blue = color.blue / 65535.0
        self.tool['cairo_fill_color'] = (red, green, blue, alpha)

    def set_stroke_color(self, color):
        """Set cairo_stroke_color.

            @param  self -- the Area object (GtkDrawingArea)
            @param  color -- a Gdk.Color object

        """
        alpha = self.tool['alpha']
        red = color.red / 65535.0
        green = color.green / 65535.0
        blue = color.blue / 65535.0
        self.tool['cairo_stroke_color'] = (red, green, blue, alpha)
        self.activity.textview.modify_text(Gtk.StateType.NORMAL, color)

    def set_alpha(self, alpha):
        """
        Set the alpha value used to draw
        @ param alpha -- float between 0.0 and 1.0
        """
        self.tool['alpha'] = alpha
        stroke_color = self.tool['cairo_stroke_color']
        self.tool['cairo_stroke_color'] = (stroke_color[0], stroke_color[1],
                stroke_color[2], alpha)

        fill_color = self.tool['cairo_fill_color']
        self.tool['cairo_fill_color'] = (fill_color[0], fill_color[1],
                fill_color[2], alpha)

    def grayscale(self, widget):
        """Apply grayscale effect.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)

        """

        def proc_grayscale(temp_pix):
            temp_pix.saturate_and_pixelate(temp_pix, 0, 0)
            return temp_pix

        self._do_process(widget, proc_grayscale)

    def invert_colors(self, widget):
        """Apply invert effect.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)

        """

        def internal_invert(self, old_cursor):
            # load a array with the surface data
            for array_type in ['H', 'I', 'L']:
                pixels = array.array(array_type)
                if pixels.itemsize == 4:
                    break
            else:
                raise AssertionError()
            pixels.fromstring(self.drawing_canvas.get_data())

            # process the pixels in the array
            new_array = array.array(pixels.typecode, len(pixels) * [0])
            for i in range(len(pixels)):
                new_array[i] = 0xffffffff - pixels[i] | 0xff000000

            # create a updated drawing_canvas
            width = self.drawing_canvas.get_width()
            height = self.drawing_canvas.get_height()
            self.drawing_canvas = cairo.ImageSurface.create_for_data(new_array,
                    cairo.FORMAT_ARGB32, width, height)
            self.setup(width, height)

            self.queue_draw()
            self.enable_undo()
            self.get_window().set_cursor(old_cursor)

        old_cursor = self.get_window().get_cursor()
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        GObject.idle_add(internal_invert, self, old_cursor)

    def mirror(self, widget, horizontal=True):
        """Apply mirror horizontal/vertical effect.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
            @param  horizontal -- If true sets flip as horizontal else vertical

        """

        def proc_mirror(temp_pix):
            return temp_pix.flip(self.horizontal)

        self.horizontal = horizontal
        self._do_process(widget, proc_mirror)

    def _do_process(self, widget, apply_process):
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        GObject.idle_add(self._do_process_internal, widget, apply_process)

    def _surface_to_pixbuf(self, surface):
        # copy from the surface to the pixbuf
        pixbuf_data = StringIO.StringIO()
        surface.write_to_png(pixbuf_data)
        pxb_loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        pxb_loader.write(pixbuf_data.getvalue())
        return pxb_loader.get_pixbuf()

    def _pixbuf_to_context(self, pixbuf, context, x=0, y=0):
        # copy from the pixbuf to the drawing context
        context.save()
        context.translate(x, y)
        Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
        context.paint()
        context.restore()

    def _do_process_internal(self, widget, apply_process):

        if self.is_selected():
            x, y, _width, _height = self.get_selection_bounds()
            surface = self.get_selection()
        else:
            x, y = 0, 0
            surface = self.drawing_canvas

        temp_pix = self._surface_to_pixbuf(surface)

        # process the pixbuf
        temp_pix = apply_process(temp_pix)

        self._pixbuf_to_context(temp_pix, self.drawing_ctx, x, y)
        self.create_selection_surface()

        del temp_pix

        self.queue_draw()
        if not self.is_selected():
            self.enable_undo()
        self.set_tool_cursor()

    def rotate_left(self, widget):
        """Rotate the image.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
        """
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        GObject.idle_add(self._rotate, widget, 90)

    def rotate_right(self, widget):
        """Rotate the image.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
        """
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        GObject.idle_add(self._rotate, widget, 270)

    def _rotate(self, widget, angle):
        """Rotate the image.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
        """
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))

        if self.is_selected():
            x, y, width, height = self.get_selection_bounds()
            surface = self.get_selection()
        else:
            x, y = 0, 0
            width, height = self.get_size()
            surface = self.drawing_canvas

        temp_pix = self._surface_to_pixbuf(surface)

        temp_pix = temp_pix.rotate_simple(angle)

        # copy from the pixbuf to the drawing context

        if self.is_selected():
            self.set_selection_bounds(x, y, height, width)
        else:
            # create a new canvas with permuted dimensions
            self.drawing_canvas = None
            self.setup(height, width)

        self._pixbuf_to_context(temp_pix, self.drawing_ctx, x, y)

        del temp_pix

        self.queue_draw()
        if not self.is_selected():
            self.enable_undo()
        self.set_tool_cursor()

    def can_undo(self):
        """
        Indicate if is there some action to undo
            @param  self -- the Area object (GtkDrawingArea)
        """
        return self._undo_index > 0

    def can_redo(self):
        """
        Indicate if is there some action to redo
            @param  self -- the Area object (GtkDrawingArea)
        """
        return self._undo_index < len(self._undo_list) - 1

    def is_selected(self):
        """
        Return True if there is some thing selected
        """
        return self.get_selection_bounds() != (0, 0, 0, 0)

    def clear_selection(self):
        self.set_selection_bounds(0, 0, 0, 0)
        self._selection_horizontal_scale = 1.0
        self._selection_vertical_scale = 1.0

    def set_selection_bounds(self, x, y, width, height):
        """
            Set selection bounds
            @param x, y, width, height - the rectangle to define the area
        """
        self._selection_bounds = (x, y, width, height)

    def set_selection_start(self, x, y):
        self._selection_bounds = (x, y, self._selection_bounds[2],
                self._selection_bounds[3])

    def get_selection_bounds(self):
        """
            @return x1, y1, width, height - the rectangle to define the area
        """
        x, y = self._selection_bounds[0], self._selection_bounds[1]
        width, height = self._selection_bounds[2], self._selection_bounds[3]
        width = width * self._selection_horizontal_scale
        height = height * self._selection_vertical_scale
        return (x, y, int(width), int(height))

    def create_selection_surface(self, clear_background=True):
        x, y, width, height = self.get_selection_bounds()
        logging.error('create_selection_surface %s', (x, y, width, height))
        self.selection_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                width, height)
        selection_ctx = cairo.Context(self.selection_surface)
        selection_ctx.translate(-x, -y)
        selection_ctx.set_source_surface(self.drawing_canvas)
        selection_ctx.paint()
        self.selection_resized_surface = None
        if clear_background:
            self.pending_clean_selection_background = True

    def resize_selection_surface(self, horizontal_scale, vertical_scale):
        x, y = self._selection_bounds[0], self._selection_bounds[1]
        new_width = int(self .selection_surface.get_width() * horizontal_scale)
        new_height = int(self.selection_surface.get_height() * vertical_scale)

        # create a surface with the selection scaled to the new size
        self.selection_resized_surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, new_width, new_height)
        temp_ctx = cairo.Context(self.selection_resized_surface)
        temp_ctx.scale(horizontal_scale, vertical_scale)
        temp_ctx.set_source_surface(self.selection_surface)
        temp_ctx.paint()

        # draw over temp canvas
        self.temp_ctx.save()
        self.temp_ctx.translate(x, y)
        self.temp_ctx.set_source_surface(self.selection_resized_surface)
        self.temp_ctx.rectangle(0, 0, new_width, new_height)
        self.temp_ctx.paint()
        self.temp_ctx.restore()

        self._selection_horizontal_scale = horizontal_scale
        self._selection_vertical_scale = vertical_scale

    def get_selection(self):
        if self.selection_resized_surface is not None:
            return self.selection_resized_surface
        if self.selection_surface is not None:
            return self.selection_surface
        else:
            return None

    def load_image(self, name, widget=None):
        """Load an image.

            @param  self -- Area instance
            @param  name -- string (image file path)
            @param  widget -- GtkDrawingArea

        """
        logging.debug('Area.load_image Loading file %s', name)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(name)
        width, height = (int)(pixbuf.get_width()), (int)(pixbuf.get_height())

        logging.debug('image size %d x %d', width, height)

        # load in the selection surface
        self.selection_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                width, height)
        selection_ctx = cairo.Context(self.selection_surface)
        self._pixbuf_to_context(pixbuf, selection_ctx)

        # show in the temp context too
        self.temp_ctx.save()
        self.temp_ctx.translate(0, 0)
        self.temp_ctx.set_source_surface(self.selection_surface)
        self.temp_ctx.paint()
        self.temp_ctx.restore()

        self.set_selection_bounds(0, 0, width, height)
        self.desenha = True
        self._selmove = True

        self.tool['name'] = 'marquee-rectangular'
        self.emit('select')

        self.queue_draw()

    def clear(self):
        """ Clear Canvas
            @param self -- Area instance
        """
        logging.debug('Area.clear')
        self.d.clear(self)

        # If something is selected, the action will be saved
        # after it is unselected
        if not self.is_selected():
            self.enable_undo()

    def set_tool(self, tool):
        '''
        Method to configure all tools.

        @param - tool: a dictionary with the tool keys
        '''
        # logging.debug('Area.set_tool %s', tool)
        self.tool = tool
        try:
            if self.tool['line size'] is not None:
                self.configure_line(self.tool['line size'])

#            if self.tool['fill color'] is not None:
#                self.set_fill_color(self.tool['fill color'])
#            else:
#                # use black
#                self.set_fill_color(self.black)

#            if self.tool['stroke color'] is not None:
#                self.set_stroke_color(self.tool['stroke color'])
#            else:
#                # use black
#                self.set_stroke_color(self.black)

        except AttributeError:
            pass

        self.set_tool_cursor()

    def set_tool_cursor(self):
        # Setting the cursor
        try:
            cursors = {'pencil': 'pencil',
                       'brush': 'paintbrush',
                       'eraser': 'eraser',
                       'bucket': 'paint-bucket'}

            display = Gdk.Display.get_default()
            if self.tool['name'] in cursors:
                name = cursors[self.tool['name']]
                cursor = Gdk.Cursor.new_from_name(display, name)
            elif self.tool['name'] == 'marquee-rectangular':
                cursor = Gdk.Cursor.new(Gdk.CursorType.CROSS)
            else:
                filename = os.path.join('images', self.tool['name'] + '.png')
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)

                # Decide which is the cursor hot spot offset:
                if self.tool['name'] == 'stamp':
                    hotspot_x, hotspot_y = 20, 38  # horizontal
                                                    # center and
                                                    # bottom
                elif self.tool['name'] == 'picker':
                    hotspot_x, hotspot_y = 1, 38  # bottom left
                                                   # corner
                else:
                    hotspot_x, hotspot_y = 0, 0

                cursor = Gdk.Cursor.new_from_pixbuf(display, pixbuf,
                        hotspot_x, hotspot_y)
        except GObject.GError:
            cursor = None
        self.get_window().set_cursor(cursor)

    def getout(self, undo=False):
        """
        Apply the selected area in the canvas.

        @param - undo: enable undo
        """

        try:
            # apply selection over canvas
            if self.is_selected():
                x, y, width, height = self.get_selection_bounds()
                selection_surface = self.get_selection()
                self.drawing_ctx.save()
                self.drawing_ctx.translate(x, y)
                self.drawing_ctx.set_source_surface(selection_surface)
                self.drawing_ctx.rectangle(0, 0, width, height)
                self.drawing_ctx.paint()
                self.drawing_ctx.restore()
                self.desenha = False

                self.clear_selection()
                if undo:
                    self.enable_undo()

        except NameError, message:
            logging.debug(message)
        except Exception, message:
            logging.debug('Unexpected error: %s', message)

    def key_press(self, widget, event):
        if event.keyval == Gdk.KEY_BackSpace:
            if self.is_selected():
                # Remove selection
                # TODO

                if self.tool['name'] == 'marquee-rectangular':
                    self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorType.CROSS))
                widget.queue_draw()
                self.enable_undo()
        elif event.keyval == Gdk.KEY_a and Gdk.ModifierType.CONTROL_MASK:
            if self.is_selected():
                self.getout()
            width, height = self.get_size()
            if self.tool['name'] == 'marquee-rectangular':
                self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorTypeFLEUR))
            self.set_selection_bounds(0, 0, width - 1, height - 1)
            self.emit('select')
            widget.queue_draw()
        elif event.keyval == Gdk.KEY_d and Gdk.ModifierType.CONTROL_MASK:
            if self.is_selected():
                self.getout(True)
                if self.tool['name'] == 'marquee-rectangular':
                    self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorType.CROSS))
                widget.queue_draw()
        elif event.keyval == Gdk.KEY_Return:
            self.getout(True)
            if self.tool['name'] == 'marquee-rectangular':
                self.get_window().set_cursor(Gdk.Cursor.new(
                                                    Gdk.CursorType.CROSS))
            widget.queue_draw()

    def change_line_size(self, delta):
        # Used from OficinaActivity
        if self.tool['name'] in ['pencil', 'eraser', 'brush', 'rainbow']:
            size = self.tool['line size'] + delta
            if size < 1:
                size = 1
            self.tool['line size'] = size
            self.configure_line(size)
            # TODO: clip
            self.queue_draw()
        if self.tool['name'] == 'stamp':
            self.resize_stamp(self.stamp_size + delta)
            # TODO: clip
            self.queue_draw()

    def _keep_selection_ratio(self, coords):

        def sign(x):
            return x and x / abs(x) or 0

        dx = int(coords[0]) - self.oldx
        dy = int(coords[1]) - self.oldy
        size = max(abs(dx), abs(dy))

        return (self.oldx + sign(dx) * size,
                self.oldy + sign(dy) * size)

    def _keep_line_ratio(self, coords):

        def sign(x):
            return x and x / abs(x) or 0

        dx = int(coords[0]) - self.oldx
        dy = int(coords[1]) - self.oldy
        size = max(abs(dx), abs(dy))

        if abs(dx) > 0.5 * size and abs(dy) > 0.5 * size:
            return (self.oldx + sign(dx) * size,
                   self.oldy + sign(dy) * size)
        elif abs(dx) < 0.5 * size and abs(dy) > 0.5 * size:
            return (self.oldx,
                   self.oldy + sign(dy) * size)
        elif abs(dx) > 0.5 * size and abs(dy) < 0.5 * size:
            return (self.oldx + sign(dx) * size,
                   self.oldy)
