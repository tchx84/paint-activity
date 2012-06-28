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

import gtk
import gobject
import logging
import os
import tempfile
import math
import pango
import cairo

from Desenho import Desenho
from urlparse import urlparse
from sugar.graphics.style import zoom

FALLBACK_FILL = True
try:
    from fill import fill
    FALLBACK_FILL = False
except:
    logging.debug('No valid fill binaries. Using slower python code')
    pass


##Tools and events manipulation are handle with this class.

TARGET_URI = 0
MAX_UNDO_STEPS = 12


class Area(gtk.DrawingArea):

    __gsignals__ = {
        'undo': (gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ([])),
        'redo': (gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ([])),
        'action-saved': (gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ([])),
        'select': (gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ([])),
    }

    def __init__(self, activity):
        """ Initialize the object from class Area which is derived
            from gtk.DrawingArea.

            @param  self -- the Area object (GtkDrawingArea)
            @param  activity -- the parent window

        """
        gtk.DrawingArea.__init__(self)

        self.set_events(gtk.gdk.POINTER_MOTION_MASK |
                gtk.gdk.POINTER_MOTION_HINT_MASK |
                gtk.gdk.BUTTON_PRESS_MASK |
                gtk.gdk.BUTTON_RELEASE_MASK |
                gtk.gdk.EXPOSURE_MASK |
                gtk.gdk.LEAVE_NOTIFY_MASK |
                gtk.gdk.ENTER_NOTIFY_MASK |
                gtk.gdk.KEY_PRESS_MASK)

        self.connect("expose_event", self.expose)
        self.connect("motion_notify_event", self.mousemove)
        self.connect("button_press_event", self.mousedown)
        self.connect("button_release_event", self.mouseup)
        self.connect("key_press_event", self.key_press)
        self.connect("leave_notify_event", self.mouseleave)
        self.connect("enter_notify_event", self.mouseenter)

        target = [('text/uri-list', 0, TARGET_URI)]
        self.drag_dest_set(gtk.DEST_DEFAULT_ALL, target,
                gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self.connect('drag_data_received', self.drag_data_received)

        self.set_can_focus(True)
        self.grab_focus()

        self.set_extension_events(gtk.gdk.EXTENSION_EVENTS_CURSOR)
        ## Define which tool is been used.
        ## It is now described as a dictionnary,
        ## with the following keys:
        ## - 'name'          : a string
        ## - 'line size'     : a integer
        ## - 'stamp size'    : a integer
        ## - 'fill color'    : a gtk.gdk.Color object
        ## - 'stroke color'  : a gtk.gdk.Color object
        ## - 'line shape'    : a string - 'circle' or 'square', for now
        ## - 'fill'          : a Boolean value
        ## - 'vertices'      : a integer
        ## All values migth be None, execept in 'name' key.
        self.tool = {
            'name': 'brush',
            'line size': 4,
            'stamp size': self._get_stamp_size(),
            'fill color': None,
            'stroke color': None,
            'line shape': 'circle',
            'fill': True,
            'cairo_stroke_color': (0.0, 0.0, 0.0, 0.3),
            'cairo_fill_color': (0.0, 0.0, 0.0, 0.3),
            'vertices': 6.0}

        self.desenha = False
        self.selmove = False
        self.sel_get_out = False
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

        self.font_description = pango.FontDescription()
        self.font_description.set_family('Sans')
        self.font_description.set_size(12)

        self.set_selection_bounds(0, 0, 0, 0)

        # List of pixmaps for the Undo function:
        self._undo_list = []
        self._undo_index = None

        # variables to show the tool shape
        self.drawing = False
        self.x_cursor = 0
        self.y_cursor = 0

    def _get_stamp_size(self):
        """Set the stamp initial size, based on the display DPI."""
        return zoom(44)

    def load_from_file(self, file_path):
        self.drawing_canvas = cairo.ImageSurface.create_from_png(file_path)

    def setup(self, width, height):
        """Configure the Area object."""

        logging.debug('Area.setup: w=%s h=%s' % (width, height))

        win = self.window
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
        self._init_temp_canvas(width, height)

        self.enableUndo(self, size=(width, height))

        # Setting a initial tool
        self.set_tool(self.tool)

        return True

    def _init_temp_canvas(self, width, height):
        self.temp_canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                  width, height)
        self.temp_ctx = cairo.Context(self.temp_canvas)
        self.temp_ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        self.temp_ctx.rectangle(0, 0, width, height)
        self.temp_ctx.fill()
        self.temp_ctx.set_source_surface(self.drawing_canvas)
        self.temp_ctx.paint()

    def display_selection_border(self, ctx):
        x, y, x2, y2 = self.get_selection_bounds()
        if (x, y, x2, y2) == (0, 0, 0, 0):
            return

        ctx.save()
        ctx.set_line_width(1)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_dash([5, 5], 0)
        ctx.set_source_rgba(0., 0., 0., 1.)
        ctx.rectangle(x, y, x2, y2)
        ctx.stroke()
        ctx.restore()

    def configure_line(self, size):
        """Configure the new line's size.

            @param  self -- the Area object (GtkDrawingArea)
            @param  size -- the size of the new line

        """
        self.drawing_ctx.set_line_width(size)
        self.drawing_ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.drawing_ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    def expose(self, widget, event):
        """ This function define which canvas will be showed to the user.
            Show up the Area object (GtkDrawingArea).

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
            @param  event -- GdkEvent

        """
        area = event.area
        #logging.error('expose area %s', area)
        width, height = self.window.get_size()

        context = self.window.cairo_create()

        if self.desenha or self.selmove:
            # Paint the canvas in the widget:
            # TODO: clipping
            context.set_source_surface(self.temp_canvas)
            context.paint()
        else:
            # TODO: clipping
            context.set_source_surface(self.drawing_canvas)
            context.paint()
            self.show_tool_shape(context)
        self._init_temp_canvas(width, height)
        self.display_selection_border(context)

    def show_tool_shape(self, context):
        """
        Show the shape of the tool selected for pencil, brush,
        rainbow and eraser
        """
        if self.tool['name'] in ['pencil', 'eraser', 'brush', 'rainbow',
                                 'stamp']:
            context.set_source_rgba(*self.tool['cairo_stroke_color'])
            context.set_line_width(1)
            if not self.drawing:
                # draw stamp border in widget.window
                if self.tool['name'] == 'stamp':
                    wr, hr = self.stamp_dimentions
                    context.rectangle(self.x_cursor - wr / 2,
                            self.y_cursor - hr / 2, wr, hr)
                    # TODO: stroke style
                    context.stroke()

                # draw shape of the brush, square or circle
                elif self.tool['line shape'] == 'circle':
                    size = self.tool['line size']
                    context.move_to(self.x_cursor,
                            self.y_cursor)
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

    def mousedown(self, widget, event):
        """Make the Area object (GtkDrawingArea) recognize
           that the mouse button has been pressed.

            @param self -- the Area object (GtkDrawingArea)
            @param widget -- the Area object (GtkDrawingArea)
            @param event -- GdkEvent

        """
        width, height = self.window.get_size()
        coords = int(event.x), int(event.y)

        # text
        if self.tool['name'] == 'text':
            self.d.text(widget, event)

        # This fixes a bug that made the text viewer get stuck in the canvas
        elif self.text_in_progress:
            try:
            # This works for a gtk.Entry
                text = self.activity.textview.get_text()
            except AttributeError:
            # This works for a gtk.TextView
                buf = self.activity.textview.get_buffer()
                start, end = buf.get_bounds()
                text = buf.get_text(start, end)

            if text is not None:
                self.d.text(widget, event)
            self.text_in_progress = False
            self.activity.textview.hide()

        self.oldx, self.oldy = coords

        x, y, state = event.window.get_pointer()

        if self.tool['name'] == 'picker':
            self.pick_color(x, y)

        if state & gtk.gdk.BUTTON3_MASK:
            #Handle with the right button click event.
            if self.tool['name'] == 'marquee-rectangular':
                self.sel_get_out = True
        elif state & gtk.gdk.BUTTON1_MASK:
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
                logging.error('mousedown')
                self.configure_line(self.tool['line size'])
                self.d.freeform(widget, coords, True,
                    self.tool['fill'], "motion")
            if self.selmove:
                #get out of the func selection
                if self.tool['name'] != 'marquee-rectangular':
                    self.getout()
                    self.selmove = False
                else:
                    size = self.pixmap_sel.get_size()
                    xi = self.orig_x
                    yi = self.orig_y
                    xf = xi + size[0]
                    yf = yi + size[1]
                    if (coords[0] < xi) or (coords[0] > xf) or \
                        (coords[1] < yi) or (coords[1] > yf):
                        self.sel_get_out = True
            else:
                self.temp_ctx.set_source_surface(self.drawing_canvas, 0, 0)
                self.temp_ctx.rectangle(0, 0, width, height)
                self.temp_ctx.paint()

            self.desenha = True
        widget.queue_draw()

    def mousemove(self, widget, event):
        """Make the Area object (GtkDrawingArea)
           recognize that the mouse is moving.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
            @param  event -- GdkEvent
        """
        x = event.x
        y = event.y
        state = event.state

        self.x_cursor, self.y_cursor = int(x), int(y)

        coords = int(x), int(y)
        if self.tool['name'] in ['rectangle', 'ellipse', 'line']:
            if (state & gtk.gdk.SHIFT_MASK) or \
                self.keep_shape_ratio:
                if self.tool['name'] in ['rectangle', 'ellipse']:
                    coords = self._keep_selection_ratio(coords)
                elif self.tool['name'] == 'line':
                    coords = self._keep_line_ratio(coords)

        if state & gtk.gdk.BUTTON1_MASK:
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

                elif self.tool['name'] == 'marquee-rectangular' and \
                    not self.selmove:
                    if (state & gtk.gdk.CONTROL_MASK) or \
                        self.keep_aspect_ratio:
                        coords = self._keep_selection_ratio(coords)
                    self.d.selection(widget, coords)
                # selected
                elif self.tool['name'] == 'marquee-rectangular' and \
                    self.selmove:
                    if not self.sel_get_out:
                        self.d.moveSelection(widget, coords)

                elif self.tool['name'] == 'freeform':
                    logging.error('mousemove')
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
                widget.queue_draw()
            if self.tool['name'] == 'marquee-rectangular' and self.selmove:
                sel_x, sel_y, sel_width, sel_height = \
                        self.get_selection_bounds()

                if (coords[0] < sel_x) or (coords[0] > sel_x + sel_width) or \
                    (coords[1] < sel_y) or (coords[1] > sel_y + sel_height):
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSS))
                else:
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))

            elif self.tool['name'] == 'freeform' and not self.selmove:
                self.desenha = True
                self.configure_line(self.tool['line size'])
                self.d.freeform(widget, coords, True,
                    self.tool['fill'], "moving")

        gtk.gdk.event_request_motions(event)

    def mouseup(self, widget, event):
        """Make the Area object (GtkDrawingArea)
           recognize that the mouse was released.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
            @param  event -- GdkEvent
        """
        coords = int(event.x), int(event.y)
        if self.tool['name'] in ['rectangle', 'ellipse', 'line']:
            if (event.state & gtk.gdk.SHIFT_MASK) or \
                self.keep_shape_ratio:
                if self.tool['name'] in ['rectangle', 'ellipse']:
                    coords = self._keep_selection_ratio(coords)
                if self.tool['name'] == 'line':
                    coords = self._keep_line_ratio(coords)

        width, height = self.window.get_size()

        private_undo = False
        if self.desenha or self.sel_get_out:
            if self.tool['name'] == 'line':
                self.d.line(widget, coords, False)

            elif self.tool['name'] == 'ellipse':
                self.d.circle(widget, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'rectangle':
                self.d.square(widget, event, coords, False, self.tool['fill'])

            elif self.tool['name'] == 'marquee-rectangular':
                if self.selmove == False:
                    if (event.state & gtk.gdk.CONTROL_MASK) or \
                        self.keep_aspect_ratio:
                        coords = self._keep_selection_ratio(coords)
                    self.d.selection(widget, coords)
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
                    self.selmove = True
                    self.sel_get_out = False
                    self.emit('select')
                elif self.sel_get_out:  # get out of the func selection
                    self.getout()
                    try:
                        del(self.d.pixbuf_resize)
                    except:
                        pass
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSS))
                    widget.queue_draw()
                    self.enableUndo(widget)
                elif self.selmove:
                    self.orig_x = self.orig_x + coords[0] - self.oldx
                    self.orig_y = self.orig_y + coords[1] - self.oldy
                self.emit('select')
                private_undo = True

            elif self.tool['name'] == 'freeform':
                self.d.freeform(widget, coords, False,
                    self.tool['fill'], 'release')
                private_undo = True

            elif self.tool['name'] == 'bucket':
                if FALLBACK_FILL:
                    if self.tool['stroke color'] is not None:
                        stroke_color = self.tool['stroke color']
                        color_r = int(stroke_color.red_float * 65535)
                        color_g = int(stroke_color.green_float * 65535)
                        color_b = int(stroke_color.blue_float * 65535)
                    else:
                        color_r, color_g, color_b = 0, 0, 0
                    cmap = self.pixmap.get_colormap()
                    fill_color = \
                            cmap.alloc_color(color_r, color_g, color_b).pixel
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
                    gobject.idle_add(self.flood_fill, coords[0], coords[1],
                            fill_color)
                else:
                    width, height = self.window.get_size()
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
                    gobject.idle_add(self.fast_flood_fill, widget, coords[0],
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
            widget.queue_draw()
            self.drawing = False
        self.desenha = False
        if not private_undo and self.tool['name'] != 'bucket':
            # We have to avoid saving an undo state if the bucket tool
            # is selected because this undo state is called before the
            # gobject.idle_add (with the fill_flood function) finishes
            # and an unconsistent undo state is saved
            self.enableUndo(widget)

    def fast_flood_fill(self, widget, x, y, width, height):
        fill(self.pixmap, self.gc, x, y, width,
                height, self.gc_line.foreground.pixel)
        widget.queue_draw()
        self.enableUndo(widget)
        display = gtk.gdk.display_get_default()
        cursor = gtk.gdk.cursor_new_from_name(display, 'paint-bucket')
        self.window.set_cursor(cursor)

    def flood_fill(self, x, y, fill_color):
        width, height = self.window.get_size()

        gdk_image = self.pixmap.get_image(0, 0, width, height)

        def within(x, y):
            if x < 0 or x >= width:
                return False
            if y < 0 or y >= height:
                return False
            return True

        if not within(x, y):
            return
        edge = [(x, y)]

        old_color = gdk_image.get_pixel(x, y)
        if old_color == fill_color:
            logging.debug('Already filled')
            return

        gdk_image.put_pixel(x, y, fill_color)

        while len(edge) > 0:
            newedge = []
            for (x, y) in edge:
                for (s, t) in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if within(s, t) and \
                            gdk_image.get_pixel(s, t) == old_color:
                        gdk_image.put_pixel(s, t, fill_color)
                        newedge.append((s, t))
            edge = newedge

        self.pixmap.draw_image(self.gc, gdk_image, 0, 0, 0, 0, width, height)
        self.queue_draw()
        self.enableUndo(self)

        display = gtk.gdk.display_get_default()
        cursor = gtk.gdk.cursor_new_from_name(display, 'paint-bucket')
        self.window.set_cursor(cursor)

    def pick_color(self, x, y):
        gdk_image = self.pixmap.get_image(x, y, 1, 1)
        pixel = gdk_image.get_pixel(0, 0)
        cmap = gdk_image.get_colormap()
        gdk_color = cmap.query_color(pixel)

        # set in the area
        pixmap_cmap = self.pixmap.get_colormap()
        stroke_color = pixmap_cmap.alloc_color(gdk_color)
        self.tool['stroke color'] = stroke_color
        self.set_stroke_color(self.tool['stroke color'])

        # update the stroke color button
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
            width, height = self.pixmap_sel.get_size()
            self.pixbuf_stamp = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False,
                8, width, height)
            self.pixbuf_stamp.get_from_drawable(self.pixmap_sel,
                gtk.gdk.colormap_get_system(), 0, 0, 0, 0, width, height)
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
                                 gtk.gdk.INTERP_HYPER)

        # Remove selected area
        self.getout()

        return self.resized_stamp

    def undo(self):
        """Undo the last drawing change.

            @param  self -- the Area object (GtkDrawingArea)
        """
        logging.debug('Area.undo(self)')
        width, height = self.window.get_size()

        if self.selmove:
            self.getout(undo=True)

        if self.text_in_progress:
            self.d.text(self, None)
            self.activity.textview.hide()

        if self._undo_index > 0:
            self._undo_index -= 1

        undo_pix = self._undo_list[self._undo_index]
        self.pixmap.draw_drawable(self.gc, undo_pix, 0, 0, 0, 0, -1, -1)
        self.queue_draw()

        self.emit('undo')

    def redo(self):
        """Redo the last undo operation.

            @param  self -- the Area object (GtkDrawingArea)
        """
        logging.debug('Area.redo(self)')
        width, height = self.window.get_size()

        if self.selmove:
            self.getout()

        if self._undo_index < len(self._undo_list) - 1:
            self._undo_index += 1

        undo_pix = self._undo_list[self._undo_index]
        self.pixmap.draw_drawable(self.gc, undo_pix, 0, 0, 0, 0, -1, -1)
        self.queue_draw()

        self.emit('redo')

    def enableUndo(self, widget, size=None, overrite=False):
        """Keep the last change in a list for Undo/Redo commands.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)

        """
        #TODO
        return

        #logging.debug('Area.enableUndo(self,widget)')

        width, height = self.window.get_size()
        # We need to pass explicitly the size on set up, because the
        # window size is not allocated yet.
        if size is not None:
            width, height = size

        if len(self._undo_list) == 0:
            # first undo pix, start index:
            self._undo_index = 0
        elif len(self._undo_list) == MAX_UNDO_STEPS:
            # drop the oldest undo pix:
            self._undo_list.pop(0)
        else:
            self._undo_index += 1
            # Forget the redos after this one:
            self._undo_list = self._undo_list[:self._undo_index]

        # If a tool needs to do several drawings, uses overrite to
        # undo them in only one step.  In that case, the index is not
        # changed:
        if overrite and self._undo_index != 0:
            self._undo_index -= 1

        undo_pix = gtk.gdk.Pixmap(widget.window, width, height, -1)
        undo_pix.draw_drawable(self.gc, self.pixmap,
            0, 0, 0, 0, width, height)

        self._undo_list.append(undo_pix)

        self.emit('action-saved')

    def copy(self):
        """ Copy Image.
            When the tool selection is working make the change
            the copy of selectioned area

            @param  self -- the Area object (GtkDrawingArea)
        """
        clipBoard = gtk.Clipboard()
        if 'SUGAR_ACTIVITY_ROOT' in os.environ:
            temp_dir = os.path.join(os.environ.get('SUGAR_ACTIVITY_ROOT'),
                'instance')
        else:
            temp_dir = '/tmp'

        f, tempPath = tempfile.mkstemp(suffix='.png', dir=temp_dir)
        del f

        if self.selmove:
            size = self.pixmap_sel.get_size()
            pixbuf_copy = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
                size[0], size[1])
            pixbuf_copy.get_from_drawable(self.pixmap_sel,
                gtk.gdk.colormap_get_system(), 0, 0, 0, 0, size[0], size[1])
            pixbuf_copy.save(tempPath, 'png')
            os.chmod(tempPath, 0604)

            clipBoard.set_with_data([('text/uri-list', 0, 0)],
                self._copyGetFunc, self._copyClearFunc, tempPath)
        else:
            logging.debug('Area.copy(self): Please select some area first')

    def _copyGetFunc(self, clipboard, selection_data, info, data):
        """  Determine type data to put in clipboard

            @param  self -- the Area object (GtkDrawingArea)
            @param  clipboard -- a gtk.Clipboard object
            @param  selection_data -- data of selection
            @param  info -- the app assigned integer associated with a target
            @param  data -- user data (tempPath)
        """
        tempPath = data

        if selection_data.target == "text/uri-list":
            selection_data.set_uris(['file://' + tempPath])

    def _copyClearFunc(self, clipboard, data):
        """ Clear the clipboard

            @param  self -- the Area object (GtkDrawingArea)
            @param  clipboard -- a gtk.Clipboard object
            @param  data -- user data (tempPath)
        """
        if (data != None):
            if (os.path.exists(data)):
                os.remove(data)
        data = None

    def drag_data_received(self, w, context, x, y, data, info, time):
        if data and data.format == 8:
            self.loadImage(urlparse(data.data).path, self)
            context.finish(True, False, time)
        else:
            context.finish(False, False, time)

    def past(self, widget):
        """ Past image.
        Past image that is in pixmap

            @param  self -- the Area object (GtkDrawingArea)
        """
        width, height = self.window.get_size()

        tempPath = os.path.join("/tmp", "tempFile")
        tempPath = os.path.abspath(tempPath)

        clipBoard = gtk.Clipboard()

        if clipBoard.wait_is_image_available():
            self.getout(True, widget)
            pixbuf_sel = clipBoard.wait_for_image()
            size = int(pixbuf_sel.get_width()), int(pixbuf_sel.get_height())
            self.pixmap_sel = gtk.gdk.Pixmap(self.window, size[0], size[1], -1)
            self.pixmap_sel.draw_pixbuf(self.gc, pixbuf_sel,
                0, 0, 0, 0, size[0], size[1],
                dither=gtk.gdk.RGB_DITHER_NORMAL, x_dither=0, y_dither=0)

            self.selmove = True
            self.desenha = True
            self.sel_get_out = False
            self.orig_x, self.orig_y = 0, 0

            self.pixmap_temp.draw_drawable(self.gc, self.pixmap, 0, 0, 0, 0,
                width, height)
            self.pixmap_temp.draw_drawable(self.gc, self.pixmap_sel,
                0, 0, 0, 0, size[0], size[1])

            self.set_selection_bounds(0, 0, size[0], size[1])

            self.tool['name'] = 'marquee-rectangular'
            self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
            self.emit('select')
        elif clipBoard.wait_is_uris_available():
            selection = clipBoard.wait_for_contents('text/uri-list')
            if selection != None:
                for uri in selection.get_uris():
                    self.loadImage(urlparse(uri).path, self)
        else:
            self.loadImage(tempPath, self)
            logging.debug('Area.past(self): Load from clipboard fails')
            logging.debug('loading from tempPath')

        self.queue_draw()

    def set_fill_color(self, color):
        """Set fill color.

            @param  self -- the Area object (GtkDrawingArea)
            @param  color -- a gdk.Color object

        """
        logging.error("TODO: Area.set_stroke_color %s", color)
        self.tool['cairo_fill_color'] = (color.red_float,
                color.green_float, color.blue_float, 0.3)

    def set_stroke_color(self, color):
        """Set stroke color.

            @param  self -- the Area object (GtkDrawingArea)
            @param  color -- a gdk.Color object

        """
        logging.error("TODO: Area.set_stroke_color %s", color)
        self.tool['cairo_stroke_color'] = (color.red_float,
                color.green_float, color.blue_float, 0.3)
        return
        self.activity.textview.modify_text(gtk.STATE_NORMAL, color)

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

        def proc_invert_color(temp_pix):
            try:
                import numpy
                # HACK: This numpy version has a bug and breaks the
                # 'invert_color' function
                # http://bugs.sugarlabs.org/ticket/3509
                if numpy.__version__ == '1.6.1':
                    logging.warning('You have installed a version of numpy '
                                    '(1.6.1) that has a bug and can\'t be '
                                    'used. Using string module instead '
                                    '(slower)')
                    raise ImportWarning
                pix_manip2 = temp_pix.get_pixels_array()
                pix_manip = numpy.ones(pix_manip2.shape, dtype=numpy.uint8) \
                            * 255
                pix_manip2 = pix_manip - pix_manip2
                temp_pix = gtk.gdk.pixbuf_new_from_array(pix_manip2,
                        gtk.gdk.COLORSPACE_RGB, 8)
            except (ImportError, ImportWarning):
                import string
                a = temp_pix.get_pixels()
                b = len(a) * ['\0']
                for i in range(len(a)):
                    b[i] = chr(255 - ord(a[i]))
                buff = string.join(b, '')
                temp_pix = gtk.gdk.pixbuf_new_from_data(buff,
                        temp_pix.get_colorspace(),
                        temp_pix.get_has_alpha(),
                        temp_pix.get_bits_per_sample(),
                        temp_pix.get_width(),
                        temp_pix.get_height(),
                        temp_pix.get_rowstride())
            return temp_pix

        self._do_process(widget, proc_invert_color)

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
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        gobject.idle_add(self._do_process_internal, widget, apply_process)

    def _do_process_internal(self, widget, apply_process):

        width, height = self.window.get_size()

        if self.selmove:
            size = self.pixmap_sel.get_size()
            temp_pix = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                size[0], size[1])
            temp_pix.get_from_drawable(self.pixmap_sel,
                gtk.gdk.colormap_get_system(), 0, 0, 0, 0, size[0], size[1])
        else:
            temp_pix = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                width, height)
            temp_pix.get_from_drawable(self.pixmap,
                gtk.gdk.colormap_get_system(), 0, 0, 0, 0, width, height)

        temp_pix = apply_process(temp_pix)

        if self.selmove:
            self.pixmap_sel.draw_pixbuf(self.gc, temp_pix, 0, 0, 0, 0,
                size[0], size[1], dither=gtk.gdk.RGB_DITHER_NORMAL,
                x_dither=0, y_dither=0)

            self.pixmap_temp.draw_drawable(self.gc, self.pixmap, 0, 0, 0, 0,
                width, height)
            self.pixmap_temp.draw_drawable(self.gc, self.pixmap_sel,
                0, 0, self.orig_x, self.orig_y, size[0], size[1])
            self.set_selection_bounds(self.orig_x, self.orig_y, size[0],
                    size[1])

