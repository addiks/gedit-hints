
import re
import os
import subprocess
import tempfile
from addiks_hints.helpers import *
from subprocess import Popen, PIPE
import xml.etree.ElementTree as ET

class HintManager:

    def __init__(self, plugin, data_dir):
        self._adapters = {
            'phplint': PHPLintAdapter(plugin, data_dir),
            'phpmd':   PHPMDAdapter(plugin, data_dir),
            'phpcs':   PHPCSAdapter(plugin, data_dir),
        }
        self._active_adapters = []

    def set_adapter_state(self, name, is_active):
        if is_active and name not in self._active_adapters:
            self._active_adapters.append(name)
        elif not is_active and name in self._active_adapters:
            self._active_adapters.remove(name)

    def get_all_adapter_names(self):
        names = []
        for adapterName in self._adapters:
            names.append(adapterName)
        return names

    def get_hints_by_file(self, filepath, content=None):
        hints = []

        suffix = "tmp"
        if "." in filepath:
            suffix = filepath.split(".")[-1]

        tempFile = tempfile.NamedTemporaryFile(suffix="."+suffix, delete=False)

        if content == None:
            tempFile.file.write(file_get_contents(filepath))
        else:
            tempFile.file.write(bytes(content, 'UTF-8'))

        tempFilePath = tempFile.name
        tempFile.close()

        for adapterName in self._adapters:
            if adapterName in self._active_adapters:
                adapter = self._adapters[adapterName]
                newHints = adapter.get_hints_by_file(tempFile.name, filepath)
                hints = hints + newHints

        os.remove(tempFilePath)

        hints = sorted(hints, key=lambda row: row[6])

        return hints


class PHPLintAdapter:

    def __init__(self, plugin, data_dir):
        pass

    def get_hints_by_file(self, filepath, filepathReal):
        hints = []

        if filepathReal[-4:]!='.php':
            return hints

        plugin_path = os.path.dirname(__file__)

        color = "#FF0000"

        try:
            sp = subprocess.Popen(["/usr/bin/env", "php", plugin_path+"/PHP-Parser/bin/php-parse.php", "-c", "--no-dump", filepath],
                stdin=PIPE, stdout=PIPE, stderr=PIPE
            )
            sp.wait()
            output, err = sp.communicate()
            output = output.decode()
            lines = output.split("\n")
            pattern = re.compile("(\=+\> )?(.*) from (\d+)\:(\d+) to (\d+)\:(\d+)")
            for line in lines:
                match = pattern.match(line)
                if match != None:
                    message, lineBegin, columnBegin, lineEnd, columnEnd = match.group(2, 3, 4, 5, 6)
                    lineBegin = int(lineBegin)-1
                    lineEnd = int(lineEnd)-1
                    columnBegin = int(columnBegin)-1
                    columnEnd = int(columnEnd)
                    hints.append([lineBegin, lineEnd, columnBegin, columnEnd, message, color, 300])
        except OSError as error:
            print(error)

        return hints

class PHPMDAdapter:

    def __init__(self, plugin, data_dir):
        self._data_dir = data_dir
        self._plugin = plugin

    def get_hints_by_file(self, filepath, filepathReal):
        hints = []

        if filepathReal[-4:]!='.php':
            return hints

        color = "#8F7811"

        for directory, rulesetFilepath in self._plugin.get_all_phpmd_rulesets():
            if filepathReal[0:len(directory)] == directory and os.path.exists(rulesetFilepath):
                try:
                    sp = subprocess.Popen(['phpmd', filepath, 'xml', rulesetFilepath],
                        stdin=PIPE, stdout=PIPE, stderr=PIPE
                    )
                    sp.wait()
                    output, err = sp.communicate()
                    output = output.decode()
                    rootXml = ET.fromstring(output)
                    for fileXml in rootXml:
                        for violationXml in fileXml:
                            lineBegin   = int(violationXml.attrib['beginline'])-1
                            lineEnd     = int(violationXml.attrib['beginline'])-1 #violationXml.attrib['endline']
                            columnBegin = 0
                            columnEnd   = 999
                            message     = violationXml.text.strip()
                            hints.append([lineBegin, lineEnd, columnBegin, columnEnd, message, color, 200])
                except OSError as error:
                    print(error)
        return hints


class PHPCSAdapter:

    def __init__(self, plugin, data_dir):
        self._data_dir = data_dir
        self._plugin = plugin

    def get_hints_by_file(self, filepath, filepathReal):
        hints = []

        color = "#A5A5A5"

        if filepathReal[-4:]!='.php':
            return hints

        for directory, rulesetFilepath in self._plugin.get_all_phpcs_rulesets():
            if filepathReal[0:len(directory)] == directory:
                try:
                    sp = subprocess.Popen(['phpcs', '--report=xml', '--standard='+rulesetFilepath, filepath],  # TODO
                        stdin=PIPE, stdout=PIPE, stderr=PIPE
                    )
                    sp.wait()
                    output, err = sp.communicate()
                    output = output.decode()
                    if len(output)>0:
                        rootXml = ET.fromstring(output)
                        for fileXml in rootXml:
                            for errorXml in fileXml:
                                lineBegin   = int(errorXml.attrib['line'])-1
                                lineEnd     = int(errorXml.attrib['line'])-1
                                columnBegin = int(errorXml.attrib['column'])-1
                                columnEnd   = int(errorXml.attrib['column'])
                                message     = errorXml.text.strip()

                                if columnBegin < 1:
                                    columnBegin = 1

                                hints.append([lineBegin, lineEnd, columnBegin, columnEnd, message, color, 100])
                except OSError as error:
                    print(error)
        return hints
