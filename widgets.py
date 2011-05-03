# -*- coding: utf-8 -*-

from gettext import gettext as _

import gtk
import gobject

from sugar.graphics import style
from sugar.graphics.palette import ToolInvoker
from sugar.graphics.colorbutton import _ColorButton


class BrushButton(_ColorButton):
    """This is a ColorButton but show the color, the size and the shape
    of the brush.
    Instead of a color selector dialog it will pop up a Sugar palette.
    As a preview an DrawingArea is used, to use the same methods to
    draw than in the main window.
    """

    __gtype_name__ = 'BrushButton'

    def __init__(self, **kwargs):
        self._title = _('Choose brush properties')
        self._color = gtk.gdk.Color(0, 0, 0)
        self._has_palette = True
        self._has_invoker = True
        self._palette = None
        self._accept_drag = True
        self._brush_size = 2
        self._stamp_size = 20
        self._brush_shape = 'circle'
        self._resized_stamp = None
        self._preview = gtk.DrawingArea()
        self._preview.set_size_request(style.STANDARD_ICON_SIZE,
                                        style.STANDARD_ICON_SIZE)

        gobject.GObject.__init__(self, **kwargs)
        self._preview.set_events(gtk.gdk.BUTTON_PRESS_MASK)

        self._preview.connect('button_press_event', self.__mouse_down_cb)
        self._preview.connect("expose_event", self.expose)
        self.set_image(self._preview)

        self._gc = None

        if self._has_palette and self._has_invoker:
            self._invoker = WidgetInvoker(self)
            # FIXME: This is a hack.
            self._invoker.has_rectangle_gap = lambda: False
            self._invoker.palette = self._palette

    def _setup(self):
        if self.get_window() is not None:
            self._preview.fill_color = ''
            self._preview.show()
            self.pixmap = gtk.gdk.Pixmap(self.get_window(),
                                            style.STANDARD_ICON_SIZE,
                                            style.STANDARD_ICON_SIZE, 24)
            self._gc = self.get_window().new_gc()
            self.show_all()

    def get_brush_size(self):
        return self._brush_size

    def set_brush_size(self, brush_size):
        self._brush_size = brush_size
        self._preview.queue_draw()

    brush_size = gobject.property(type=int, getter=get_brush_size,
                    setter=set_brush_size)

    def get_brush_shape(self):
        return self._brush_shape

    def set_brush_shape(self, brush_shape):
        self._brush_shape = brush_shape
        self._preview.queue_draw()

    brush_shape = gobject.property(type=str, getter=get_brush_shape,
                    setter=set_brush_shape)

    def set_color(self, color):
        # receive gtk.gdk.Color
        self._color = color
        self._preview.queue_draw()

    def get_stamp_size(self):
        return self._stamp_size

    def set_stamp_size(self, stamp_size):
        self._stamp_size = stamp_size
        self._preview.queue_draw()

    stamp_size = gobject.property(type=int, getter=get_stamp_size,
                    setter=set_stamp_size)

    def set_resized_stamp(self, resized_stamp):
        self._resized_stamp = resized_stamp

    def stop_stamping(self):
        self._resized_stamp = None
        self._preview.queue_draw()

    def is_stamping(self):
        return self._resized_stamp != None

    def expose(self, widget, event):
        if self._gc is None:
            self._setup()

        if self.get_window() is not None:
            center = style.STANDARD_ICON_SIZE / 2
            self.pixmap.draw_rectangle(self._preview.get_style().white_gc,
            True, 0, 0, style.STANDARD_ICON_SIZE, style.STANDARD_ICON_SIZE)
            self._gc.set_foreground(self._color)

            if self.is_stamping():
                width = self._resized_stamp.get_width()
                height = self._resized_stamp.get_height()
                dx = center - width / 2
                dy = center - height / 2
                self.pixmap.draw_pixbuf(self._gc, self._resized_stamp,
                    0, 0, dx, dy, width, height)

            else:
                if self._brush_shape == 'circle':
                    self.pixmap.draw_arc(self._gc, True,
                        center - self._brush_size / 2,
                        center - self._brush_size / 2,
                        self._brush_size, self._brush_size, 0, 360 * 64)

                elif self._brush_shape == 'square':
                    self.pixmap.draw_rectangle(self._gc, True,
                        center - self._brush_size / 2,
                        center - self._brush_size / 2,
                        self._brush_size, self._brush_size)

        area = event.area
        widget.window.draw_drawable(self._gc, self.pixmap,
            area[0], area[1], area[0], area[1], area[2], area[3])
        return False

    def do_style_set(self, previous_style):
        pass

    def set_icon_name(self, icon_name):
        pass

    def get_icon_name(self):
        pass

    def set_icon_size(self, icon_size):
        pass

    def get_icon_size(self):
        pass

    def __mouse_down_cb(self, event):
        if self._palette:
            if not self._palette.is_up():
                self._palette.popup(immediate=True,
                                    state=self._palette.SECONDARY)
            else:
                self._palette.popdown(immediate=True)
            return True


