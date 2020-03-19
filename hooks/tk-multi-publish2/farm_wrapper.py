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

import sgtk

try:
    from sgtk.platform.qt import QtCore, QtGui
except ImportError:
    CustomWidgetController = None
else:
    class FarmWrapperWidget(QtGui.QWidget):
        """
        This is the plugin's custom UI.

        It is meant to allow the user to send a task to the
        render farm or not.
        """
        def __init__(self, parent):
            super(FarmWrapperWidget, self).__init__(parent)

            # Create a nice simple layout with a checkbox in it.
            layout = QtGui.QFormLayout(self)
            self.setLayout(layout)

            label = QtGui.QLabel(
                "Clicking this checkbox will submit this task to the render farm.",
                self
            )
            label.setWordWrap(True)
            layout.addRow(label)

            self._check_box = QtGui.QCheckBox("Submit to Farm", self)
            self._check_box.setTristate(False)
            layout.addRow(self._check_box)

        @property
        def state(self):
            """
            :returns: ``True`` if the checkbox is checked, ``False`` otherwise.
            """
            return self._check_box.checkState() == QtCore.Qt.Checked

        @state.setter
        def state(self, is_checked):
            """
            Update the status of the checkbox.

            :param bool is_checked: When set to ``True``, the checkbox will be
                checked.
            """
            if is_checked:
                self._check_box.setCheckState(QtCore.Qt.Checked)
            else:
                self._check_box.setCheckState(QtCore.Qt.Unchecked)


class FarmWrapper(sgtk.get_hook_baseclass()):

    # User setting used to track if a task will be publish locally
    # or on the farm.
    _SUBMIT_TO_FARM = "Submit to Farm"

    # local_property that will be used to keep track of who submitted
    # a job and will be used when registering a publish.
    _JOB_SUBMITTER = "job_submitter"

    @property
    def name(self):
        """
        :returns: Name of the plugin.
        """
        return self._SUBMIT_TO_FARM

    @property
    def settings(self):
        """
        Exposes the list of settings for this hook.

        :returns: Dictionary of settings definitions for the app.
        """
        # Inherit the settings from the base publish plugin
        base_settings = super(FarmWrapper, self).settings or {}

        # settings specific to this class
        submit_to_farm_settings = {
            self._SUBMIT_TO_FARM: {
                "type": "bool",
                "default": True,
                "description": "When set to True, this task will not be "
                               "published inside the DCC and will be published "
                               "on the render farm instead."
            }
        }

        # merge the settings
        base_settings.update(submit_to_farm_settings)
        return base_settings

    def create_settings_widget(self, parent):
        """
        Creates the widget for our plugin.

        :param parent: Parent widget for the settings widget.
        :type parent: :class:`QtGui.QWidget`

        :returns: Custom widget for this plugin.
        :rtype: :class:`QtGui.QWidget`
        """
        return FarmWrapperWidget(parent)

    def get_ui_settings(self, widget):
        """
        Retrieves the state of the ui and returns a settings dictionary.

        :param parent: The settings widget returned by :meth:`create_settings_widget`
        :type parent: :class:`QtGui.QWidget`

        :returns: Dictionary of settings.
        """
        return {self._SUBMIT_TO_FARM: widget.state}

    def set_ui_settings(self, widget, settings):
        """
        Populates the UI with the settings for the plugin.

        :param parent: The settings widget returned by :meth:`create_settings_widget`
        :type parent: :class:`QtGui.QWidget`
        :param list(dict) settings: List of settings dictionaries, one for each
            item in the publisher's selection.

        :raises NotImplementeError: Raised if this implementation does not
            support multi-selection.
        """
        if len(settings) > 1:
            raise NotImplementedError()
        settings = settings[0]
        widget.state = settings[self._SUBMIT_TO_FARM]

    def publish(self, settings, item):
        """
        Publishes a given task to Shotgun if it's the right time.

        :param dict settings: Dictionary of :class:`PluginSetting` object for this task.
        :param item: The item currently being published.
        :type item: :class:`PublishItem` to publish.
        """
        if self._is_submitting_to_farm(settings):
            # The publish_user will be picked up by the publish method at publishing time
            # on the render farm.
            item.local_properties.publish_user = sgtk.util.get_current_user(
                self.parent.sgtk
            )
            # We're inside the DCC and we're currently publishing a task
            # that will go on the farm, so we do nothing.
            self.logger.info("This publish will be submitted to the farm.")
        else:
            super(FarmWrapper, self).publish(settings, item)

    def finalize(self, settings, item):
        """
        Finalizes a given task if it's the right time.

        :param dict settings: Dictionary of :class:`PluginSetting` object for this task.
        :param item: The item currently being published.
        :type item: :class:`PublishItem` to publish.
        """
        if self._is_submitting_to_farm(settings):
            # We're inside the DCC and we're currently finalizing a task
            # that will go on the farm, so we do nothing.
            pass
        else:
            super(FarmWrapper, self).finalize(settings, item)

    def _is_submitting_to_farm(self, settings):
        """
        Indicates if we're currently submitting something to the farm.

        :param dict settings: Dictionary of :class:`PluginSetting` object for this task.

        :returns: ``True`` if the action should be taken, ``False`` otherwise.
        """
        # If the Submit to Farm setting is turned set and we're on the a user's machine
        if settings[self._SUBMIT_TO_FARM].value and _is_on_local_computer():
            # We are indeed submitting to the farm.
            return True
        else:
            # We're not currently submitting to the farm.
            return False


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
