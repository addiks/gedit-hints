# Copyright (C) 2015 Gerrit Addiks <gerrit@addiks.net>
# https://github.com/addiks/gedit-dbgp-plugin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import csv

from gi.repository import Gtk, GObject, Gedit, PeasGtk, Gio
from addiks_hints.gladehandler import GladeHandler
from hintmanager import HintManager

class AddiksHintsApp(GObject.Object, Gedit.AppActivatable, PeasGtk.Configurable):
    app = GObject.property(type=Gedit.App)

    def __init__(self):
        GObject.Object.__init__(self)
        self._glade_builder = None
        self._glade_handler = None
        self._hint_manager = None
        self._settings = None

        if not os.path.exists(os.path.dirname(__file__)+"/gschemas.compiled"):
            pass

        schema_source = Gio.SettingsSchemaSource.new_from_directory(
            os.path.dirname(__file__),
            Gio.SettingsSchemaSource.get_default(),
            False,
        )
        schema = schema_source.lookup('de.addiks.gedit.hints', False)
        self._settings = Gio.Settings.new_full(schema, None, None)

        for name in ['phplint', 'phpmd', 'phpcs']:
            isActive = self._settings.get_boolean(name)
            self.get_hint_manager().set_adapter_state(name, isActive)

    def set_config(self, name, is_active):
        self.get_hint_manager().set_adapter_state(name, is_active)

    def do_activate(self):
        AddiksHintsApp.__instance = self

    def do_deactivate(self):
        AddiksHintsApp.__instance = None

    def do_update_state(self):
        pass

    ### CONFIGURATION

    def do_create_configure_widget(self):
        filename = os.path.dirname(__file__)+"/hints.glade"
        glade_handler = self._getGladeHandler()
        glade_builder = Gtk.Builder()
        glade_builder.add_objects_from_file(filename, ["gridConfig"])
        glade_builder.connect_signals(glade_handler)
        for key, objectName in [
            ["phplint",      "switchPHPLint"],
            ["phpmd",        "switchPHPMD"],
            ["phpcs",        "switchPHPCS"]]:
            switch = glade_builder.get_object(objectName)
            self._settings.bind(key, switch, "active", Gio.SettingsBindFlags.DEFAULT)
        return glade_builder.get_object("gridConfig")

    def get_settings(self):
        return self._settings

    ### PHPMD

    def show_phpmd_config(self):
        builder = self._getGladeBuilder()
        configWindow = builder.get_object("windowPHPMDConfig")
        configWindow.show_all()
        self.update_phpmd_ruleset_treeview()

    def add_phpmd_ruleset(self, ruleset, directory):
        path = self.get_phpmd_ruleset_file()
        with open(path, "a") as handle:
            writer = csv.writer(handle, delimiter=",")
            writer.writerow([directory, ruleset])

    def get_all_phpmd_rulesets(self):
        path = self.get_phpmd_ruleset_file()
        rulesets = []
        with open(path, "r") as handle:
            reader = csv.reader(handle, delimiter=",")
            for directory, ruleset in reader:
                rulesets.append([directory, ruleset])
        return rulesets

    def remove_phpmd_ruleset(self, needleRuleset, needleDirectory):
        path = self.get_phpmd_ruleset_file()
        rulesets = self.get_all_phpmd_rulesets()
        self.reset_phpmd_ruleset_file()
        for directory, ruleset in rulesets:
            if ruleset != needleRuleset or directory != needleDirectory:
                self.add_phpmd_ruleset(ruleset, directory)

    def reset_phpmd_ruleset_file(self):
        path = self.get_phpmd_ruleset_file()
        with open(path, 'w'):
            os.utime(path)

    def update_phpmd_ruleset_treeview(self):
        builder = self._getGladeBuilder()
        treeview  = builder.get_object("treeviewPHPMDConfig")
        liststore = builder.get_object("liststorePHPMDConfig")
        liststore.clear()
        for directory, ruleset in self.get_all_phpmd_rulesets():
            rowIter = liststore.append()
            liststore.set_value(rowIter, 0, directory)
            liststore.set_value(rowIter, 1, ruleset)

    def get_phpmd_ruleset_file(self):
        path = os.path.expanduser("~/.local/share/gedit/addiks/hints/phpmd/rulesets.csv")
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if not os.path.exists(path):
            with open(path, 'w+'):
                os.utime(path)
        return path

    ### PHP-CODESNIFFER

    def show_phpcs_config(self):
        builder = self._getGladeBuilder()
        configWindow = builder.get_object("windowPHPCSConfig")
        configWindow.show_all()
        self.update_phpcs_ruleset_treeview()

    def add_phpcs_ruleset(self, ruleset, directory):
        path = self.get_phpcs_ruleset_file()
        with open(path, "a") as handle:
            writer = csv.writer(handle, delimiter=",")
            writer.writerow([directory, ruleset])

    def get_all_phpcs_rulesets(self):
        path = self.get_phpcs_ruleset_file()
        rulesets = []
        with open(path, "r") as handle:
            reader = csv.reader(handle, delimiter=",")
            for directory, ruleset in reader:
                rulesets.append([directory, ruleset])
        return rulesets

    def remove_phpcs_ruleset(self, needleRuleset, needleDirectory):
        path = self.get_phpcs_ruleset_file()
        rulesets = self.get_all_phpcs_rulesets()
        self.reset_phpcs_ruleset_file()
        for directory, ruleset in rulesets:
            if ruleset != needleRuleset or directory != needleDirectory:
                self.add_phpmd_ruleset(ruleset, directory)

    def reset_phpcs_ruleset_file(self):
        path = self.get_phpcs_ruleset_file()
        with open(path, 'w'):
            os.utime(path)

    def update_phpcs_ruleset_treeview(self):
        builder = self._getGladeBuilder()
        treeview  = builder.get_object("treeviewPHPCSConfig")
        liststore = builder.get_object("liststorePHPCSConfig")
        liststore.clear()
        for directory, ruleset in self.get_all_phpcs_rulesets():
            rowIter = liststore.append()
            liststore.set_value(rowIter, 0, directory)
            liststore.set_value(rowIter, 1, ruleset)

    def get_phpcs_ruleset_file(self):
        path = os.path.expanduser("~/.local/share/gedit/addiks/hints/phpcs/rulesets.csv")
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if not os.path.exists(path):
            with open(path, 'w+'):
                os.utime(path)
        return path

    ### SINGLETON

    __instance = None

    @staticmethod
    def get():
        if AddiksHintsApp.__instance == None:
            AddiksHintsApp.__instance = AddiksHintsApp()
        return AddiksHintsApp.__instance

    ### WINDOW / VIEW MANAGEMENT

    windows = []

    def get_all_windows(self):
        return self.windows

    def register_window(self, window):
        if window not in self.windows:
            self.windows.append(window)

    def unregister_window(self, window):
        if window in self.windows:
            self.windows.remove(window)

    def get_window_by_view(self, view):
        for window in self.windows:
            if view in window.window.get_views():
                return window

    views = []

    def get_all_views(self):
        return self.views

    def register_view(self, view):
        if view not in self.views:
            self.views.append(view)

    def unregister_view(self, view):
        if view in self.views:
            self.views.remove(view)

    def get_plugin_view_by_view(self, view):
        for pluginView in self.views:
            if pluginView.view == view:
                return pluginView

    ### PATHS

    def get_data_dir(self):
        return expanduser("~/.local/share/gedit/addiks/hints")

    ### GLADE

    def _getGladeHandler(self):
        if self._glade_handler == None:
            self.__initGlade()
        return self._glade_handler

    def _getGladeBuilder(self):
        if self._glade_builder == None:
            self.__initGlade()
        return self._glade_builder

    def __initGlade(self):
        self._glade_builder = Gtk.Builder()
        self._glade_builder.add_from_file(os.path.dirname(__file__)+"/hints.glade")
        self._glade_handler = GladeHandler(self, self._glade_builder)
        self._glade_builder.connect_signals(self._glade_handler)

    ### HINTS

    def get_hint_manager(self):
        if self._hint_manager == None:
            self._hint_manager = HintManager(self, self.get_data_dir)
        return self._hint_manager

    def get_hints_by_file(self, filePath, content=None):
        hint_manager = self.get_hint_manager()
        return hint_manager.get_hints_by_file(filePath, content)