#            self.pixmap_temp.draw_rectangle(self.gc_selection, False,
#                self.orig_x, self.orig_y, size[0], size[1])
#            self.pixmap_temp.draw_rectangle(self.gc_selection1, False,
#                self.orig_x - 1, self.orig_y - 1, size[0] + 2, size[1] + 2)

        else:
            self.pixmap.draw_pixbuf(self.gc, temp_pix, 0, 0, 0, 0,
                width, height, dither=gtk.gdk.RGB_DITHER_NORMAL,
                x_dither=0, y_dither=0)

        del temp_pix

        self.queue_draw()
        if not self.selmove:
            self.enableUndo(widget)
        self.set_tool_cursor()

    def drain_events(self, block=gtk.FALSE):
        while gtk.events_pending():
            gtk.mainiteration(block)

    def rotate_left(self, widget):
        """Rotate the image.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
        """
        self._rotate(widget, 90)

    def rotate_right(self, widget):
        """Rotate the image.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
        """
        self._rotate(widget, 270)

    def _rotate(self, widget, angle):
        """Rotate the image.

            @param  self -- the Area object (GtkDrawingArea)
            @param  widget -- the Area object (GtkDrawingArea)
        """
        width, height = self.window.get_size()

        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self.drain_events()

        if self.selmove:
            size = self.pixmap_sel.get_size()
            temp_pix = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                size[0], size[1])
            temp_pix.get_from_drawable(self.pixmap_sel,
                gtk.gdk.colormap_get_system(), 0, 0, 0, 0, size[0], size[1])
        else:
            temp_pix = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                width, height)
            temp_pix.get_from_drawable(self.pixmap,
                gtk.gdk.colormap_get_system(), 0, 0, 0, 0, width, height)

        temp_pix = temp_pix.rotate_simple(angle)

        if self.selmove:
            try:
                self.d.pixbuf_resize = \
                    self.d.pixbuf_resize.rotate_simple(angle)
            except:
                pass

            try:
                del(self.pixmap_sel)
            except:
                pass

            self.pixmap_sel = gtk.gdk.Pixmap(widget.window,
                size[1], size[0], -1)
            self.pixmap_sel.draw_pixbuf(self.gc, temp_pix, 0, 0, 0, 0,
                width=-1, height=-1, dither=gtk.gdk.RGB_DITHER_NORMAL,
                x_dither=0, y_dither=0)

            self.pixmap_temp.draw_drawable(self.gc, self.pixmap, 0, 0, 0, 0,
                width, height)
            self.pixmap_temp.draw_drawable(self.gc, self.pixmap_sel,
                0, 0, self.orig_x, self.orig_y, size[1], size[0])

            self.set_selection_bounds(self.orig_x, self.orig_y, size[0],
                    size[1])

