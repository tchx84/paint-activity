# -*- coding: utf-8 -*-
"""
@namespace Desenho

    Pixmap manipulation


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

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject
import logging
import math
import cairo

# The time to wait for the resize operation to be
# executed, after the resize controls are pressed.
RESIZE_DELAY = 500


class Desenho:
    # Pixmap manipulation

    def __init__(self, widget):
        """Initialize Desenho object.

            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)

        """
        self._resize_timer = None
        self._rainbow_color_list = ['#ff0000',  # red
                                    '#ff8000',  # orange
                                    '#ffff00',  # yellow
                                    '#80ff00',  # lime
                                    '#00ff00',  # green
                                    '#00ff80',  # green water
                                    '#00ffff',  # light blue
                                    '#007fff',  # almost blue
                                    '#0000ff',  # blue
                                    '#8000ff',  # indigo
                                    '#ff00ff',  # pink violet
                                    '#ff0080']  # violet
        self._rainbow_counter = 0

        self.points = []
        self.points1 = []
        self.points2 = []
        self.points3 = []
        self.points4 = []
        self._last_points_used = []
        self._last_point_drawn_index = 0

    def clear_control_points(self):
        self._last_points_used = []

    def line(self, widget, coords, temp):
        """Draw line.

            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple

        """
        if temp:
            ctx = widget.temp_ctx
        else:
            ctx = widget.drawing_ctx

        ctx.save()
        ctx.new_path()
        ctx.set_line_width(widget.tool['line size'])
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*widget.tool['cairo_stroke_color'])
        ctx.move_to(widget.oldx, widget.oldy)
        ctx.line_to(coords[0], coords[1])
        ctx.stroke()
        ctx.restore()
        # TODO: clip
        widget.queue_draw()

    def eraser(self, widget, coords, last):
        """Erase part of the drawing.

            @param  self -- Desenho.Desenho instance
            @param  last -- last of oldx
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  size -- integer (default 30)
            @param  shape -- string (default 'circle')

        """
        self._trace(widget, coords, last)

    def brush(self, widget, coords, last):
        """Paint with brush.

            @param  self -- Desenho.Desenho instance
            @param  last -- last of oldx
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  size -- integer (default 30)
            @param  shape -- string (default 'circle')

        """
        self._trace(widget, coords, last)

    def kalidoscope(self, widget, coords, last):
        """Paint with kalidoscope.

            @param  self -- Desenho.Desenho instance
            @param  last -- last of oldx
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple

        """
        if not last:
            self.points1 = []
            self.points2 = []
            self.points3 = []
            self.points4 = []

        shape = widget.tool['line shape']
        rounded = (shape == 'circle')
        x1, y1 = coords
        x3, y2 = x1, y1
        width, height = widget.get_size()
        x2 = width - x1
        x4 = x2
        y3 = height - y1
        y4 = y3

        self.points1.append((x1, y1))
        self.points2.append((x2, y2))
        self.points3.append((x3, y3))
        self.points4.append((x4, y4))

        self._draw_polygon(widget, False, False, self.points1, False, rounded)
        self._draw_polygon(widget, False, False, self.points2, False, rounded)
        self._draw_polygon(widget, False, False, self.points3, False, rounded)
        self._draw_polygon(widget, False, False, self.points4, False, rounded)
        widget.queue_draw()

    def stamp(self, widget, coords, last, stamp_size=20):
        """Paint with stamp.

            @param  self -- Desenho.Desenho instance
            @param  last -- last of oldx
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  stamp_size -- integer (default 20)

        """

        widget.desenha = False

        width = widget.resized_stamp.get_width()
        height = widget.resized_stamp.get_height()
        dx = coords[0] - width / 2
        dy = coords[1] - height / 2

        widget.drawing_ctx.save()
        widget.drawing_ctx.translate(dx, dy)
        widget.drawing_ctx.rectangle(dx, dy, width, height)
        Gdk.cairo_set_source_pixbuf(widget.drawing_ctx, widget.resized_stamp,
                                    0, 0)
        widget.drawing_ctx.paint()
        widget.drawing_ctx.restore()

        widget.queue_draw_area(dx, dy, width, height)

    def rainbow(self, widget, coords, last):
        """Paint with rainbow.

            @param  self -- Desenho.Desenho instance
            @param  last -- last of oldx
            @param  widget -- Area object (GtkDrawingArea)
            @param  color -- select the color adress
            @param  coords -- Two value tuple
            @param  size -- integer (default 30)
            @param  shape -- string (default 'circle')

        """
        _color_str = self._rainbow_color_list[self._rainbow_counter]
        _color = Gdk.color_parse(_color_str)
        self._rainbow_counter += 1
        if self._rainbow_counter > 11:
            self._rainbow_counter = 0

        widget.drawing_ctx.set_source_rgba(_color.red, _color.green,
                                           _color.blue, 0.3)
        self._old_trace(widget, coords, last)

    def _old_trace(self, widget, coords, last):
        """
        _old_trace is used only by rainbow
        """
        widget.desenha = False
        size = widget.tool['line size']
        shape = widget.tool['line shape']

        if shape == 'circle':
            if last:
                widget.drawing_ctx.set_line_width(size)

                widget.drawing_ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                widget.drawing_ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                widget.drawing_ctx.move_to(last[0], last[1])
                widget.drawing_ctx.line_to(coords[0], coords[1])
                widget.drawing_ctx.stroke()
            else:
                widget.drawing_ctx.move_to(coords[0], coords[1])
                widget.drawing_ctx.arc(coords[0], coords[1],
                                       size / 2, 0., 2 * math.pi)
                # when activity starts with rainbow tool, need this to
                # not paint the background
                widget.drawing_ctx.set_source_rgba(1.0, 1.0, 1.0, 0.0)
                widget.drawing_ctx.fill()

        elif shape == 'square':
            if last:
                points = [(last[0] - size / 2, last[1] - size / 2),
                          (coords[0] - size / 2, coords[1] - size / 2),
                          (coords[0] + size / 2, coords[1] + size / 2),
                          (last[0] + size / 2, last[1] + size / 2)]
                for point in points:
                    widget.drawing_ctx.line_to(*point)
                widget.drawing_ctx.fill()
                points = [(last[0] + size / 2, last[1] - size / 2),
                          (coords[0] + size / 2, coords[1] - size / 2),
                          (coords[0] - size / 2, coords[1] + size / 2),
                          (last[0] - size / 2, last[1] + size / 2)]
                for point in points:
                    widget.drawing_ctx.line_to(*point)
                widget.drawing_ctx.fill()
            else:
                widget.drawing_ctx.move_to(coords[0] - size / 2,
                                           coords[1] - size / 2)
                widget.drawing_ctx.rectangle(coords[0] - size / 2,
                                             coords[1] - size / 2, size, size)
                # when activity starts with rainbow tool, need this to
                # not paint the background
                widget.drawing_ctx.set_source_rgba(1.0, 1.0, 1.0, 0.0)
                widget.drawing_ctx.fill()

        if last:
            x = min(coords[0], last[0])
            width = max(coords[0], last[0]) - x
            y = min(coords[1], last[1])
            height = max(coords[1], last[1]) - y
            # We add size to avoid drawing dotted lines
            widget.queue_draw_area(x - size, y - size,
                                   width + size * 2, height + size * 2)
        else:
            widget.queue_draw()

    def finish_trace(self, widget):
        widget.desenha = False
        shape = widget.tool['line shape']
        rounded = (shape == 'circle')
        self._draw_polygon(widget, False, False, self.points, False, rounded)
        if not rounded and len(self.points) == 1:
            # draw a square if the mouse was not moved
            size = widget.tool['line size']
            coords = self.points[0]
            widget.drawing_ctx.save()
            if widget.tool['name'] == 'eraser':
                color = (1.0, 1.0, 1.0, 1.0)
            else:
                color = widget.tool['cairo_stroke_color']
            widget.drawing_ctx.set_source_rgba(*color)
            widget.drawing_ctx.move_to(coords[0] - size / 2,
                                       coords[1] - size / 2)
            widget.drawing_ctx.rectangle(coords[0] - size / 2,
                                         coords[1] - size / 2, size, size)
            widget.drawing_ctx.fill()
            widget.drawing_ctx.restore()

        self.points = []
        self._last_point_drawn_index = 0

    def _trace(self, widget, coords, last):
        widget.desenha = True
        size = widget.tool['line size']
        shape = widget.tool['line shape']

        rounded = (shape == 'circle')

        self.points.append((coords[0], coords[1]))
        if last:
            self._draw_polygon(widget, True, False, self.points, False,
                               rounded)
        self.clear_control_points()
        if last:
            x = min(coords[0], last[0])
            width = max(coords[0], last[0]) - x
            y = min(coords[1], last[1])
            height = max(coords[1], last[1]) - y
            # We add size to avoid drawing dotted lines
            widget.queue_draw_area(x - size, y - size,
                                   width + size * 2, height + size * 2)

    def square(self, widget, coords, temp, fill):
        """Draw a square.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between drawing context and temp context
            @param  fill -- Fill object
        """

        x, y, dx, dy, = self.adjust(widget, coords)
        points = [(x, y), (x + dx, y), (x + dx, y + dy), (x, y + dy)]
        self._draw_polygon(widget, temp, fill, points)

    def _draw_polygon(self, widget, temp, fill, points, closed=True,
                      rounded=False):
        if not points:
            return
        if temp:
            ctx = widget.temp_ctx
        else:
            ctx = widget.drawing_ctx

        ctx.save()
        ctx.new_path()
        ctx.move_to(*points[0])
        for point in points:
            ctx.line_to(*point)
        if closed:
            ctx.close_path()
        if rounded:
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        else:
            ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
            ctx.set_line_join(cairo.LINE_JOIN_MITER)
        ctx.set_line_width(widget.tool['line size'])
        if fill:
            ctx.save()
            ctx.set_source_rgba(*widget.tool['cairo_fill_color'])
            ctx.fill_preserve()
            ctx.set_operator(cairo.OPERATOR_SOURCE)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1)
            ctx.stroke_preserve()
            ctx.restore()

        if widget.tool['name'] == 'eraser':
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        else:
            ctx.set_source_rgba(*widget.tool['cairo_stroke_color'])
        ctx.stroke()
        ctx.restore()
        if fill or closed:
            self._last_points_used.extend(points)
            area = widget.calculate_damaged_area(self._last_points_used)
            widget.queue_draw_area(*area)
        else:
            # if is a open line and is not filled (like when using the pencil)
            # we don't need draw all the poligon, can draw only the part
            # from the last queue update until now
            self._last_points_used = points[self._last_point_drawn_index:]
            if self._last_points_used:
                area = widget.calculate_damaged_area(self._last_points_used)
                self._last_point_drawn_index = len(points)
                widget.queue_draw_area(*area)

    def triangle(self, widget, coords, temp, fill):
        """Draw a triangle.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between drawing context and temp context
            @param  fill -- Fill object
        """

        points = [(widget.oldx, widget.oldy),
                  (widget.oldx + int((coords[0] - widget.oldx) / 2),
                   coords[1]),
                  (coords[0], widget.oldy)]
        self._draw_polygon(widget, temp, fill, points)

    def trapezoid(self, widget, coords, temp, fill):
        """Draw a trapezoid.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between context and temp context
            @param  fill -- Fill object
        """

        dif = int((coords[0] - widget.oldx) / 4)
        points = [(widget.oldx, widget.oldy), (widget.oldx + dif, coords[1]),
                  (coords[0] - dif, coords[1]), (coords[0], widget.oldy)]
        self._draw_polygon(widget, temp, fill, points)

    def arrow(self, widget, coords, temp, fill):
        """Draw a arrow.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between context and temp context
            @param  fill -- Fill object
        """
        x = coords[0] - widget.oldx
        y = coords[1] - widget.oldy
        A = math.atan2(y, x)
        dA = 2 * math.pi / 2
        r = math.hypot(y, x)
        p = [(widget.oldx, widget.oldy)]
        p.append((widget.oldx + int(r * math.cos(A)),
                  widget.oldy + int(r * math.sin(A))))
        p.append((widget.oldx + int(0.74 * r * math.cos(A + dA / 6)),
                  widget.oldy + int(0.74 * r * math.sin(A + dA / 6))))
        p.append((widget.oldx + int(2 * r * math.cos(A + dA / 6 + dA / 20)),
                  widget.oldy + int(2 * r * math.sin(A + dA / 6 + dA / 20))))
        p.append((widget.oldx +
                  int(2 * r * math.cos(A + dA / 6 - dA / 20 + dA / 6)),
                  widget.oldy +
                  int(2 * r * math.sin(A + dA / 6 - dA / 20 + dA / 6))))
        p.append((widget.oldx + int(0.74 * r * math.cos(A + dA / 6 + dA / 6)),
                  widget.oldy + int(0.74 * r * math.sin(A + dA / 6 + dA / 6))))
        p.append((widget.oldx + int(r * math.cos(A + dA / 2)),
                  widget.oldy + int(r * math.sin(A + dA / 2))))

        self._draw_polygon(widget, temp, fill, p)

    def parallelogram(self, widget, coords, temp, fill):
        """Draw a parallelogram.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between context and temp context
            @param  fill -- Fill object
        """
        x = int((coords[0] - widget.oldx) / 4)
        points = [(widget.oldx, widget.oldy), (coords[0] - x, widget.oldy),
                  (coords[0], coords[1]), (widget.oldx + x, coords[1])]
        self._draw_polygon(widget, temp, fill, points)

    def star(self, widget, coords, n, temp, fill):
        """Draw polygon with n sides.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  n -- number of sides
            @param  temp -- switch between context and temp context
            @param  fill -- Fill object
        """
        x = coords[0] - widget.oldx
        y = coords[1] - widget.oldy
        A = math.atan2(y, x)
        dA = 2 * math.pi / n
        r = math.hypot(y, x)
        p = [(widget.oldx + int(r * math.cos(A)),
             widget.oldy + int(r * math.sin(A))),
             (widget.oldx + int(0.4 * r * math.cos(A + dA / 2)),
             widget.oldy + int(0.4 * r * math.sin(A + dA / 2)))]
        for _i in range(int(n) - 1):
            A = A + dA
            p.append((widget.oldx + int(r * math.cos(A)),
                     widget.oldy + int(r * math.sin(A))))
            p.append((widget.oldx + int(0.4 * r * math.cos(A + dA / 2)),
                     widget.oldy + int(0.4 * r * math.sin(A + dA / 2))))
        self._draw_polygon(widget, temp, fill, p)

    def polygon_regular(self, widget, coords, n, temp, fill):
        """Draw polygon with n sides.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  n -- number of sides
            @param  temp -- switch between context and temp context
            @param  fill -- Fill object
        """
        x = coords[0] - widget.oldx
        y = coords[1] - widget.oldy
        A = math.atan2(y, x)
        dA = 2 * math.pi / n
        r = math.hypot(y, x)
        p = [(widget.oldx + int(r * math.cos(A)),
             widget.oldy + int(r * math.sin(A)))]
        for _i in range(int(n) - 1):
            A = A + dA
            p.append((widget.oldx + int(r * math.cos(A)),
                     widget.oldy + int(r * math.sin(A))))
        self._draw_polygon(widget, temp, fill, p)

    def heart(self, widget, coords, temp, fill):
        """Draw polygon with n sides.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between context and temp context
            @param  fill -- Fill object
        """
        if temp:
            ctx = widget.temp_ctx
        else:
            ctx = widget.drawing_ctx

        dy = math.fabs(coords[1] - widget.oldy)
        r = math.hypot(dy, dy)
        w = r / 10.0

        if w == 0:
            # non invertible cairo matrix
            return

        ctx.set_line_width(widget.tool['line size'])
        line_width = ctx.get_line_width()

        ctx.save()
        ctx.new_path()
        ctx.translate(widget.oldx, widget.oldy)
        ctx.scale(w, w)
        ctx.move_to(0, 0)
        ctx.curve_to(0, -30, -50, -30, -50, 0)
        ctx.curve_to(-50, 30, 0, 35, 0, 60)
        ctx.curve_to(0, 35, 50, 30, 50, 0)
        ctx.curve_to(50, -30, 0, -30, 0, 0)

        ctx.set_line_width(line_width / w)
        if fill:
            ctx.save()
            ctx.set_source_rgba(*widget.tool['cairo_fill_color'])
            ctx.fill_preserve()
            ctx.set_operator(cairo.OPERATOR_SOURCE)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1)
            ctx.stroke_preserve()
            ctx.restore()

        ctx.set_source_rgba(*widget.tool['cairo_stroke_color'])
        ctx.stroke()
        ctx.restore()

        # TODO: clip
        widget.queue_draw()

    def circle(self, widget, coords, temp, fill):
        """Draw a circle.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between context and temp context
            @param  fill -- Fill object
        """
        if temp:
            ctx = widget.temp_ctx
        else:
            ctx = widget.drawing_ctx

        x, y, dx, dy = self.adjust(widget, coords)
        if dx == 0 or dy == 0:
            # scale by 0 gives error
            return
        ctx.set_line_width(widget.tool['line size'])
        line_width = ctx.get_line_width()
        ctx.save()
        ctx.new_path()
        ctx.translate(x, y)
        ctx.scale(dx, dy)
        ctx.arc(0., 0., 1., 0., 2 * math.pi)
        ctx.set_line_width(line_width / float(min(dx, dy)))
        if fill:
            ctx.save()
            ctx.set_source_rgba(*widget.tool['cairo_fill_color'])
            ctx.fill_preserve()
            ctx.set_operator(cairo.OPERATOR_SOURCE)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1)
            ctx.stroke_preserve()
            ctx.restore()

        ctx.set_source_rgba(*widget.tool['cairo_stroke_color'])
        ctx.stroke()
        ctx.restore()
        # TODO: clip
        widget.queue_draw()

    def clear(self, widget):
        """Clear the drawing.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
        """
        logging.debug('Desenho.clear')
        widget.desenha = False

        widget.textos = []
        x, y = 0, 0
        width, height = widget.get_size()
        # try to clear a selected area first
        if widget.is_selected():
            selection_surface = widget.get_selection()
            _x, _y, width, height = widget.get_selection_bounds()
            ctx = cairo.Context(selection_surface)
            ctx.rectangle(0, 0, width, height)
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.fill()
        else:
            widget.drawing_ctx.rectangle(x, y, width, height)
            widget.drawing_ctx.set_source_rgb(1.0, 1.0, 1.0)
            widget.drawing_ctx.fill()

        widget.queue_draw()

    def text(self, widget, coord_x, coord_y):
        """Display and draw text in the drawing area.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coord_x
            @param  coord_y
        """

        if not widget.text_in_progress:
            widget.text_in_progress = True

            widget.activity.move_textview(coord_x, coord_y)
            widget.activity.textview.show()
            widget.activity.textview.set_cursor_visible(True)
            widget.activity.textview.grab_focus()

        else:
            widget.text_in_progress = False
            textview = widget.activity.textview
            textview.set_cursor_visible(False)
            # need wait until the cursor is hidden
            GObject.idle_add(self._finalize_text, widget, textview)

    def _finalize_text(self, widget, textview):
        window = textview.get_window(Gtk.TextWindowType.TEXT)
        ctx = widget.drawing_ctx
        tv_alloc = textview.get_allocation()
        Gdk.cairo_set_source_window(ctx, window, tv_alloc.x, tv_alloc.y)
        ctx.paint()

        widget.activity.textview.hide()
        widget.drawing_canvas.flush()

        textview.get_buffer().set_text('')

        widget.enable_undo()
        widget.queue_draw()

    def selection(self, widget, coords):
        """Make a selection.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
        """

        x, y, dx, dy = self.adjust(widget, coords, True)
        widget.set_selection_bounds(x, y, dx, dy)
        # TODO: clip
        widget.queue_draw()

    def move_selection(self, widget, coords):
        """Move the selection.

            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  mvcopy -- Copy or Move
            @param  pixbuf_copy -- For import image

        """
        widget.desenha = True

        dx = int(coords[0] - widget.oldx)
        dy = int(coords[1] - widget.oldy)

        x, y, width, height = widget.get_selection_bounds()

        if widget.pending_clean_selection_background:
            # clear the selection background
            widget.clear_selection_background()
            widget.pending_clean_selection_background = False

        widget.oldx = coords[0]
        widget.oldy = coords[1]

        new_x, new_y = x + dx, y + dy
        widget.set_selection_start(new_x, new_y)

        widget.queue_draw()

    def resize_selection(self, widget, coords):
        """Move the selection.

            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  mvcopy -- Copy or Move
            @param  pixbuf_copy -- For import image

        """
        dx = int(coords[0] - widget.oldx)
        dy = int(coords[1] - widget.oldy)

        sel_width = widget.selection_surface.get_width()
        sel_height = widget.selection_surface.get_height()

        if widget.pending_clean_selection_background:
            # clear the selection background
            widget.clear_selection_background()
            widget.pending_clean_selection_background = False

        width_scale = float(sel_width + dx) / float(sel_width)
        height_scale = float(sel_height + dy) / float(sel_height)

        if width_scale < 0 or height_scale < 0:
            return

        widget.resize_selection_surface(width_scale, height_scale)

    def freeform(self, widget, coords, temp, fill, param=None):
        """Draw polygon.
            @param  self -- Desenho.Desenho instance
            @param  widget -- Area object (GtkDrawingArea)
            @param  coords -- Two value tuple
            @param  temp -- switch between drawing context and temp context
            @param  fill -- Fill object
        """
        if param == "moving":
            # mouse not pressed moving
            if self.points:
                if widget.last:
                    self.points.append((coords[0], coords[1]))
                    widget.last = []
                else:
                    self.points[-1] = (coords[0], coords[1])
        elif param == "motion":
            # when mousepress or mousemove
            if widget.last:
                self.points.append((widget.last[0], widget.last[1]))
                self.points.append((coords[0], coords[1]))
            else:
                self.points.append((widget.oldx, widget.oldy))
                self.points.append((coords[0], coords[1]))
            widget.last = coords
        elif param == "release":
            if len(self.points) > 2:
                first = self.points[0]
                dx = coords[0] - first[0]
                dy = coords[1] - first[1]
                d = math.hypot(dx, dy)
                if d > 20:
                    widget.last = coords
                    self.points.append(coords)
                else:
                    # close the polygon
                    self.points.append((first[0], first[1]))
                    # set the last point index to zero to force draw all
                    # the polygon
                    self._last_point_drawn_index = 0
                    self._draw_polygon(widget, False, fill, self.points)
                    widget.desenha = False
                    widget.last = []
                    self.points = []
                    widget.enable_undo()
                    return

        widget.desenha = True

        if self.points:
            # Draw a circle to show where the freeform start/finish
            ctx = widget.temp_ctx
            ctx.save()
            x_init, y_init = self.points[0]
            ctx.new_path()
            ctx.translate(x_init, y_init)
            ctx.set_line_width(1)
            ctx.set_source_rgba(1., 1., 1., 1.)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.arc(0, 0, 20, 0., 2 * math.pi)
            ctx.stroke_preserve()
            ctx.set_dash([5, 5], 0)
            ctx.set_source_rgba(0., 0., 0., 1.)
            ctx.stroke()
            ctx.restore()

        # Display the polygon open in the temp canvas
        self._draw_polygon(widget, True, False, self.points, closed=False)
        self.clear_control_points()

    def adjust(self, widget, coords, locked=False):
        width, height = widget.get_size()
        if widget.oldx > int(coords[0]):
            xi = int(coords[0])
            xf = widget.oldx
        else:
            xi = widget.oldx
            xf = int(coords[0])

        if widget.oldy > int(coords[1]):
            yi = int(coords[1])
            yf = widget.oldy
        else:
            yi = widget.oldy
            yf = int(coords[1])

        if locked:
            if xi < 0:
                xi = 0
            if yi < 0:
                yi = 0
            if xf > width:
                xf = width
            if yf > height:
                yf = height

        dx = xf - xi
        dy = yf - yi
        return xi, yi, dx, dy
