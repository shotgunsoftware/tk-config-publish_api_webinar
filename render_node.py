# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

############################################################################
# Warning!
# Please note that this code is provided as is. It is meant only as a proof
# of concept and does not aim to handle all the issues that might crop up
# during farm submission.

from __future__ import print_function

import os
import sys
from tank_vendor import yaml

# For some environments, like mayapy, we'll have to initialize the
# environment.
try:
    import maya.standalone
except ImportError:
    pass
else:
    # Some stuff mandated by Maya on startup of the Python interpreter.
    maya.standalone.initialize(name="python")


def get_parameters():
    # Read dcc state information from disk
    dcc_state_file = sys.argv[1]
    with open(dcc_state_file, "rt") as f:
        dcc_state = yaml.safe_load(f)

    # Extract the published file path.
    publish_tree_file = sys.argv[2]

    # Create the context object and figure out in which one we'll publishing
    # to.
    import sgtk
    context = sgtk.Context.from_dict(
        None, dcc_state["toolkit"]["context"]
    )
    context_entity = context.task or context.entity or context.project

    return (
        dcc_state["session_path"],
        dcc_state["toolkit"]["pipeline_configuration_id"],
        context_entity,
        dcc_state["toolkit"]["app_instance_name"],
        dcc_state["toolkit"]["engine_instance_name"],
        publish_tree_file
    )


def bootstrap_toolkit(configuration_id, context, engine_instance_name):
    """
    Syncs the path cache and starts Toolkit.

    The method expects SHOTGUN_HOST, SHOTGUN_SCRIPT_NAME and
    SHOTGUN_SCRIPT_KEY to be set to authenticate with Shotgun. If not,
    it will fail.
    """
    # When writing bootstrap scripts, always make sure to locally import
    # Toolkit. This will ensure you are using the right copy of the
    # module after bootstrapping, which will swap the cached copy of
    # Toolkit in sys.module, but can't update the references you have
    # to it.
    import sgtk

    # Set up logging.
    sgtk.LogManager().initialize_base_file_handler("tk-batch-rendering")

    # Never hard code credentials in your scripts.
    user = sgtk.authentication.ShotgunAuthenticator().create_script_user(
        os.environ["SHOTGUN_SCRIPT_NAME"],
        os.environ["SHOTGUN_SCRIPT_KEY"],
        os.environ["SHOTGUN_HOST"]
    )

    # Set the right pipeline configuration.
    tk_manager = sgtk.bootstrap.ToolkitManager(user)
    tk_manager.plugin_id = "basic.batch"
    tk_manager.pipeline_configuration = configuration_id

    # Sync the path cache before the engine starts. The engine validates the templates
    # when it starts so path cache has to be already synced.
    tk_manager.pre_engine_start_callback = lambda ctx: ctx.sgtk.synchronize_filesystem_structure()

    # Start the engine, we're done!
    return tk_manager.bootstrap_engine(engine_instance_name, context)


def load_scene(session_path, engine):
    # Load the scene
    try:
        import maya.cmds
    except ImportError:
        pass
    else:
        maya.cmds.file(new=True, force=True)
        maya.cmds.file(session_path, open=True, force=True)
        return

    raise NotImplementedError("Render farm script does not support the %s engine." % engine.name)


def publish_items(engine, app_instance_name, publish_tree_file):
    """
    Publishes the items that have been submitted to the farm.

    :param engine: The current :class:`sgtk.platform.Engine`.
    :param str app_instance_name: Name of the publish manager instance.
    :param str publish_tree_file: Path to the serialized publish tree.
    """

    # Create the Publish Manager, which will allow us to unserialize the publish tree
    # and do some publishing.
    publisher_app = engine.apps[app_instance_name]
    manager = publisher_app.create_publish_manager()

    # Load the publish tree
    manager.load(publish_tree_file)

    def generator(tree):
        """
        Yields tasks that have the "Submit to Farm" setting set to True.
        """
        for item in tree:
            for task in item.tasks:
                if "Submit to Farm" in task.settings and task.settings["Submit to Farm"].value is True:
                    yield task

    # Publish tasks that have been submitted to the farm.
    manager.publish(generator(manager.tree))
    manager.finalize(generator(manager.tree))


def print_title(text):
    print()
    print(len(text) * "=")
    print(text)
    print(len(text) * "=")


def main():
    print_title("Retrieving render settings")
    (
        session_path, configuration_id, context, app_name,
        engine_name, publish_tree_file
    ) = get_parameters()

    print_title("Starting engine")
    engine = bootstrap_toolkit(configuration_id, context, engine_name)

    print_title("Loading scene")
    load_scene(session_path, engine)

    print_title("Rendering and publishing")
    publish_items(engine, app_name, publish_tree_file)


if __name__ == "__main__":
    main()
