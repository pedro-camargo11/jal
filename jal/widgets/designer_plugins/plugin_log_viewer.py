# Here reference goes from PYSIDE_DESIGNER_PLUGINS directory
from custom.log_viewer import LogViewer

from PySide6.QtGui import QIcon
from PySide6.QtDesigner import (QDesignerCustomWidgetInterface)


DOM_XML = """
<ui language='c++'>
    <widget class='LogViewer' name='logViewer'>
        <property name='geometry'>
            <rect>
                <x>0</x>
                <y>0</y>
                <width>300</width>
                <height>200</height>
            </rect>
        </property>
    </widget>
</ui>
"""


class LogViewerPlugin(QDesignerCustomWidgetInterface):
    def __init__(self):
        super().__init__()
        self._initialized = False

    def createWidget(self, parent):
        t = LogViewer(parent)
        return t

    def domXml(self):
        return DOM_XML

    def group(self):
        return ''

    def icon(self):
        return QIcon()

    def includeFile(self):
        return 'jal/widgets/custom/log_viewer.h'

    def initialize(self, form_editor):
        if self._initialized:
            return
        self._initialized = True

    def isContainer(self):
        return False

    def isInitialized(self):
        return self._initialized

    def name(self):
        return 'LogViewer'

    def toolTip(self):
        return 'Widget to display python logger messages in UI'

    def whatsThis(self):
        return self.toolTip()
