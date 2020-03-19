# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
This hook will submit the publish tree to the "farm".
"""

############################################################################
# Warning!
# Please note that this code is provided as is. It is meant only as a proof
# of concept and does not aim to handle all the issues that might crop up
# during farm submission.

import os

import sgtk
from tank_vendor import yaml


class FarmSubmission(sgtk.get_hook_baseclass()):

    _SUBMIT_TO_FARM = "Submit to Farm"

    def post_publish(self, tree):
        """
        This hook method is invoked after the publishing phase.

        :param tree: The tree of items and tasks that has just been published.
        :type tree: :ref:`publish-api-tree`
        """
        if not _is_on_local_computer():
            return
        if not self._has_render_submissions(tree):
            self.logger.info("No job was submitted to the farm.")
            return

        # Grab some information about the context Toolkit is running in so
        # we can initialize Toolkit properly on the farm.
        engine = sgtk.platform.current_engine()
        dcc_state = {
            "session_path": _get_session_path(),
            "toolkit": {
                "pipeline_configuration_id": engine.sgtk.configuration_id,
                "context": engine.context.to_dict(),
                "engine_instance_name": engine.instance_name,
                "app_instance_name": self.parent.instance_name
            }
        }

        self._submit_to_farm(dcc_state, tree)
        self.logger.info("Job has been submitted to the render farm.")

    def _has_render_submissions(self, tree):
        """
        :returns: ``True`` if one task is submitting something to the farm, ``False`` otherwise.
        """
        for item in tree:
            for task in item.tasks:
                if self._SUBMIT_TO_FARM in task.settings and task.settings[self._SUBMIT_TO_FARM].value:
                    return True
        return False

    def _submit_to_farm(self, dcc_state, tree):
        """
        Submits the job to the render farm.

        :param dict dcc_state: Information about the DCC and Toolkit.
        :param tree: The tree of items and tasks that has just been published.
        :type tree: :ref:`publish-api-tree`
        """
        # TODO: You are the render farm experts. We'll just mock the submission
        # here.

        submission_folder = "/var/tmp/webinar"
        if not os.path.exists(submission_folder):
            os.makedirs(submission_folder)

        tree.save_file(
            os.path.join(submission_folder, "publish2_tree.txt")
        )

        with open(
            os.path.join(submission_folder, "dcc_state.txt"), "wt"
        ) as f:
            # Make sure you call safe_dump, as accentuated characters
            # might not get encoded properly otherwise.
            yaml.safe_dump(dcc_state, f)

        self.logger.info(
            "Publishing context and state has been saved on disk for farm rendering.",
            extra={
                "action_show_folder": {
                    "path": submission_folder
                }
            }
        )


def _is_on_local_computer():
    """
    :returns: ``True`` if on the render farm, ``False`` otherwise.
    """
    # Here this is synonymous with being in batch mode. Your mileage may vary.
    try:
        import maya.cmds
    except ImportError:
        pass
    else:
        return not maya.cmds.about(batch=True)

    # TODO: You can support for other DCCs here by trying to import them
    # one after another to figure out if you're in batch mode in those.
    raise NotImplementedError("%s is not supported." % sgtk.platform.current_engine().name)


def _get_session_path():
    """
    :returns: Path to the current session.
    """
    try:
        import maya.cmds as cmds
    except ImportError:
        pass
    else:
        path = cmds.file(query=True, sn=True)

        if isinstance(path, unicode):
            path = path.encode("utf-8")

        return path

    # TODO: You can support for other DCCs here by trying to import them
    # one after another to find the current scene name.
    raise NotImplementedError("%s is not supported." % sgtk.platform.current_engine().name)
