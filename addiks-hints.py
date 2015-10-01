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

from gi.repository import GLib, Gtk, Gdk, GObject, Gedit, PeasGtk, Gio, GtkSource, GdkPixbuf, Notify, Pango
from addiks_hints.helpers import *
from inspect import getmodule
from addiks_hints.gladehandler import GladeHandler
from hintmanager import HintManager
import os
import os.path
import re
import csv
import random
import time
from time import sleep
import subprocess
import socket
from os.path import expanduser
from _thread import start_new_thread
import xml.etree.ElementTree as ElementTree

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
        home = expanduser("~")
        path = home + "/.local/share/gedit/addiks/hints/phpmd/rulesets.csv"
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
        home = expanduser("~")
        path = home + "/.local/share/gedit/addiks/hints/phpcs/rulesets.csv"
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
        home = expanduser("~")
        basedir = home + "/.local/share/gedit/addiks/hints"
        return basedir

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

class AddiksHintsView(GObject.Object, Gedit.ViewActivatable):
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        self.__drawArea = None
        self.__tags = {}
        GObject.Object.__init__(self)

    def do_activate(self):
        AddiksHintsApp.get().register_view(self)

        document = self.view.get_buffer()

        window = AddiksHintsApp.get().get_window_by_view(self.view)

        document = self.view.get_buffer()
        location = document.get_location()
        if location != None:
            tab = window.window.get_tab_from_location(location)

            viewFrame = tab.get_children()[0]
            
            scrolledWindow = viewFrame.get_child()

            self.__drawArea = scrolledWindow
            self.__drawArea.set_property("app-paintable", True)
            self.__drawArea.connect("size-allocate", self.on_drawingarea_size_allocate)
            self.__drawArea.connect_after("draw", self.on_drawingarea_draw)

        self.view.connect("query_tooltip", self._on_query_tooltip)
        self.view.set_has_tooltip(True)

        if document != None:
            document.connect("loaded", self.update_hints_threaded)
            document.connect("saved", self.update_hints_threaded)

    def do_deactivate(self):
        AddiksHintsApp.get().unregister_view(self)

    def on_drawingarea_size_allocate(self, widget, allocationRect, data=None):
        widget.queue_draw()

    def on_drawingarea_draw(self, widget, cairo, data=None):
        textView = self.view
        lineCount = textView.get_buffer().get_end_iter().get_line()
        
        viewHeight = widget.get_allocated_height()
        viewWidth  = widget.get_allocated_width()

        width = 3
        if hasattr(textView, 'addiks_hints'):
            for lineBegin, lineEnd, columnBegin, columnEnd, message, color, priority in textView.addiks_hints:
                lineEnd += 1

                top    = int((lineBegin / lineCount) * viewHeight)
                bottom = int((lineEnd   / lineCount) * viewHeight)
                height = bottom - top

                if height < 10:
                    height = 10

                red, green, blue = self.hexToIntColors(color)
                cairo.set_source_rgb(red/255, green/255, blue/255)
                cairo.rectangle(viewWidth-width, top, width, height)
                cairo.fill()

        return False

    def hexToIntColors(self, hexCode):
        redHex   = hexCode[1:3]
        greenHex = hexCode[3:5]
        blueHex  = hexCode[5:7]
        red   = int(redHex, 16)
        green = int(greenHex, 16)
        blue  = int(blueHex, 16)
        return (red, green, blue, )

    def _on_query_tooltip(self, textView, x, y, isKeyboardTooltip, tooltip):
        textBuffer = textView.get_buffer()
        if isKeyboardTooltip:
            offset   = textBuffer.property_cursor_position().get_value()
            textIter = textBuffer.get_iter_at_offset(offset)
        else:
            mouse_x, mouse_y = textView.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, x, y)
            textIter, trailing = textView.get_iter_at_position(mouse_x, mouse_y)
        hasTag = False
        for tagKey in self.__tags:
            tag = self.__tags[tagKey]
            if textIter.has_tag(tag):
                hasTag = True
                break
        if hasTag:
            tooltipMessages = []
            textIterLine = textIter.get_line()
            textIterColumn = textIter.get_line_offset()
            for lineBegin, lineEnd, columnBegin, columnEnd, message, color, priority in textView.addiks_hints:
                if (textIterLine >= lineBegin and textIterLine <= lineEnd and
                    textIterColumn >= columnBegin and textIterColumn <= columnEnd):
                    tooltipMessages.append(message)
            tooltip.set_markup("\n".join(tooltipMessages))
            return True
        else:
            return False

    def update_hints_threaded(self, document=None, foo=None):
        start_new_thread(self.update_hints, (document, foo, ))

    def update_hints(self, document=None, foo=None):
        if document == None:
            document = self.view.get_buffer()

        for tagKey in self.__tags:
            document.remove_tag(self.__tags[tagKey],  document.get_start_iter(), document.get_end_iter())
        
        self.view.addiks_hints = []

        if document.get_location() != None:
            filePath = document.get_location().get_path()

            content = document.get_text(document.get_start_iter(), document.get_end_iter(), False)

            hintLines = []
            for lineBegin, lineEnd, columnBegin, columnEnd, message, color, priority in AddiksHintsApp.get().get_hints_by_file(filePath, content):
                tag = self.get_hint_tag(color)

                lineBegin = int(lineBegin)
                lineEnd = int(lineEnd)
                columnBegin = int(columnBegin)
                columnEnd = int(columnEnd)

                self.view.addiks_hints.append([lineBegin, lineEnd, columnBegin, columnEnd, message, color, priority])

                #continue
                beginIter = document.get_end_iter().copy()
                beginIter.set_line(lineBegin)

                if beginIter.get_chars_in_line() > columnBegin:
                    beginIter.set_line_offset(columnBegin)
                else:
                    beginIter.forward_to_line_end()

                endIter = beginIter.copy()
                endIter.set_line(lineEnd)

                if endIter.get_chars_in_line() > columnEnd:
                    endIter.set_line_offset(columnEnd)
                else:
                    endIter.forward_to_line_end()

                document.apply_tag(tag, beginIter, endIter)
                for line in range(lineBegin, lineEnd):
                    hintLines.append(line)

        if self.__drawArea != None:
            self.__drawArea.queue_draw()

    def get_hint_tag(self, color):

        tagKey = "addiks_hint_" + color

        document = self.view.get_buffer()
        tagTable = document.get_tag_table()
        tag = tagTable.lookup(tagKey)

        if tag == None:
            red, green, blue = self.hexToIntColors(color)
            tag = document.create_tag(tagKey, underline=Pango.Underline.ERROR)
            # TODO: somehow set the underline-color
            #setattr(tag, "underline-rgba", color) 
            #tag.set_property("underline-rgba", color) 
            #print(tag.__gproperties__)
            #print(dir(tag))
            self.__tags[tagKey] = tag

        return tag

    
