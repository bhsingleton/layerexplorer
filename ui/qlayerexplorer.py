from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui, QtCompat
from dcc.ui import quicwindow
from dcc.maya.libs import dagutils
from . import resources
from .models import qlayeritemmodel, qstyledlayeritemdelegate

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def onSceneChanged(*args, **kwargs):
    """
    Callback method for any scene IO changes.

    :rtype: None
    """

    # Check if instance exists
    #
    instance = QLayerExplorer.getInstance()

    if instance is None:

        return

    # Evaluate if instance is still valid
    #
    if QtCompat.isValid(instance):

        instance.sceneChanged(*args, **kwargs)

    else:

        log.warning('Unable to process scene changed callback!')


class QLayerExplorer(quicwindow.QUicWindow):
    """
    Overload of `QUicWindow` that interfaces with display layers.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QLayerExplorer, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._callbackId = None

        # Declare public variables
        #
        self.layersMenu = None  # type: QtWidgets.QMenu
        self.createEmptyLayerAction = None
        self.createLayerFromSelectedAction = None
        self.selectObjectsInSelectedLayersAction = None
        self.removeSelectedObjectsFromSelectedLayersAction = None
        self.membershipAction = None
        self.attributesAction = None
        self.deleteSelectedLayersAction = None
        self.deleteUnusedLayersAction = None
        self.setAllLayersAction = None
        self.setSelectedLayersAction = None
        self.setOnlySelectedLayersAction = None
        self.chronologicallyAction = None
        self.alphabeticallyAction = None
        self.layerSortingActionGroup = None

        self.optionsMenu = None  # type: QtWidgets.QMenu
        self.makeNewLayersCurrentAction = None
        self.addNewObjectsToCurrentLayerAction = None
        self.autoOverridesAction = None
        self.showNamespaceAction = None

        self.helpMenu = None  # type: QtWidgets.QMenu
        self.helpOnDisplayLayersAction = None

        self.layerInteropWidget = None
        self.moveLayerUpPushButton = None
        self.moveLayerDownPushButton = None
        self.createEmptyLayerPushButton = None
        self.createLayerFromSelectedPushButton = None

        self.layerTreeView = None
        self.layerItemModel = None
        self.styledLayerItemDelegate = None
    # endregion

    # region Callbacks
    def sceneChanged(self, *args, **kwargs):
        """
        Notifies all tabs of a scene change.

        :key clientData: Any
        :rtype: None
        """

        self.layerItemModel.setLayerManagers(list(dagutils.iterNodes(om.MFn.kDisplayLayerManager)))
    # endregion

    # region Events
    def closeEvent(self, event):
        """
        Event method called after the window has been closed.

        :type event: QtGui.QCloseEvent
        :rtype: None
        """

        # Call parent method
        #
        super(QLayerExplorer, self).closeEvent(event)

        # Remove scene callback
        #
        om.MSceneMessage.removeCallback(self._callbackId)
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QLayerExplorer, self).postLoad(*args, **kwargs)

        # Initialize layer menu actions
        #
        self.createEmptyLayerAction = QtWidgets.QAction('Create Empty Layer', parent=self.layersMenu)
        self.createEmptyLayerAction.setObjectName('createEmptyLayerAction')

        self.createLayerFromSelectedAction = QtWidgets.QAction('Create Layer From Selected', parent=self.layersMenu)
        self.createLayerFromSelectedAction.setObjectName('createLayerFromSelectedAction')

        self.selectObjectsInSelectedLayersAction = QtWidgets.QAction('Select Objects in Selected Layers', parent=self.layersMenu)
        self.selectObjectsInSelectedLayersAction.setObjectName('selectObjectsInSelectedLayersAction')

        self.removeSelectedObjectsFromSelectedLayersAction = QtWidgets.QAction('Removed Selected Objects from Selected Layers', parent=self.layersMenu)
        self.removeSelectedObjectsFromSelectedLayersAction.setObjectName('removeSelectedObjectsFromSelectedLayersAction')

        self.membershipAction = QtWidgets.QAction('Membership', parent=self.layersMenu)
        self.membershipAction.setObjectName('membershipAction')

        self.attributesAction = QtWidgets.QAction('Attributes', parent=self.layersMenu)
        self.attributesAction.setObjectName('attributesAction')

        self.deleteSelectedLayersAction = QtWidgets.QAction('Delete Selected Layers', parent=self.layersMenu)
        self.deleteSelectedLayersAction.setObjectName('deleteSelectedLayersAction')

        self.deleteUnusedLayersAction = QtWidgets.QAction('Delete Unused Layers', parent=self.layersMenu)
        self.deleteUnusedLayersAction.setObjectName('deleteUnusedLayersAction')

        self.setAllLayersAction = QtWidgets.QAction('Set All Layers', parent=self.layersMenu)
        self.setAllLayersAction.setObjectName('setAllLayersAction')

        self.setSelectedLayersAction = QtWidgets.QAction('Set Selected Layers', parent=self.layersMenu)
        self.setSelectedLayersAction.setObjectName('setSelectedLayersAction')

        self.setOnlySelectedLayersAction = QtWidgets.QAction('Set Only Selected Layers', parent=self.layersMenu)
        self.setOnlySelectedLayersAction.setObjectName('setOnlySelectedLayersAction')

        self.chronologicallyAction = QtWidgets.QAction('Chronologically', parent=self.layersMenu)
        self.chronologicallyAction.setObjectName('chronologicallyAction')
        self.chronologicallyAction.setCheckable(True)
        self.chronologicallyAction.setChecked(True)

        self.alphabeticallyAction = QtWidgets.QAction('Alphabetically', parent=self.layersMenu)
        self.alphabeticallyAction.setObjectName('alphabeticallyAction')
        self.alphabeticallyAction.setCheckable(True)

        self.layerSortingActionGroup = QtWidgets.QActionGroup(self.layersMenu)
        self.layerSortingActionGroup.setObjectName('layerSortingActionGroup')
        self.layerSortingActionGroup.addAction(self.chronologicallyAction)
        self.layerSortingActionGroup.addAction(self.alphabeticallyAction)
        self.layerSortingActionGroup.setExclusive(True)

        self.layersMenu.addActions([self.createEmptyLayerAction, self.createLayerFromSelectedAction])
        self.layersMenu.addSeparator()
        self.layersMenu.addActions([self.selectObjectsInSelectedLayersAction, self.removeSelectedObjectsFromSelectedLayersAction])
        self.layersMenu.addSeparator()
        self.layersMenu.addActions([self.membershipAction, self.attributesAction])
        self.layersMenu.addSeparator()
        self.layersMenu.addActions([self.deleteSelectedLayersAction, self.deleteUnusedLayersAction])
        self.layersMenu.addSeparator()
        self.layersMenu.addActions([self.setAllLayersAction, self.setSelectedLayersAction, self.setOnlySelectedLayersAction])
        self.layersMenu.addSeparator()
        self.layersMenu.addActions([self.chronologicallyAction, self.alphabeticallyAction])

        # Initialize options menu actions
        #
        self.makeNewLayersCurrentAction = QtWidgets.QAction('Make New Layers Current', parent=self.optionsMenu)
        self.makeNewLayersCurrentAction.setObjectName('makeNewLayersCurrentAction')
        self.makeNewLayersCurrentAction.setCheckable(True)

        self.addNewObjectsToCurrentLayerAction = QtWidgets.QAction('Add New Objects to Current Layer', parent=self.optionsMenu)
        self.addNewObjectsToCurrentLayerAction.setObjectName('addNewObjectsToCurrentLayerAction')
        self.addNewObjectsToCurrentLayerAction.setCheckable(True)

        self.autoOverridesAction = QtWidgets.QAction('Auto Overrides', parent=self.optionsMenu)
        self.autoOverridesAction.setObjectName('autoOverridesAction')
        self.autoOverridesAction.setCheckable(True)

        self.showNamespaceAction = QtWidgets.QAction('Show Namespace', parent=self.optionsMenu)
        self.showNamespaceAction.setObjectName('showNamespaceAction')
        self.showNamespaceAction.setCheckable(True)

        self.optionsMenu.addActions([self.makeNewLayersCurrentAction, self.addNewObjectsToCurrentLayerAction, self.autoOverridesAction, self.showNamespaceAction])

        # Initialize help menu actions
        #
        self.helpOnDisplayLayersAction = QtWidgets.QAction('Help on Display Layers', parent=self.helpMenu)
        self.helpOnDisplayLayersAction.setObjectName('helpOnDisplayLayersAction')

        self.helpMenu.addAction(self.helpOnDisplayLayersAction)

        # Initialize layer item model
        #
        self.layerItemModel = qlayeritemmodel.QLayerItemModel(parent=self.layerTreeView)
        self.layerItemModel.setObjectName('layerItemModel')

        self.layerTreeView.setModel(self.layerItemModel)

        self.styledLayerItemDelegate = qstyledlayeritemdelegate.QStyledLayerItemDelegate(parent=self.layerTreeView)
        self.layerTreeView.setItemDelegate(self.styledLayerItemDelegate)

        self.layerTreeView.selectionModel().selectionChanged.connect(self.on_layerSelectionModel_selectionChanged)

        # Register scene change callback
        #
        self._callbackId = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, onSceneChanged)
        self.sceneChanged()

    # endregion

    # region Slots
    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_layerSelectionModel_selectionChanged(self, selected, deselected):
        """
        Slot method for the `layerTreeView` widget's `selectionChanged` signal.

        :type selected: QtCore.QItemSelection
        :type deselected: QtCore.QItemSelection
        :rtype: None
        """

        # Collect dag nodes
        #
        nodes = [self.layerItemModel.nodeFromIndex(index) for index in selected.indexes() if index.column() == 0]
        selectionList = dagutils.createSelectionList(nodes)

        # Evaluate keyboard modifiers
        #
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        shiftPressed = QtCore.Qt.ShiftModifier & modifiers
        controlPressed = QtCore.Qt.ControlModifier & modifiers

        if shiftPressed or controlPressed:

            selectionList.merge(om.MGlobal.getActiveSelectionList())

        # Update active selection
        #
        om.MGlobal.setActiveSelectionList(selectionList)
    # endregion