class ButtonStrokeColor(gtk.ToolItem):
    """Class to manage the Stroke Color of a Button"""

    __gtype_name__ = 'BrushColorToolButton'
    __gsignals__ = {'color-set': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        tuple())}

    def __init__(self, activity, **kwargs):
        self._activity = activity
        self.properties = self._activity.area.tool
        self._accelerator = None
        self._tooltip = None
        self._palette_invoker = ToolInvoker()
        self._palette = None

        gobject.GObject.__init__(self, **kwargs)

        # The gtk.ToolButton has already added a normal button.
        # Replace it with a ColorButton
        self.color_button = BrushButton(has_invoker=False)
        self.add(self.color_button)
        self.color_button.set_brush_size(2)
        self.color_button.set_brush_shape('circle')
        self.color_button.set_stamp_size(20)

        # The following is so that the behaviour on the toolbar is correct.
        self.color_button.set_relief(gtk.RELIEF_NONE)

        self._palette_invoker.attach_tool(self)

        # This widget just proxies the following properties to the colorbutton
        self.color_button.connect('notify::color', self.__notify_change)
        self.color_button.connect('notify::icon-name', self.__notify_change)
        self.color_button.connect('notify::icon-size', self.__notify_change)
        self.color_button.connect('notify::title', self.__notify_change)
        self.color_button.connect('can-activate-accel',
                             self.__button_can_activate_accel_cb)

        self.create_palette()

    def __button_can_activate_accel_cb(self, button, signal_id):
        # Accept activation via accelerators regardless of this widget's state
        return True

    def __notify_change(self, widget, pspec):
        new_color = self.alloc_color(self.get_color())
        self.color_button.set_color(new_color)
        self.notify(pspec.name)

    def _color_button_cb(self, widget, pspec):
        color = self.get_color()
        self.set_stroke_color(color)

    def alloc_color(self, color):
        colormap = self._activity.area.get_colormap()
        return colormap.alloc_color(color.red, color.green, color.blue)

    def create_palette(self):
        self._palette = self.get_child().create_palette()

        color_palette_hbox = self._palette._picker_hbox
        content_box = gtk.VBox()
        self.size_spinbutton = gtk.SpinButton()
        # This is where we set restrictions for size:
        # Initial value, minimum value, maximum value, step
        adj = gtk.Adjustment(self.properties['line size'], 1.0, 100.0, 1.0)
        self.size_spinbutton.set_adjustment(adj)
        self.size_spinbutton.set_numeric(True)

        label = gtk.Label(_('Size: '))
        hbox_size = gtk.HBox()
        self.vbox_brush_options = gtk.VBox()
        content_box.pack_start(hbox_size)
        content_box.pack_start(self.vbox_brush_options)

        hbox_size.pack_start(label)
        hbox_size.pack_start(self.size_spinbutton)
        self.size_spinbutton.connect('value-changed', self._on_value_changed)

        # User is able to choose Shapes for 'Brush' and 'Eraser'
        item1 = gtk.RadioButton(None, _('Circle'))
        item1.set_active(True)
        image1 = gtk.Image()
        pixbuf1 = gtk.gdk.pixbuf_new_from_file_at_size(
                                './icons/tool-shape-ellipse.svg',
                                style.SMALL_ICON_SIZE,
                                style.SMALL_ICON_SIZE)
        image1.set_from_pixbuf(pixbuf1)
        item1.set_image(image1)

        item2 = gtk.RadioButton(item1, _('Square'))
        image2 = gtk.Image()
        pixbuf2 = gtk.gdk.pixbuf_new_from_file_at_size(
                                './icons/tool-shape-rectangle.svg',
                                style.SMALL_ICON_SIZE,
                                style.SMALL_ICON_SIZE)
        image2.set_from_pixbuf(pixbuf2)
        item2.set_image(image2)

        item1.connect('toggled', self._on_toggled, self.properties, 'circle')
        item2.connect('toggled', self._on_toggled, self.properties, 'square')

        label = gtk.Label(_('Shape'))

        self.vbox_brush_options.pack_start(label)
        self.vbox_brush_options.pack_start(item1)
        self.vbox_brush_options.pack_start(item2)

        keep_aspect_checkbutton = gtk.CheckButton(_('Keep aspect'))
        ratio = self._activity.area.keep_aspect_ratio
        keep_aspect_checkbutton.set_active(ratio)
        keep_aspect_checkbutton.connect('toggled',
            self._keep_aspect_checkbutton_toggled)
        self.vbox_brush_options.pack_start(keep_aspect_checkbutton)

        color_palette_hbox.pack_start(gtk.VSeparator(),
                                     padding=style.DEFAULT_SPACING)
        color_palette_hbox.pack_start(content_box)
        color_palette_hbox.show_all()
        self._update_palette()
        return self._palette

    def _keep_aspect_checkbutton_toggled(self, checkbutton):
        self._activity.area.keep_aspect_ratio = checkbutton.get_active()

    def _update_palette(self):
        palette_children = self._palette._picker_hbox.get_children()
        if self.color_button.is_stamping():
            # Hide palette color widgets:
            for ch in palette_children[:4]:
                ch.hide_all()
            # Hide brush options:
            self.vbox_brush_options.hide_all()
            # Change title:
            self.set_title(_('Stamp properties'))
        else:
            # Show palette color widgets:
            for ch in palette_children[:4]:
                ch.show_all()
            # Show brush options:
            self.vbox_brush_options.show_all()
            # Change title:
            self.set_title(_('Brush properties'))

        self._palette._picker_hbox.resize_children()
        self._palette._picker_hbox.queue_draw()

    def update_stamping(self):
        if self.color_button.is_stamping():
            self.size_spinbutton.set_value(self.color_button.stamp_size)
        else:
            self.size_spinbutton.set_value(self.color_button.brush_size)
        self._update_palette()

    def _on_value_changed(self, spinbutton):
        size = spinbutton.get_value_as_int()
        if self.color_button.is_stamping():
            self.properties['stamp size'] = size
            resized_stamp = self._activity.area.resize_stamp(size)
            self.color_button.set_resized_stamp(resized_stamp)
            self.color_button.set_stamp_size(self.properties['stamp size'])
        else:
            self.properties['line size'] = size
            self.color_button.set_brush_size(self.properties['line size'])
        self._activity.area.set_tool(self.properties)

    def _on_toggled(self, radiobutton, tool, shape):
        if radiobutton.get_active():
            self.properties['line shape'] = shape
            self.color_button.set_brush_shape(shape)
            self.color_button.set_brush_size(self.properties['line size'])

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = gobject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_color(self, color):
        self.color_button.set_color(color)

    def get_color(self):
        return self.get_child().props.color

    color = gobject.property(type=object, getter=get_color, setter=set_color)

    def set_title(self, title):
        self.get_child().props.title = title

    def get_title(self):
        return self.get_child().props.title

    title = gobject.property(type=str, getter=get_title, setter=set_title)

    def do_expose_event(self, event):
        child = self.get_child()
        allocation = self.get_allocation()
        if self._palette and self._palette.is_up():
            invoker = self._palette.props.invoker
            invoker.draw_rectangle(event, self._palette)
        elif child.state == gtk.STATE_PRELIGHT:
            child.style.paint_box(event.window, gtk.STATE_PRELIGHT,
                                  gtk.SHADOW_NONE, event.area,
                                  child, 'toolbutton-prelight',
                                  allocation.x, allocation.y,
                                  allocation.width, allocation.height)

        gtk.ToolButton.do_expose_event(self, event)
