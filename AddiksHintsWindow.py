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
import re

from gi.repository import Gtk, GObject, Gedit

from AddiksHintsApp import AddiksHintsApp

class AddiksHintsWindow(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        AddiksHintsApp.get().register_window(self)

        plugin_path = os.path.dirname(__file__)

        if "get_ui_manager" in dir(self.window):# build menu for gedit 3.10 (global menu per window)
            self._ui_manager = self.window.get_ui_manager()
            actions = [
                ['RepairFileAction',  "Try to repair the file",  "<Ctrl><Alt>R",   self.on_repair_file],
            ]

            self._actions = Gtk.ActionGroup("AddiksHintsMenuActions")
            for actionName, title, shortcut, callback in actions:
                self._actions.add_actions([(actionName, Gtk.STOCK_INFO, title, shortcut, "", callback),])

            with open(plugin_path + "/menubar.xml") as menubarXmlFile:
                menubarXml = menubarXmlFile.read()

                self._ui_manager.insert_action_group(self._actions)
                self._ui_merge_id = self._ui_manager.add_ui_from_string(menubarXml)
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