class AddiksHintsWindow(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        AddiksHintsApp.get().register_window(self)

        plugin_path = os.path.dirname(__file__)
        self._ui_manager = self.window.get_ui_manager()
        actions = [
            ['RepairFileAction',  "Try to repair the file",  "<Ctrl><Alt>R",   self.on_repair_file],
        ]

        self._actions = Gtk.ActionGroup("AddiksHintsMenuActions")
        for actionName, title, shortcut, callback in actions:
            self._actions.add_actions([(actionName, Gtk.STOCK_INFO, title, shortcut, "", callback),])

        self._ui_manager.insert_action_group(self._actions)
        self._ui_merge_id = self._ui_manager.add_ui_from_string(file_get_contents(plugin_path + "/menubar.xml"))
        self._ui_manager.ensure_update()

    def do_deactivate(self):
        AddiksHintsApp.get().unregister_window(self)
        
    def do_update_state(self):
        pass

    def get_accel_group(self):
        return self._ui_manager.get_accel_group()

    def on_repair_file(self, action, data=None, cycleLimit=5):

        view = self.window.get_active_view()

        document = view.get_buffer()

        patternStrings = [
            'Expected (\d+) space after ([A-Z_]+) keyword; (\d+) found',
            'Expected (\d+) space after closing parenthesis; found (\d+)',
            'Expected (\d+) space after (opening|closing) brace; (\d+) found',
            'Expected (\d+) spaces before opening brace; (\d+) found',
            'Expected (\d+) newline at end of file; (\d+) found',
            'Expected (\d+) newline after (opening|closing) brace; (\d+) found',
            '[A-Za-z ]+ indented incorrectly; expected( at least)? (\d+) spaces, found (\d+)',
            'Incorrect spacing between default value and equals sign for argument "$([a-zA-Z_]+)"; expected (\d+) but found (\d+)',
            'Incorrect spacing between argument "$([a-zA-Z_]+)" and equals sign; expected (\d+) but found (\d+)',
            'There must be one blank line after the last ([A-Z_]+) statement; (\d+) found;'
        ]

        patterns = {}
        for patternString in patternStrings:
            patterns[patternString] = re.compile(patternString)

        results = {}

        contentChanged = False

        for lineBegin, lineEnd, columnBegin, columnEnd, message, color, priority in reversed(view.addiks_hints):

            if lineBegin > document.get_line_count():
                lineBegin = document.get_line_count()
            elif lineBegin < 0:
                lineBegin = 0

            if lineEnd > document.get_line_count():
                lineEnd = document.get_line_count()
            elif lineEnd < 0:
                lineEnd = 0

            textIter = document.get_iter_at_line_offset(lineBegin, 0)
            textIter.forward_to_line_end()

            if columnBegin > textIter.get_line_offset():
                columnBegin = textIter.get_line_offset()-1
            if columnBegin < 0:
                columnBegin = 0
            
            textIter = document.get_iter_at_line_offset(lineEnd, 0)
            textIter.forward_to_line_end()

            if columnEnd > textIter.get_line_offset():
                columnEnd = textIter.get_line_offset()-1
            if columnEnd < 0:
                columnEnd = 0
            
            textIterLineBegin = document.get_iter_at_line_offset(lineBegin, 0)
            textIterBegin     = document.get_iter_at_line_offset(lineBegin, columnBegin)
            textIterEnd       = document.get_iter_at_line_offset(lineEnd, columnEnd)

            textIterLineBegin.forward_word_end()
            textIterLineBegin.backward_word_start()
            indentionChars = "".ljust(textIterLineBegin.get_line_offset(), " ")

            for patternKey in patterns:
                pattern = patterns[patternKey]
                results[patternKey] = pattern.match(message)

            if message == 'Opening brace of a class must be on the line after the definition':
                textIterBegin, textIterEnd = textIterBegin.forward_search("{", Gtk.TextSearchFlags.VISIBLE_ONLY)
                document.insert(textIterBegin, "\n", 1)
                contentChanged = True

            elif message == 'Opening brace should be on a new line':
                textIterBegin, textIterEnd = textIterBegin.forward_search("{", Gtk.TextSearchFlags.VISIBLE_ONLY)
                contentChanged = True
                document.insert(textIterBegin, "\n"+indentionChars, 1+len(indentionChars))

            elif results['Expected (\d+) space after ([A-Z_]+) keyword; (\d+) found'] != None:
                expected, token, actual = results['Expected (\d+) space after ([A-Z_]+) keyword; (\d+) found'].group(1, 2, 3)
                expected, actual = [int(expected), int(actual)]
                textIterBegin, textIterEnd = textIterBegin.forward_search(token, Gtk.TextSearchFlags.CASE_INSENSITIVE)
                contentChanged = True
                if expected > actual:
                    document.insert(textIterEnd, ''.ljust(expected - actual), expected - actual)
                else:
                    textIterNext = textIterEnd.copy()
                    textIterNext.forward_chars(actual - expected)
                    document.delete(textIterEnd, textIterNext)

            elif results['[A-Za-z ]+ indented incorrectly; expected( at least)? (\d+) spaces, found (\d+)'] != None:
                expected, actual = results['[A-Za-z ]+ indented incorrectly; expected( at least)? (\d+) spaces, found (\d+)'].group(2, 3)
                expected, actual = [int(expected), int(actual)]
                textIterBegin.set_line_offset(0)
                contentChanged = True
                if expected > actual:
                    document.insert(textIterBegin, ''.ljust(expected - actual), expected - actual)
                else:
                    textIterNext = textIterBegin.copy()
                    textIterNext.forward_chars(actual - expected)
                    document.delete(textIterBegin, textIterNext)

            elif results['Expected (\d+) space after (opening|closing) brace; (\d+) found'] != None:
                expected, actual, braceType = results['Expected (\d+) space after (opening|closing) brace; (\d+) found'].group(1, 3, 2)
                expected, actual = [int(expected), int(actual)]

                if braceType == 'closing':
                    textIterBegin, textIterEnd = textIterBegin.backward_search("}", Gtk.TextSearchFlags.VISIBLE_ONLY)
                    if expected > actual:
                        contentChanged = True
                        document.insert(textIterEnd, ''.ljust(expected - actual), expected - actual)
                    else:
                        textIterNext = textIterEnd.copy()
                        textIterNext.forward_chars(actual - expected)
                        contentChanged = True
                        document.delete(textIterEnd, textIterNext)

                else:
                    pass # TODO: implement
                
            elif results['Expected (\d+) newline at end of file; (\d+) found'] != None:
                expected, actual = results['Expected (\d+) newline at end of file; (\d+) found'].group(1, 2)
                expected = int(expected)
                actual   = int(actual)

            elif results['Expected (\d+) newline after (opening|closing) brace; (\d+) found'] != None:
                expected, actual, braceType = results['Expected (\d+) newline after (opening|closing) brace; (\d+) found'].group(1, 3, 2)
                expected, actual = [int(expected), int(actual)]

                if braceType == "opening":
                    textIterEnd
                    if expected > actual:
                        contentChanged = True
                        document.insert(textIterEnd, ''.ljust(expected - actual, "\n"), len(expected - actual))
                    
                    elif expected < actual:
                        textIterNext = textIterEnd.copy()
                        textIterNext.forward_chars(actual - expected)
                        contentChanged = True
                        document.delete(textIterEnd, textIterNext)
                else:
                    pass # TODO: implement

            elif results['Expected (\d+) space after closing parenthesis; found (\d+)'] != None:
                expected, actual = results['Expected (\d+) space after closing parenthesis; found (\d+)'].group(1, 2)
                expected, actual = [int(expected), int(actual)]

                if expected > actual:
                    contentChanged = True
                    document.insert(textIterEnd, ''.ljust(expected - actual), expected - actual)
                else:
                    textIterNext = textIterEnd.copy()
                    textIterNext.forward_chars(actual - expected)
                    contentChanged = True
                    document.delete(textIterEnd, textIterNext)

            elif results['Incorrect spacing between default value and equals sign for argument "$([a-zA-Z_]+)"; expected (\d+) but found (\d+)'] != None:
                variable, expected, actual = results['Incorrect spacing between default value and equals sign for argument "($[a-zA-Z_]+)"; expected (\d+) but found (\d+)'].group(1, 2)
                expected, actual = [int(expected), int(actual)]

            elif results['Incorrect spacing between argument "$([a-zA-Z_]+)" and equals sign; expected (\d+) but found (\d+)'] != None:
                variable, expected, actual = results['Incorrect spacing between argument "($[a-zA-Z_]+)" and equals sign; expected (\d+) but found (\d+)'].group(1, 2)
                expected, actual = [int(expected), int(actual)]

            elif results['Expected (\d+) spaces before opening brace; (\d+) found'] != None:
                expected, actual = results['Expected (\d+) spaces before opening brace; (\d+) found'].group(1, 2)
                expected, actual = [int(expected), int(actual)]

            elif results['There must be one blank line after the last ([A-Z_]+) statement; (\d+) found;'] != None:
                keyword, actual = results['There must be one blank line after the last ([A-Z_]+) statement; (\d+) found;'].group(1, 2)
                actual   = int(actual)

            elif message == 'The closing brace for the class must go on the next line after the body':
                pass # remove all empty lines just before line-begin

            elif message == 'Usage of ELSE IF is discouraged; use ELSEIF instead':
                contentChanged = True
                textIterNext = textIterBegin.copy()
                textIterNext.forward_chars(len("else if"))
                document.delete(textIterBegin, textIterNext)
                document.insert(textIterBegin, "elseif", len("elseif"))

            elif message == 'The static declaration must come after the visibility declaration':
                contentChanged = True
                textIterNext = textIterBegin.copy()
                textIterNext.forward_chars(len("static "))
                document.delete(textIterBegin, textIterNext)
                textIterDeclBegin, textIterDeclEnd = textIterBegin.forward_search(" ", Gtk.TextSearchFlags.CASE_INSENSITIVE)
                document.insert(textIterDeclEnd, "static ", len("static "))

            elif message == 'Whitespace found at end of line':
                
                textIter = document.get_iter_at_line_offset(lineBegin, 0)
                textIter.forward_to_line_end()
                
                textIterPrev = textIter.copy()
                textIterPrev.backward_char()

                while document.get_text(textIterPrev, textIter, False) == " ":
                    contentChanged = True
                    document.delete(textIterPrev, textIter)
                    
                    textIter = document.get_iter_at_line_offset(lineBegin, 0)
                    textIter.forward_to_line_end()
                    
                    textIterPrev = textIter.copy()
                    textIterPrev.backward_char()

            else:
                print([lineBegin, lineEnd, columnBegin, columnEnd, message])

        AddiksHintsApp.get().get_plugin_view_by_view(view).update_hints()

        #if contentChanged and cycleLimit > 0:
        #    self.on_repair_file(action, data, cycleLimit-1)

