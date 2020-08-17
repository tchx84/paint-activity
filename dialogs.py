#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _
import os
import glob
import shutil

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from sugar3.datastore import datastore
from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.icon import Icon
from sugar3.graphics.objectchooser import ObjectChooser
try:
    from sugar3.graphics.objectchooser import FILTER_TYPE_GENERIC_MIME
except:
    FILTER_TYPE_GENERIC_MIME = 'generic_mime'

from sugarapp.helpers import PrimaryMonitor
from sugarapp.widgets import DesktopOpenChooser

STORE = None
JOURNAL_IMAGES = []


class _DialogWindow(Gtk.Window):

    # A base class for a modal dialog window.

    def __init__(self, icon_name, title):
        super(_DialogWindow, self).__init__()

        self.set_border_width(style.LINE_WIDTH)
        width = PrimaryMonitor.width() - style.GRID_CELL_SIZE * 2
        height = PrimaryMonitor.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        vbox = Gtk.VBox()
        self.add(vbox)

        toolbar = _DialogToolbar(icon_name, title)
        toolbar.connect('stop-clicked', self._stop_clicked_cb)
        vbox.pack_start(toolbar, False, False, 0)

        self.content_vbox = Gtk.VBox()
        self.content_vbox.set_border_width(style.DEFAULT_SPACING)
        vbox.add(self.content_vbox)

        self.connect('realize', self._realize_cb)

    def _stop_clicked_cb(self, source):
        self.destroy()

    def _realize_cb(self, source):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_accept_focus(True)


class _DialogToolbar(Gtk.Toolbar):

    # Displays a dialog window's toolbar, with title, icon, and close box.

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, icon_name, title):
        super(_DialogToolbar, self).__init__()

        if icon_name is not None:
            icon = Icon()
            icon.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            self._add_widget(icon)

        self._add_separator()

        label = Gtk.Label(label=title)
        self._add_widget(label)

        self._add_separator(expand=True)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Done'))
        stop.connect('clicked', self._stop_clicked_cb)
        self.add(stop)

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.set_expand(expand)
        separator.set_draw(False)
        self.add(separator)

    def _add_widget(self, widget):
        tool_item = Gtk.ToolItem()
        tool_item.add(widget)
        self.add(tool_item)

    def _stop_clicked_cb(self, button):
        self.emit('stop-clicked')


class TuxStampDialog(_DialogWindow):
    __gsignals__ = {
        'stamp-selected': (
            GObject.SIGNAL_RUN_FIRST,
            GObject.TYPE_NONE,
            (GObject.TYPE_STRING,
             ))}

    def __init__(self, activity):
        super(TuxStampDialog, self).__init__('tool-stamp', _('Select stamp'))

        self._activity = activity

        global JOURNAL_IMAGES
        if not JOURNAL_IMAGES:
            JOURNAL_IMAGES = self._activity._journal_images

        global STORE
        if not STORE:
            STORE = self._create_model()

        self._iconview = Gtk.IconView()
        self._iconview.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._iconview.set_model(STORE)
        self._iconview.set_pixbuf_column(0)
        self._iconview.connect('selection-changed', self._stamp_changed)

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content_vbox.pack_start(scrollwin, True, True, 0)
        scrollwin.add(self._iconview)

        scrollwin.show_all()

    def _stamp_changed(self, widget):
        items = widget.get_selected_items()
        if not items:
            return

        iter_ = STORE.get_iter(items[0])
        filepath = STORE.get(iter_, 1)[0]
        if filepath == 'loadfromjournal':
            self.hide()
            chooser = DesktopOpenChooser(self._activity)

            try:
                filename = chooser.get_filename()
                newfilepath = GLib.build_filenamev([
                    GLib.get_user_data_dir(),
                    os.path.basename(filename)])
                shutil.copyfile(filename, newfilepath)

                if newfilepath not in JOURNAL_IMAGES:
                    JOURNAL_IMAGES.append(newfilepath)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        newfilepath,
                        50,
                        50)
                    STORE.append([pixbuf, newfilepath])
            finally:
                if not newfilepath:
                    self.show_all()
                else:
                    self.emit('stamp-selected', newfilepath)
                    self.destroy()
                del chooser
        else:
            self.emit('stamp-selected', filepath)
            self.destroy()

    def _create_model(self):
        tuxstamps = '/usr/share/tuxpaint/stamps'
        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        tuxavailable = True
        if not os.path.exists(tuxstamps):
            tuxavailable = False

        filepaths = []

        for object_id in JOURNAL_IMAGES:
            if os.path.exists(object_id) and os.path.isfile(object_id):
                filepaths.append(object_id)
                continue
            try:
                obj = datastore.get(object_id)
                fpath = obj.file_path
                if os.path.exists(fpath):
                    filepaths.append(fpath)
            except Exception:
                pass

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
            'icons/loadfromjournal.svg',
            50,
            50)
        store.append([pixbuf, 'loadfromjournal'])

        for f in filepaths:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                f,
                50,
                50)
            store.append([pixbuf, f])

        if tuxavailable:
            categories = []
            dirs = os.listdir(tuxstamps)
            for d in dirs:
                d = os.path.join(tuxstamps, d)
                if os.path.isdir(d):
                    categories.append(d)

            for cat in categories:
                patron = os.path.join(tuxstamps, cat)
                for x in range(5):
                    patron = patron + "/*"
                    files = glob.iglob(patron + '.png')
                    for f in files:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                            f,
                            50,
                            50)
                        store.append([pixbuf, f])
        return store


def get_journal_images():
    return JOURNAL_IMAGES
