# -*- coding: UTF-8 -*-
__author__ = "Jaime Rivera <jaime.rvq@gmail.com>"
__copyright__ = "Copyright 2022, Jaime Rivera"
__credits__ = []
__license__ = "MIT License"


import concurrent.futures
import importlib
import inspect
import os
import time

from PySide2 import QtCore
import yaml

from all_nodes import constants
from all_nodes import utils


LOGGER = utils.get_logger(__name__)


# -------------------------------- NODE CLASSES -------------------------------- #
CLASSES_TO_SKIP = [
    "InputsGUI",
    "PreviewsGUI",
    "GeneralLogicNode",
    "Run",
    "GrabInputFromCtx",
    "SetOutputToCtx",
]  # Classes to skip when gathering all usable clases, populating widgets...


def register_node_lib(full_path):
    classes_dict = dict()

    node_lib_path = os.path.dirname(full_path)
    node_lib_name = os.path.basename(node_lib_path)
    module_filename = os.path.basename(full_path)
    module_name = os.path.splitext(module_filename)[0]
    icons_path = os.path.join(node_lib_path, "icons")
    styles_path = os.path.join(node_lib_path, "styles.yml")

    # ICONS - registering the icons so they can be found
    if not os.path.isdir(icons_path):
        LOGGER.warning(
            f"No icons folder available for {module_filename}, icons for this module should be saved at: {icons_path}"
        )
    if os.path.isdir(icons_path) and icons_path not in QtCore.QDir.searchPaths("icons"):
        QtCore.QDir.addSearchPath("icons", icons_path)
        LOGGER.debug("Registered path {} to 'icons'".format(icons_path))

    # STYLES
    node_styles = dict()
    if not os.path.isfile(styles_path):
        LOGGER.warning(
            f"No styles file available for {node_lib_name}, styles for this library should be saved at: {styles_path}"
        )
    else:
        with open(styles_path, "r") as stream:
            node_styles = yaml.safe_load(stream)

    # CLASSES SCANNING
    loaded_spec = importlib.util.spec_from_file_location(
        module_name,
        full_path,
    )
    loaded_module = importlib.util.module_from_spec(loaded_spec)
    loaded_spec.loader.exec_module(loaded_module)
    class_members = inspect.getmembers(loaded_module, inspect.isclass)
    if not class_members:
        return

    classes_dict[module_name] = dict()
    module_classes = list()
    class_counter = 0
    for name, cls in class_members:
        if name in CLASSES_TO_SKIP:
            continue
        # Icon for this class  # TODO Refactor this out
        default_icon = node_styles.get(module_name, dict()).get("default_icon")
        icon_path = "icons:nodes.png"
        if (
            hasattr(cls, "IS_CONTEXT") and cls.IS_CONTEXT
        ):  # TODO inheritance not working here?
            icon_path = "icons:cubes.png"
        if QtCore.QFile.exists(f"icons:{name}.png"):
            icon_path = f"icons:{name}.png"
        elif QtCore.QFile.exists(f"icons:{name}.svg"):
            icon_path = f"icons:{name}.svg"
        elif default_icon:
            if QtCore.QFile.exists("icons:" + default_icon + ".png"):
                icon_path = f"icons:{default_icon}.png"
            elif QtCore.QFile.exists("icons:" + default_icon + ".svg"):
                icon_path = f"icons:{default_icon}.svg"
        setattr(cls, "ICON_PATH", icon_path)

        # Class name and object
        setattr(cls, "FILEPATH", full_path)  # TODO not ideal?
        module_classes.append((name, cls))
        class_counter += 1

    classes_dict[module_name]["node_lib_path"] = node_lib_path
    classes_dict[module_name]["node_lib_name"] = node_lib_name
    classes_dict[module_name]["module_filename"] = module_filename
    classes_dict[module_name]["module_full_path"] = full_path
    classes_dict[module_name]["classes"] = module_classes

    classes_dict[module_name]["color"] = constants.DEFAULT_NODE_COLOR
    for module_style in node_styles:
        if module_style in module_name:
            classes_dict[module_name]["color"] = node_styles[module_style].get(
                "color", constants.DEFAULT_NODE_COLOR
            )
    LOGGER.debug(
        "Scanned {} for classes: found {}".format(
            os.path.basename(full_path), class_counter
        )
    )

    return classes_dict


