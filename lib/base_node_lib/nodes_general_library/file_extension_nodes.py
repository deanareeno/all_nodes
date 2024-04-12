# -*- coding: UTF-8 -*-
__author__ = "Jaime Rivera <jaime.rvq@gmail.com>"
__copyright__ = "Copyright 2022, Jaime Rivera"
__credits__ = []
__license__ = "MIT License"


from all_nodes.constants import InputsGUI
from all_nodes.logic.logic_node import GeneralLogicNode
from all_nodes import utils


LOGGER = utils.get_logger(__name__)


class ImageFileExtensionSelect(GeneralLogicNode):
    NICE_NAME = "Image file extension select"

    INTERNALS_DICT = {
        "internal_str": {
            "type": str,
            "gui_type": InputsGUI.OPTION_INPUT,
            "options": [".png", ".exr", ".jpg"],
        },
    }

    OUTPUTS_DICT = {"out_str": {"type": str}}

    def run(self):
        self.set_output("out_str", self.get_attribute_value("internal_str"))


class TextFileExtensionSelect(GeneralLogicNode):
    NICE_NAME = "Text file extension select"

    INTERNALS_DICT = {
        "internal_str": {
            "type": str,
            "gui_type": InputsGUI.OPTION_INPUT,
            "options": [".txt", ".json", ".yml"],
        },
    }

    OUTPUTS_DICT = {"out_str": {"type": str}}

    def run(self):
        self.set_output("out_str", self.get_attribute_value("internal_str"))
