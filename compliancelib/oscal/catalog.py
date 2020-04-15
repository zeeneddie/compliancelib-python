#!/usr/bin/python
"""Class for reading OSCAL Control Catalog

Instantiate class with Security Catalog Reference ID (???????????).

Methods provide information about the Control Catalog.


This program is part of research for Homeland Open Security Technologies to better
understand how to map security controls to continuous monitoring.

Visit [??????] for the latest version.

LICENSE

ComplianceLib Catalog is a class for representing a NIST OSCAL security control catalog
Copyright (C) 2020  GovReady PBC.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Greg Elin (gregelin@govready.com)"
__version__ = "$Revision: 0.1 $"
__date__ = "$Date: 2020/04/20 12:30:00 $"
__copyright__ = "Copyright (c) 2020 GovReady PBC"
__license__ = "GNU General Public License"

import os
import json
import yaml
import re
from pathlib import Path
# import defusedxml.ElementTree as ET

CATALOG_PATH = os.path.join(os.path.dirname(__file__),'data','catalogs')


class Catalogs (object):
    """Represent list of catalogs"""
    def __init__(self):
        global CATALOG_PATH
        self.catalog_path = CATALOG_PATH
        # self.catalog = None
        self.index = self._build_index()

    def _list_catalog_files(self):
        return [
            'NIST_SP-800-53_rev4_catalog.json',
            'NIST_SP-800-53_rev5_catalog.json'
        ]

    def _load_catalog_json(self, file):
        from compliancelib import Catalog
        catalog = Catalog(file)
        return catalog._load_catalog_json()

    def _build_index(self):
        """Build a small catalog_index from metada"""
        index = []
        for src in self._list_catalog_files():
            catalog = self._load_catalog_json(src)
            index.append( { 'id': catalog['id'], 'file': src, 'metadata': catalog['metadata'] } )
        return index

    def list(self):
        catalog_titles = [item['metadata']['title'] for item in self.index ]
        return catalog_titles

class Catalog (object):
    """Represent a catalog"""
    def __init__(self, catalog_file='NIST_SP-800-53_rev4_catalog.json'):
        global CATALOG_PATH
        self.catalog_path = CATALOG_PATH
        self.catalog_file = catalog_file
        self.oscal = self._load_catalog_json()
        self.info = {}
        self.info['groups'] = self.get_groups()

    def _load_catalog_json(self):
        """Read catalog file - JSON"""
        catalog_file = os.path.join(self.catalog_path, self.catalog_file)
        # Does file exist?
        if not os.path.isfile(catalog_file):
            print("ERROR: {} does not exist".format(catalog_file))
            return False
        # Load file as json
        with open(catalog_file, 'r') as json_file:
            data = json.load(json_file)
            oscal = data['catalog']
        return oscal

    def find_dict_by_value(self, search_array, search_key, search_value):
        """Return the dictionary in an array of dictionaries with a key matching a value"""
        result_dict = next((sub for sub in search_array if sub[search_key] == search_value), None)
        return result_dict

    # def ids(self, search_collection):
    #     """Return the array of ids for a collection"""
    #     return [item['id'] for item in search_collection if 'id' in item]

    def get_groups(self):
        return self.oscal['groups']

    def get_group_ids(self):
        search_collection = self.get_groups()
        return [item['id'] for item in search_collection]

    def get_controls(self):
        controls = []
        for group in self.get_groups():
            controls += [control for control in group['controls']]
        return controls

    def get_control_ids(self):
        search_collection = self.get_controls()
        return [item['id'] for item in search_collection]

    def get_controls_all(self):
        controls = []
        for group in self.get_groups():
            for control in group['controls']:
                controls.append(control)
                if 'controls' in control:
                    controls += [control_e for control_e in control['controls']]
        return controls

    def get_controls_all_ids(self):
        search_collection = self.get_controls_all()
        return [item['id'] for item in search_collection]

    def get_control_by_id(self, control_id):
        """Return the dictionary in an array of dictionaries with a key matching a value"""
        search_array = self.get_controls_all()
        search_key = 'id'
        search_value = control_id
        result_dict = next((sub for sub in search_array if sub[search_key] == search_value), None)
        return result_dict

    def get_control_parameter_label_by_id(self, control, param_id):
        """Return value of a parameter of a control by id of parameter"""
        param = self.find_dict_by_value(control['parameters'], "id", param_id)
        return param['label']

    def get_control_prose_as_markdown(self, control_data, part_types={ "statement" }):
        # Concatenate the prose text of all of the 'parts' of this control
        # in Markdown. Filter out the parts that are not wanted.
        # Example 'statement'
        #   python3 -c "import compliancelib; cg = compliancelib.Catalog(); print(cg.get_control_prose_as_markdown(cg.get_control_by_id('ac-6')))"
        # Example 'guidance'
        #   python3 -c "import compliancelib; cg = compliancelib.Catalog(); print(cg.get_control_prose_as_markdown(cg.get_control_by_id('ac-6'), part_types={'guidance'}))"

        return self.format_part_as_markdown(control_data, filter_name=part_types)

    def format_part_as_markdown(self, part, indentation_level=-1, indentation_string="    ", filter_name=None, hide_first_label=True):
        # Format part, which is either a control or a part, as Markdown.

        # First construct the prose text of this part. If there is a
        # label, put it at the start.

        md = ""

        # If this part has a label (i.e. "a."), get the label.
        label = ""
        label_property = self.find_dict_by_value(part.get('properties', []), 'name', 'label')
        if label_property:
            label = label_property['value'] + " "
        # Hide first label to avoid showing control_id
        if indentation_level == -1 and hide_first_label:
            label = ""
        # Emit the label, if any.
        md += label

        # If it has a 'prose' key, then add that. The 'prose' is a string
        # that may contain Markdown formatting, so we don't touch it much
        # because we are supposed to produce markdown.
        #
        # OSCAL defines "markup-multiline" to use two escaped \n's to
        # denote paragraph boundaries, so we replace the literal "\n\n"
        # with two actual newline characters.
        if 'prose' in part:
            prose = part['prose']
            prose = prose.replace("\\n\\n", "\n\n")
            md += prose

        # If prose is multiple lines and if there is a label, then to be
        # valid Markdown, all lines after the first should be indented
        # the number of characters in the label (plus its space).
        if label:
            md = md.split("\n")
            for i in range(1, len(md)):
                md[i] = (" " * len(label)) + md[i]
            md = "\n".join(md)

        # Apply indentation. Each line of the prose should be indented
        # (not just the first line). Break the prose up into lines,
        # add the indentation at the start of each line, and then put
        # the lines back together again.
        # In Python, a string times an integer repeats it.
        md = "\n".join([
            (indentation_level*indentation_string) + line
            for line in md.split("\n")
        ])

        # If there was any prose text, add a paragraph boundary.
        if md != "":
            md += "\n\n"

        # If it has sub-parts, then emit those.
        if "parts" in part:
            for part in part["parts"]:
                # If filter_name is given, filter out the parts that don't have
                # one of the givne names.
                if filter_name and part.get('name') not in filter_name:
                    continue

                # Append this part.
                md += self.format_part_as_markdown(part,
                                                   indentation_string=indentation_string,
                                                   indentation_level=indentation_level+1)

        return md