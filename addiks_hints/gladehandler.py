# Copyright (C) 2015 Gerrit Addiks <gerrit@addiks.net>
# https://github.com/addiks/gedit-window-management
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

from gi.repository import Gtk

class GladeHandler:

    def __init__(self, plugin, builder):
        self._plugin  = plugin
        self._builder = builder

    ### CONFIGURATION

    def onConfigPHPLintActivate(self, switch, userData=None):
        builder = self._builder
        switch = builder.get_object("switchPHPLint")
        active = switch.get_active()
        self._plugin.set_config("phplint", active)

    def onConfigPHPMDActivate(self, switch, userData=None):
        builder = self._builder
        switch = builder.get_object("switchPHPMD")
        active = switch.get_active()
        self._plugin.set_config("phpmd", active)

    def onPHPMDConfigureClicked(self, button):
        self._plugin.show_phpmd_config()

    def onPHPCSConfigureClicked(self, button):
        self._plugin.show_phpcs_config()

    ### PHPMD CONFIGURATION

    def onPHPMDAdd(self, button):
        builder = self._builder
        window  = builder.get_object("windowPHPMDConfig")

        dialog = Gtk.Dialog("Add ruleset for directory", window)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OK,     Gtk.ResponseType.OK)
        dialogBox = dialog.get_content_area()

        dialogGrid = Gtk.Grid()
        dialogBox.pack_end(dialogGrid, True, True, 0);

        labelDirectory = Gtk.Label("Directory that the ruleset applies for:")
        dialogGrid.attach(labelDirectory, 0, 0, 1, 1)

        userEntryDirectory = Gtk.Entry()
        dialogGrid.attach(userEntryDirectory, 1, 0, 1, 1)

        buttonBrowseDirectory = Gtk.Button("browse")
        buttonBrowseDirectory.userEntry = userEntryDirectory
        buttonBrowseDirectory.connect("button_press_event", self.__select_folder)
        dialogGrid.attach(buttonBrowseDirectory, 2, 0, 1, 1)

        labelRuleset = Gtk.Label("Path to PHP-MD ruleset:")
        dialogGrid.attach(labelRuleset, 0, 1, 1, 1)

        userEntryRuleset = Gtk.Entry()
        dialogGrid.attach(userEntryRuleset, 1, 1, 1, 1)

        buttonBrowseRuleset = Gtk.Button("browse")
        buttonBrowseRuleset.userEntry = userEntryRuleset
        buttonBrowseRuleset.connect("button_press_event", self.__select_file)
        dialogGrid.attach(buttonBrowseRuleset, 2, 1, 1, 1)

        dialog.show_all()
        response  = dialog.run()
        directory = userEntryDirectory.get_text()
        ruleset   = userEntryRuleset.get_text()
        dialog.destroy()

        if (response == Gtk.ResponseType.OK) and directory != '' and ruleset != '':
            self._plugin.add_phpmd_ruleset(ruleset, directory)
            self._plugin.update_phpmd_ruleset_treeview()

    def onPHPMDRemove(self, button):
        builder = self._builder

        treeview  = builder.get_object("treeviewPHPMDConfig")
        liststore = builder.get_object("liststorePHPMDConfig")

        selection = treeview.get_selection()

        store, selected_rows = selection.get_selected_rows()

        for path in selected_rows:
            treeIter = liststore.get_iter(path)
            directory = liststore.get_value(treeIter, 0)
            ruleset   = liststore.get_value(treeIter, 1)
            self._plugin.remove_phpmd_ruleset(ruleset, directory)
        self._plugin.update_phpmd_ruleset_treeview()

    ### PHPCS CONFIGURATION

    def onPHPCSAdd(self, button):
        builder = self._builder
        window  = builder.get_object("windowPHPCSConfig")

        dialog = Gtk.Dialog("Add ruleset for directory", window)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OK,     Gtk.ResponseType.OK)
        dialogBox = dialog.get_content_area()

        dialogGrid = Gtk.Grid()
        dialogBox.pack_end(dialogGrid, True, True, 0);

        labelDirectory = Gtk.Label("Directory that the ruleset applies for:")
        dialogGrid.attach(labelDirectory, 0, 0, 1, 1)

        userEntryDirectory = Gtk.Entry()
        dialogGrid.attach(userEntryDirectory, 1, 0, 1, 1)

        buttonBrowseDirectory = Gtk.Button("browse")
        buttonBrowseDirectory.userEntry = userEntryDirectory
        buttonBrowseDirectory.connect("button_press_event", self.__select_folder)
        dialogGrid.attach(buttonBrowseDirectory, 2, 0, 1, 1)

        labelRuleset = Gtk.Label("Path to PHP-CS ruleset or predefined standard:")
        dialogGrid.attach(labelRuleset, 0, 1, 1, 1)

        userEntryRuleset = Gtk.Entry()
        dialogGrid.attach(userEntryRuleset, 1, 1, 1, 1)

        buttonBrowseRuleset = Gtk.Button("browse")
        buttonBrowseRuleset.userEntry = userEntryRuleset
        buttonBrowseRuleset.connect("button_press_event", self.__select_file)
        dialogGrid.attach(buttonBrowseRuleset, 2, 1, 1, 1)

        description = "Known standards: PHPCS, PSR1, Zend, PSR2, MySource, Squiz and PEAR"
        descriptionLabel = Gtk.Label(description)
        dialogGrid.attach(descriptionLabel, 0, 2, 3, 1)

        dialog.show_all()
        response  = dialog.run()
        directory = userEntryDirectory.get_text()
        ruleset   = userEntryRuleset.get_text()
        dialog.destroy()

        if (response == Gtk.ResponseType.OK) and directory != '' and ruleset != '':
            self._plugin.add_phpcs_ruleset(ruleset, directory)
            self._plugin.update_phpcs_ruleset_treeview()

    def onPHPCSRemove(self, button):
        builder = self._builder

        treeview  = builder.get_object("treeviewPHPCSConfig")
        liststore = builder.get_object("liststorePHPCSConfig")

        selection = treeview.get_selection()

        store, selected_rows = selection.get_selected_rows()

        for path in selected_rows:
            treeIter = liststore.get_iter(path)
            directory = liststore.get_value(treeIter, 0)
            ruleset   = liststore.get_value(treeIter, 1)
            self._plugin.remove_phpcs_ruleset(ruleset, directory)
        self._plugin.update_phpcs_ruleset_treeview()

    ### HELPER

    def __select_folder(self, entry, event=None):
        return self.__select_file(entry, event, True)

    def __select_file(self, entry, event=None, isFolder=False):
        if event.button == 1:
            builder = self._builder

            window = entry.get_toplevel()

            if hasattr(entry, "userEntry"):
                entry = entry.userEntry

            action = Gtk.FileChooserAction.OPEN
            if isFolder:
                action = Gtk.FileChooserAction.SELECT_FOLDER

            title = "Choose file"
            if isFolder:
                title = "Choose folder"

            dialog = Gtk.FileChooserDialog(title, window, action)
            dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            dialog.add_button(Gtk.STOCK_OK,     Gtk.ResponseType.OK)

            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                entry.set_text(dialog.get_filename())
            dialog.destroy()
