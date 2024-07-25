from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui, QtCompat
from dcc.ui import qsingletonwindow
from dcc.maya.libs import dagutils
from dcc.ui import qsignalblocker
from . import resources
from .models import qlayeritemmodel, qlayeritemfiltermodel, qstyledlayeritemdelegate

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


class QLayerExplorer(qsingletonwindow.QSingletonWindow):
    """
    Overload of `QSingletonWindow` that interfaces with display layers.
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
        self._callbackIds = om.MCallbackIdArray()
        self._dataChanges = QtCore.QItemSelection()

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QLayerExplorer, self).__setup_ui__(self, *args, **kwargs)

        # Initialize main window
        #
        self.setWindowTitle("|| Layer Explorer")
        self.setMinimumSize(QtCore.QSize(450, 450))

        # Initialize central widget
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        centralWidget = QtWidgets.QWidget()
        centralWidget.setObjectName('centralWidget')
        centralWidget.setLayout(centralLayout)

        self.setCentralWidget(centralWidget)

        # Initialize interop widget
        #
        self.interopLayout = QtWidgets.QHBoxLayout()
        self.interopLayout.setObjectName('interopLayout')
        self.interopLayout.setContentsMargins(0, 0, 0, 0)

        self.interopWidget = QtWidgets.QWidget()
        self.interopWidget.setObjectName('interopWidget')
        self.interopWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.interopWidget.setFixedHeight(24)
        self.interopWidget.setLayout(self.interopLayout)

        self.searchLineEdit = QtWidgets.QLineEdit()
        self.searchLineEdit.setObjectName('searchLineEdit')
        self.searchLineEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(True)

        self.moveLayerUpPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/moveLayerUp.png'), '')
        self.moveLayerUpPushButton.setObjectName('moveLayerUpPushButton')
        self.moveLayerUpPushButton.setSizePolicy(sizePolicy)

        self.moveLayerDownPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/moveLayerDown.png'), '')
        self.moveLayerDownPushButton.setObjectName('moveLayerDownPushButton')
        self.moveLayerDownPushButton.setSizePolicy(sizePolicy)

        self.createEmptyLayerPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/newEmptyLayer.png'), '')
        self.createEmptyLayerPushButton.setObjectName('createEmptyLayerPushButton')
        self.createEmptyLayerPushButton.setSizePolicy(sizePolicy)

        self.createLayerFromSelectedPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/newLayer.png'), '')
        self.createLayerFromSelectedPushButton.setObjectName('createLayerFromSelectedPushButton')
        self.createLayerFromSelectedPushButton.setSizePolicy(sizePolicy)

        self.interopLayout.addWidget(self.searchLineEdit)
        self.interopLayout.addWidget(self.moveLayerUpPushButton)
        self.interopLayout.addWidget(self.moveLayerDownPushButton)
        self.interopLayout.addWidget(self.createEmptyLayerPushButton)
        self.interopLayout.addWidget(self.createLayerFromSelectedPushButton)

        centralLayout.addWidget(self.interopWidget)

        # Initialize layer tree view
        #
        self.layerTreeView = QtWidgets.QTreeView()
        self.layerTreeView.setObjectName('layerTreeView')

        self.layerItemModel = qlayeritemmodel.QLayerItemModel(parent=self.layerTreeView)
        self.layerItemModel.setObjectName('layerItemModel')
        self.layerItemModel.dataChanged.connect(self.on_layerItemModel_dataChanged)

        self.layerItemFilterModel = qlayeritemfiltermodel.QLayerItemFilterModel(parent=self.layerTreeView)
        self.layerItemFilterModel.setObjectName('layerItemFilterModel')
        self.layerItemFilterModel.setSourceModel(self.layerItemModel)

        self.searchLineEdit.textEdited.connect(self.layerItemFilterModel.setFilterWildcard)

        self.layerTreeView.setModel(self.layerItemFilterModel)
        self.layerTreeView.setSortingEnabled(True)
        self.layerTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)

        self.styledLayerItemDelegate = qstyledlayeritemdelegate.QStyledLayerItemDelegate(parent=self.layerTreeView)
        self.styledLayerItemDelegate.setObjectName('styledLayerItemDelegate')

        self.layerTreeView.setItemDelegate(self.styledLayerItemDelegate)

        self.layerSelectionModel = self.layerTreeView.selectionModel()
        self.layerSelectionModel.setObjectName('layerSelectionModel')
        self.layerSelectionModel.selectionChanged.connect(self.on_layerSelectionModel_selectionChanged)

        centralLayout.addWidget(self.layerTreeView)

        # Initialize menu-bar
        #
        mainMenuBar = QtWidgets.QMenuBar(self)
        mainMenuBar.setObjectName('mainMenuBar')

        self.setMenuBar(mainMenuBar)

        # Initialize layers menu
        #
        self.layersMenu = mainMenuBar.addMenu('&Layers')
        self.layersMenu.setObjectName('layersMenu')

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

        self.alphabeticallyAction = QtWidgets.QAction('Alphabetically', parent=self.layersMenu)
        self.alphabeticallyAction.setObjectName('alphabeticallyAction')
        self.alphabeticallyAction.setCheckable(True)
        self.alphabeticallyAction.setChecked(True)
        self.alphabeticallyAction.triggered.connect(self.layerTreeView.setSortingEnabled)

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

        # Initialize options menu
        #
        self.optionsMenu = mainMenuBar.addMenu('&Options')
        self.optionsMenu.setObjectName('optionsMenu')

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
        self.helpMenu = mainMenuBar.addMenu('&Help')
        self.helpMenu.setObjectName('helpMenu')

        self.helpOnDisplayLayersAction = QtWidgets.QAction('Help on Display Layers', parent=self.helpMenu)
        self.helpOnDisplayLayersAction.setObjectName('helpOnDisplayLayersAction')

        self.helpMenu.addAction(self.helpOnDisplayLayersAction)
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

    # region Methods
    def addCallbacks(self):
        """
        Adds any callbacks required by this window.

        :rtype: None
        """

        # Add callbacks
        #
        hasCallbacks = len(self._callbackIds) > 0

        if not hasCallbacks:

            callbackId = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, onSceneChanged)
            self._callbackIds.append(callbackId)

            self.sceneChanged()

    def removeCallbacks(self):
        """
        Removes any callbacks created by this window.

        :rtype: None
        """

        # Remove callbacks
        #
        hasCallbacks = len(self._callbackIds) > 0

        if hasCallbacks:

            om.MMessage.removeCallbacks(self._callbackIds)
            self._callbackIds.clear()
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_chronologicallyAction_triggered(self, checked=False):
        """
        Slot method for the `chronologicallyAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.layerTreeView.setSortingEnabled(not checked)

    @QtCore.Slot(bool)
    def on_alphabeticallyAction_triggered(self, checked=False):
        """
        Slot method for the `alphabeticallyAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.layerTreeView.setSortingEnabled(checked)

    @QtCore.Slot(QtCore.QModelIndex, QtCore.QModelIndex, list)
    def on_layerItemModel_dataChanged(self, topLeft, bottomRight, roles=None):
        """
        Slot method for the `layerItemModel` widget's `dataChanged` signal.

        :type topLeft: QtCore.QModelIndex
        :type bottomRight: QtCore.QModelIndex
        :type roles: List[QtCore.Qt.ItemDataRole]
        :rtype: None
        """

        # Evaluate data role
        #
        role = roles[0] if len(roles) == 1 else None

        if role != QtCore.Qt.CheckStateRole:

            return

        # Evaluate selection count
        #
        itemSelection = self.layerSelectionModel.selection()
        sourceIndices = [self.layerItemFilterModel.mapToSource(index) for index in itemSelection.indexes()]

        column = topLeft.column()
        rowIndices = [index for index in sourceIndices if index.column() == column]
        numRows = len(rowIndices)

        if not (numRows >= 2):

            return

        # Propagate check state change to other rows
        #
        model = self.sender()
        checkState = topLeft.data(role=role)

        with qsignalblocker.QSignalBlocker(model):

            self._dataChanges = itemSelection  # Store current selection in case we need to recreate it later on!

            for index in rowIndices:

                model.setData(index, checkState, role=role)

    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_layerSelectionModel_selectionChanged(self, selected, deselected):
        """
        Slot method for the `layerSelectionModel` widget's `selectionChanged` signal.

        :type selected: QtCore.QItemSelection
        :type deselected: QtCore.QItemSelection
        :rtype: None
        """

        # Check if any data changes recently occurred
        # If so, then we need to recreate the original selection!
        #
        selectionLost = any([self._dataChanges.contains(index) for index in deselected.indexes()])

        if selectionLost:

            selected.merge(self._dataChanges, QtCore.QItemSelectionModel.Select)
            self._dataChanges.clear()

            with qsignalblocker.QSignalBlocker(self.layerSelectionModel):

                self.layerSelectionModel.select(selected, QtCore.QItemSelectionModel.Select)

        # Collect dag nodes from selected indices
        #
        indexes = [self.layerItemFilterModel.mapToSource(index) for index in selected.indexes() if index.column() == 0]
        nodes = list(map(self.layerItemModel.nodeFromIndex, indexes))

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
