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


from gi.repository import Gtk, GObject, Gedit, Pango
import os
from _thread import start_new_thread
from AddiksHintsApp import AddiksHintsApp

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