#            self.pixmap_temp.draw_rectangle(self.gc_selection, False,
#                self.orig_x, self.orig_y, size[1], size[0])
#            self.pixmap_temp.draw_rectangle(self.gc_selection1, False,
#                self.orig_x - 1, self.orig_y - 1, size[1] + 2, size[0] + 2)

        else:
            win = self.window
            self.set_size_request(height, width)
            self.pixmap = gtk.gdk.Pixmap(win, height, width, -1)
            self.pixmap.draw_pixbuf(self.gc, temp_pix, 0, 0, 0, 0,
                height, width, dither=gtk.gdk.RGB_DITHER_NORMAL,
                x_dither=0, y_dither=0)
            self.pixmap_temp = gtk.gdk.Pixmap(win, height, width, -1)
            self.pixmap_temp.draw_pixbuf(self.gc, temp_pix, 0, 0, 0, 0,
                height, width, dither=gtk.gdk.RGB_DITHER_NORMAL,
                x_dither=0, y_dither=0)

            self.activity.center_area()

        del temp_pix

        self.queue_draw()
        if not self.selmove:
            self.enableUndo(widget)
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

            @param  self -- the Area object (GtkDrawingArea)
        """
        if self.selmove:
            return True
        else:
            return False

    def set_selection_bounds(self, x1, y1, width, height):
        """
            Set selection bounds

            @param  self -- the Area object (GtkDrawingArea)
            @param  x1,y1,x2,y2 -- the coords of limit points
        """
        self._selection_corners = (x1, y1, width, height)

    def get_selection_bounds(self):
        """
            Get points of selection

            @param  self -- the Area object (GtkDrawingArea)

            @return selection_corners

        """
        return self._selection_corners[0], self._selection_corners[1], \
            self._selection_corners[2], self._selection_corners[3]

    def loadImage(self, name, widget=None):
        """Load an image.

            @param  self -- Area instance
            @param  name -- string (image file path)
            @param  widget -- GtkDrawingArea

        """
        logging.debug('Area.loadImage Loading file %s', name)

        pixbuf = gtk.gdk.pixbuf_new_from_file(name)
        size = (int)(pixbuf.get_width()), (int)(pixbuf.get_height())
        #self.getout(True,widget)
        self.getout(True)
        #self.pixmap_sel = gtk.gdk.Pixmap(widget.window,size[0],size[1],-1)
        self.pixmap_sel = gtk.gdk.Pixmap(self.window, size[0], size[1], -1)
        self.pixmap_sel.draw_pixbuf(self.gc, pixbuf, 0, 0, 0, 0,
            size[0], size[1], dither=gtk.gdk.RGB_DITHER_NORMAL,
            x_dither=0, y_dither=0)

        self.sel_get_out = False
        self.selmove = True
        self.desenha = True
        self.orig_x, self.orig_y = 0, 0
        #width, height = widget.window.get_size()
        width, height = self.window.get_size()

        self.pixmap_temp.draw_drawable(self.gc, self.pixmap, 0, 0, 0, 0,
            width, height)
        self.pixmap_temp.draw_drawable(self.gc, self.pixmap_sel, 0, 0, 0, 0,
            size[0], size[1])

        self.set_selection_bounds(0, 0, size[0], size[1])

#        self.pixmap_temp.draw_rectangle(self.gc_selection, False,
#            0, 0, size[0], size[1])
#        self.pixmap_temp.draw_rectangle(self.gc_selection1, False,
#            -1, -1, size[0] + 2, size[1] + 2)

        self.tool['name'] = 'marquee-rectangular'
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
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
            self.enableUndo(self)

    def set_tool(self, tool):
        '''
        Method to configure all tools.

        @param - tool: a dictionary with the following keys:
                       'name': a string
                       'line size': a integer
                       'fill color': a gtk.gdk.Color object
                       'stroke color': a gtk.gdk.Color object
                       'line shape': a string - 'circle' or 'square', for now
                       'fill': a Boolean value
                       'vertices': a integer
        '''
        # logging.debug('Area.set_tool %s', tool)
        self.tool = tool
        try:
            if self.tool['line size'] is not None:
                self.configure_line(self.tool['line size'])

            if self.tool['fill color'] is not None:
                self.set_fill_color(self.tool['fill color'])
            else:
                # use black
                self.set_fill_color(self.black)

            if self.tool['stroke color'] is not None:
                self.set_stroke_color(self.tool['stroke color'])
            else:
                # use black
                self.set_stroke_color(self.black)

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

            display = gtk.gdk.display_get_default()
            if self.tool['name'] in cursors:
                name = cursors[self.tool['name']]
                cursor = gtk.gdk.cursor_new_from_name(display, name)
            elif self.tool['name'] == 'marquee-rectangular':
                cursor = gtk.gdk.Cursor(gtk.gdk.CROSS)
            else:
                filename = os.path.join('images', self.tool['name'] + '.png')
                pixbuf = gtk.gdk.pixbuf_new_from_file(filename)

                # Decide which is the cursor hot spot offset:
                if self.tool['name'] == 'stamp':
                    hotspot_x, hotspot_y  = 20, 38  # horizontal
                                                    # center and
                                                    # bottom
                elif self.tool['name'] == 'picker':
                    hotspot_x, hotspot_y  = 1, 38  # bottom left
                                                   # corner
                else:
                    hotspot_x, hotspot_y  = 0, 0

                cursor = gtk.gdk.Cursor(display, pixbuf, hotspot_x, hotspot_y)
        except gobject.GError:
            cursor = None
        self.window.set_cursor(cursor)

    def getout(self, undo=False, widget=None):
        logging.debug('Area.getout')

        try:
            self.pixmap_sel
            size = self.pixmap_sel.get_size()
            self.pixmap.draw_drawable(self.gc, self.pixmap_sel, 0, 0,
                self.orig_x, self.orig_y, size[0], size[1])
            self.selmove = False
            if undo:
                if widget is not None:
                    self.enableUndo(widget)
                else:
                    self.enableUndo(self)

            del(self.pixmap_sel)
            del(self.pixbuf_resize)

        except NameError, message:
            logging.debug(message)
        except Exception, message:
            logging.debug('Unexpected error: %s', message)

    def key_press(self, widget, event):
        if event.keyval == gtk.keysyms.BackSpace:
            if self.selmove:
                self.selmove = False
                try:
                    del(self.pixmap_sel)
                    del(self.pixbuf_resize)
                except:
                    pass

                if self.tool['name'] == 'marquee-rectangular':
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSS))
                widget.queue_draw()
                self.enableUndo(widget)
        elif event.keyval == gtk.keysyms.a and gtk.gdk.CONTROL_MASK:
            if self.selmove:
                self.getout()
            width, height = self.window.get_size()
            if self.tool['name'] == 'marquee-rectangular':
                self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
            self.pixmap_sel = gtk.gdk.Pixmap(self.window, width, height, -1)
            self.pixmap_sel.draw_drawable(self.gc, self.pixmap, 0, 0, 0, 0,
                width, height)
            self.pixmap_temp.draw_drawable(self.gc, self.pixmap, 0, 0, 0, 0,
                width, height)
            self.pixmap.draw_rectangle(self.get_style().white_gc, True, 0, 0,
                width, height)
            self.orig_x = 0
            self.orig_y = 0

            self.set_selection_bounds(0, 0, width - 1, height - 1)
#            self.pixmap_temp.draw_rectangle(self.gc_selection, False,
#                0, 0, width - 1, height - 1)
            self.selmove = True
            self.sel_get_out = False
            self.emit('select')
            widget.queue_draw()
        elif event.keyval == gtk.keysyms.d and gtk.gdk.CONTROL_MASK:
            if self.selmove:
                self.getout(True, widget)
                if self.tool['name'] == 'marquee-rectangular':
                    self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSS))
                widget.queue_draw()
        elif event.keyval == gtk.keysyms.Return:
            self.getout(True, widget)
            if self.tool['name'] == 'marquee-rectangular':
                self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSS))
            widget.queue_draw()

    def change_line_size(self, delta):
        # Used from OficinaActivity
        if self.tool['name'] in ['pencil', 'eraser', 'brush', 'rainbow']:
            size = self.tool['line size'] + delta
            if size < 1:
                size = 1
            self.tool['line size'] = size
            self.configure_line(size)
            self.queue_draw()
        if self.tool['name'] == 'stamp':
            self.resize_stamp(self.stamp_size + delta)
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