def get_all_node_classes():
    # Paths to be examined
    libraries_path = os.getenv("ALL_NODES_LIB_PATH", "").split(os.pathsep)
    if not os.getenv("ALL_NODES_LIB_PATH"):
        root = os.path.abspath(__file__)
        root_dir_path = os.path.dirname(os.path.dirname(root))
        default_lib_path = os.path.join(root_dir_path, "lib", "base_node_lib")
        libraries_path = [default_lib_path]
        LOGGER.warning(
            "Env variable 'ALL_NODES_LIB_PATH' is not defined, "
            "will just scan for node libraries at default location: " + default_lib_path
        )

    # Iterate through paths
    all_py = list()
    for path in libraries_path:
        path = path.strip()
        if not path:
            continue
        elif not os.path.isdir(path):
            LOGGER.warning("Folder {} does not exist".format(path))
        for root, dirs, files in os.walk(path, topdown=True):
            for file in files:
                p = os.path.join(root, file)
                if p.endswith(".py") and "__init__" not in p:
                    all_py.append(p)

    all_classes_dict = dict()
    t1 = time.time()
    executor = concurrent.futures.ThreadPoolExecutor()
    with concurrent.futures.ThreadPoolExecutor(10) as executor:
        futures = [
            executor.submit(register_node_lib, full_path) for full_path in all_py
        ]
        for future in concurrent.futures.as_completed(futures):
            all_classes_dict.update(future.result())
    LOGGER.info(f"Total time scanning classes: {time.time()-t1} s.")

    # TODO examine classes to make sure there are no repeated names?
    return all_classes_dict


# -------------------------------- SCENES -------------------------------- #
def get_all_scenes_recursive(libraries_path=None, scenes_dict=None):
    if libraries_path is None:
        libraries_path = []
        if not os.getenv("ALL_NODES_LIB_PATH"):
            root = os.path.abspath(__file__)
            root_dir_path = os.path.dirname(os.path.dirname(root))
            default_lib_path = os.path.join(root_dir_path, "lib", "example_scene_lib")
            libraries_path.append(default_lib_path)
            LOGGER.warning(
                "Env variable 'ALL_NODES_LIB_PATH' is not defined, "
                "will just scan for scene libraries at default location: "
                + default_lib_path
            )
        else:
            all_paths = os.getenv("ALL_NODES_LIB_PATH").split(os.pathsep)
            for path in all_paths:
                path = path.strip()
                if path:
                    for elem in os.listdir(path):
                        full_path = os.path.join(path, elem)
                        if os.path.isdir(full_path) and "scene_lib" in full_path:
                            libraries_path.append(full_path)

    if scenes_dict is None:
        scenes_dict = dict()

    for path in libraries_path:
        folder_name = os.path.basename(os.path.normpath(path))
        if not os.path.exists(path):
            LOGGER.error(
                "Path {} registered to ALL_NODES_LIB_PATH does not exist!".format(path)
            )
        if not os.listdir(path):
            continue
        scenes_dict[folder_name] = list()
        for elem in os.listdir(path):
            full_path = os.path.join(path, elem)
            scene_name = os.path.splitext(elem)[0]
            if os.path.isfile(full_path) and full_path.endswith(".yml"):
                scenes_dict[folder_name].append((scene_name, full_path))
            elif os.path.isdir(full_path):
                new_dict = dict()
                scenes_dict[folder_name].append(new_dict)
                get_all_scenes_recursive([full_path], new_dict)

    return scenes_dict


def get_scene_from_alias(scenes_dict, alias):
    """
    Given just an alias (or more specifically filename) find full path to the yml file.
    Scans recursively.

    Args:
        scenes_dict (dict): dict with all the scenes and their paths
        alias (str): alias/filename to search for

    Returns: str, full path to the yml scene found
    """
    scene_path = None

    for key in scenes_dict:
        list_value = scenes_dict[key]
        for elem in list_value:
            if isinstance(elem, dict):
                scene_path = get_scene_from_alias(elem, alias)
                if scene_path is not None:
                    return scene_path
            else:
                for elem in list_value:
                    if isinstance(elem, dict):
                        scene_path = get_scene_from_alias(elem, alias)
                        if scene_path is not None:
                            return scene_path
                    elif isinstance(elem, tuple):
                        scene_name, full_path = elem
                        if scene_name == alias:
                            scene_path = full_path
                            return scene_path
    return scene_path


# -------------------------------- Class Registry -------------------------------- #
class ClassRegistry:
    _instance = None

    _all_classes = None
    _all_scenes = None

    _all_classes_simplified = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClassRegistry, cls).__new__(cls)
        return cls._instance

    def get_all_classes(cls):
        if cls._all_classes is None:
            LOGGER.info("Gathering all classes...")
            cls._all_classes = get_all_node_classes()

        return cls._all_classes

    def get_all_scenes(cls):
        if cls._all_scenes is None:
            cls._all_scenes = get_all_scenes_recursive()

        return cls._all_scenes

    def get_all_classes_simplified(cls):
        if cls._all_classes_simplified is None:
            cls._all_classes_simplified = list()
            all_classes = cls.get_all_classes()
            for m in sorted(all_classes):
                for name, class_object in all_classes[m]["classes"]:
                    cls._all_classes_simplified.append((name, class_object.ICON_PATH))

        return cls._all_classes_simplified

    def get_icon_path(cls, class_name_to_search):
        for class_name, icon_path in cls.get_all_classes_simplified():
            if class_name_to_search == class_name:
                return icon_path


CLASS_REGISTRY = ClassRegistry()
