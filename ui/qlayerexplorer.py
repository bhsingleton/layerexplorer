from maya import cmds as mc
from maya.api import OpenMaya as om
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
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


def onSelectionChanged(*args, **kwargs):
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

        instance.selectionChanged(*args, **kwargs)

    else:

        log.warning('Unable to process selection changed callback!')


class QLayerExplorer(MayaQWidgetDockableMixin, qsingletonwindow.QSingletonWindow):
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
        self.searchLineEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.searchLineEdit.setClearButtonEnabled(True)
        self.searchLineEdit.textEdited.connect(self.on_searchLineEdit_textChanged)

        self.moveLayerUpPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/moveLayerUp.png'), '')
        self.moveLayerUpPushButton.setObjectName('moveLayerUpPushButton')
        self.moveLayerUpPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.moveLayerUpPushButton.setMinimumWidth(24)
        self.moveLayerUpPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.moveLayerUpPushButton.clicked.connect(self.on_moveLayerUpPushButton_clicked)

        self.moveLayerDownPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/moveLayerDown.png'), '')
        self.moveLayerDownPushButton.setObjectName('moveLayerDownPushButton')
        self.moveLayerDownPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.moveLayerDownPushButton.setMinimumWidth(24)
        self.moveLayerDownPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.moveLayerDownPushButton.clicked.connect(self.on_moveLayerDownPushButton_clicked)

        self.createEmptyLayerPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/newEmptyLayer.png'), '')
        self.createEmptyLayerPushButton.setObjectName('createEmptyLayerPushButton')
        self.createEmptyLayerPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.createEmptyLayerPushButton.setMinimumWidth(24)
        self.createEmptyLayerPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.createEmptyLayerPushButton.clicked.connect(self.on_createEmptyLayerPushButton_clicked)

        self.createLayerFromSelectedPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/layerExplorer/icons/newLayer.png'), '')
        self.createLayerFromSelectedPushButton.setObjectName('createLayerFromSelectedPushButton')
        self.createLayerFromSelectedPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.createLayerFromSelectedPushButton.setMinimumWidth(24)
        self.createLayerFromSelectedPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.createLayerFromSelectedPushButton.clicked.connect(self.on_createLayerFromSelectedPushButton_clicked)

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
        self.layerTreeView.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.layerTreeView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.layerTreeView.setEditTriggers(QtWidgets.QAbstractItemView.SelectedClicked)
        self.layerTreeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.layerTreeView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.layerTreeView.setDropIndicatorShown(False)
        self.layerTreeView.setAlternatingRowColors(True)
        self.layerTreeView.setRootIsDecorated(True)
        self.layerTreeView.setUniformRowHeights(True)
        self.layerTreeView.setAnimated(False)
        self.layerTreeView.setExpandsOnDoubleClick(False)
        self.layerTreeView.header().setMinimumSectionSize(50)

        self.layerItemModel = qlayeritemmodel.QLayerItemModel(parent=self.layerTreeView)
        self.layerItemModel.setObjectName('layerItemModel')
        self.layerItemModel.dataChanged.connect(self.on_layerItemModel_dataChanged)

        self.layerItemFilterModel = qlayeritemfiltermodel.QLayerItemFilterModel(parent=self.layerTreeView)
        self.layerItemFilterModel.setObjectName('layerItemFilterModel')
        self.layerItemFilterModel.setSourceModel(self.layerItemModel)

        self.layerTreeView.setModel(self.layerItemFilterModel)
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
        self.createEmptyLayerAction.triggered.connect(self.on_createEmptyLayerAction_triggered)

        self.createLayerFromSelectedAction = QtWidgets.QAction('Create Layer From Selected', parent=self.layersMenu)
        self.createLayerFromSelectedAction.setObjectName('createLayerFromSelectedAction')
        self.createLayerFromSelectedAction.triggered.connect(self.on_createLayerFromSelectedAction_triggered)

        self.selectObjectsInSelectedLayersAction = QtWidgets.QAction('Select Objects in Selected Layers', parent=self.layersMenu)
        self.selectObjectsInSelectedLayersAction.setObjectName('selectObjectsInSelectedLayersAction')
        self.selectObjectsInSelectedLayersAction.triggered.connect(self.on_selectObjectsInSelectedLayersAction_triggered)

        self.removeSelectedObjectsFromSelectedLayersAction = QtWidgets.QAction('Removed Selected Objects from Selected Layers', parent=self.layersMenu)
        self.removeSelectedObjectsFromSelectedLayersAction.setObjectName('removeSelectedObjectsFromSelectedLayersAction')
        self.removeSelectedObjectsFromSelectedLayersAction.triggered.connect(self.on_removeSelectedObjectsFromSelectedLayersAction_triggered)

        self.membershipAction = QtWidgets.QAction('Membership', parent=self.layersMenu)
        self.membershipAction.setObjectName('membershipAction')
        self.membershipAction.triggered.connect(self.on_membershipAction_triggered)

        self.attributesAction = QtWidgets.QAction('Attributes', parent=self.layersMenu)
        self.attributesAction.setObjectName('attributesAction')
        self.attributesAction.triggered.connect(self.on_attributesAction_triggered)

        self.deleteSelectedLayersAction = QtWidgets.QAction('Delete Selected Layers', parent=self.layersMenu)
        self.deleteSelectedLayersAction.setObjectName('deleteSelectedLayersAction')
        self.deleteSelectedLayersAction.triggered.connect(self.on_deleteSelectedLayersAction_triggered)

        self.deleteUnusedLayersAction = QtWidgets.QAction('Delete Unused Layers', parent=self.layersMenu)
        self.deleteUnusedLayersAction.setObjectName('deleteUnusedLayersAction')
        self.deleteUnusedLayersAction.triggered.connect(self.on_deleteUnusedLayersAction_triggered)

        self.setAllLayersAction = QtWidgets.QAction('Set All Layers', parent=self.layersMenu)
        self.setAllLayersAction.setObjectName('setAllLayersAction')
        self.setAllLayersAction.triggered.connect(self.on_setAllLayersAction_triggered)

        self.setSelectedLayersAction = QtWidgets.QAction('Set Selected Layers', parent=self.layersMenu)
        self.setSelectedLayersAction.setObjectName('setSelectedLayersAction')
        self.setSelectedLayersAction.triggered.connect(self.on_setSelectedLayersAction_triggered)

        self.setOnlySelectedLayersAction = QtWidgets.QAction('Set Only Selected Layers', parent=self.layersMenu)
        self.setOnlySelectedLayersAction.setObjectName('setOnlySelectedLayersAction')
        self.setOnlySelectedLayersAction.triggered.connect(self.on_setOnlySelectedLayersAction_triggered)

        self.chronologicallyAction = QtWidgets.QAction('Chronologically', parent=self.layersMenu)
        self.chronologicallyAction.setObjectName('chronologicallyAction')
        self.chronologicallyAction.setCheckable(True)
        self.chronologicallyAction.triggered.connect(self.on_chronologicallyAction_triggered)

        self.alphabeticallyAction = QtWidgets.QAction('Alphabetically', parent=self.layersMenu)
        self.alphabeticallyAction.setObjectName('alphabeticallyAction')
        self.alphabeticallyAction.setCheckable(True)
        self.alphabeticallyAction.setChecked(True)
        self.alphabeticallyAction.triggered.connect(self.on_alphabeticallyAction_triggered)

        self.layerSortingActionGroup = QtWidgets.QActionGroup(self.layersMenu)
        self.layerSortingActionGroup.setObjectName('layerSortingActionGroup')
        self.layerSortingActionGroup.setExclusive(True)
        self.layerSortingActionGroup.addAction(self.chronologicallyAction)
        self.layerSortingActionGroup.addAction(self.alphabeticallyAction)

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
        self.makeNewLayersCurrentAction.triggered.connect(self.on_makeNewLayersCurrentAction_triggered)

        self.addNewObjectsToCurrentLayerAction = QtWidgets.QAction('Add New Objects to Current Layer', parent=self.optionsMenu)
        self.addNewObjectsToCurrentLayerAction.setObjectName('addNewObjectsToCurrentLayerAction')
        self.addNewObjectsToCurrentLayerAction.setCheckable(True)
        self.addNewObjectsToCurrentLayerAction.triggered.connect(self.on_addNewObjectsToCurrentLayerAction_triggered)

        self.autoOverridesAction = QtWidgets.QAction('Auto Overrides', parent=self.optionsMenu)
        self.autoOverridesAction.setObjectName('autoOverridesAction')
        self.autoOverridesAction.setCheckable(True)
        self.autoOverridesAction.triggered.connect(self.on_autoOverridesAction_triggered)

        self.showNamespaceAction = QtWidgets.QAction('Show Namespace', parent=self.optionsMenu)
        self.showNamespaceAction.setObjectName('showNamespaceAction')
        self.showNamespaceAction.setCheckable(True)
        self.showNamespaceAction.setChecked(True)
        self.showNamespaceAction.triggered.connect(self.on_showNamespaceAction_triggered)

        self.showNodesAction = QtWidgets.QAction('Show Nodes', parent=self.optionsMenu)
        self.showNodesAction.setObjectName('showNamespaceAction')
        self.showNodesAction.setCheckable(True)
        self.showNodesAction.setChecked(True)
        self.showNodesAction.triggered.connect(self.on_showNodesAction_triggered)

        self.optionsMenu.addActions(
            [
                self.makeNewLayersCurrentAction,
                self.addNewObjectsToCurrentLayerAction,
                self.autoOverridesAction,
                self.showNamespaceAction,
                self.showNodesAction
            ]
        )

        # Initialize help menu actions
        #
        self.helpMenu = mainMenuBar.addMenu('&Help')
        self.helpMenu.setObjectName('helpMenu')

        self.helpOnDisplayLayersAction = QtWidgets.QAction('Help on Display Layers', parent=self.helpMenu)
        self.helpOnDisplayLayersAction.setObjectName('helpOnDisplayLayersAction')
        self.helpOnDisplayLayersAction.triggered.connect(self.on_helpOnDisplayLayersAction_triggered)

        self.helpMenu.addAction(self.helpOnDisplayLayersAction)
    # endregion

    # region Callbacks
    def sceneChanged(self, *args, **kwargs):
        """
        Notifies layer item model of a scene change.

        :key clientData: Any
        :rtype: None
        """

        self.layerItemModel.setLayerManagers(list(dagutils.iterNodes(om.MFn.kDisplayLayerManager)))

    def selectionChanged(self, *args, **kwargs):
        """
        Notifies layer selection model of a selection change.

        :key clientData: Any
        :rtype: None
        """

        self.synchronizeSelection()
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

            callbackId = om.MEventMessage.addEventCallback('SelectionChanged', onSelectionChanged)
            self._callbackIds.append(callbackId)

        # Force scene update
        #
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

    def synchronizeSelection(self):
        """
        Synchronizes the layer selection model with the scene selection.

        :rtype: None
        """

        # Get associated item indices
        #
        selection = dagutils.getActiveSelection(apiType=om.MFn.kDependencyNode)
        items = QtCore.QItemSelection()

        for selectedNode in selection:

            sourceIndex = self.layerItemModel.indexFromNode(selectedNode)
            index = self.layerItemFilterModel.mapFromSource(sourceIndex)

            if index.isValid():

                items.select(index, index.siblingAtColumn(self.layerItemModel.columnCount() - 1))

            else:

                continue

        # Update layer selection model
        #
        with qsignalblocker.QSignalBlocker(self.layerSelectionModel):

            self.layerSelectionModel.select(items, QtCore.QItemSelectionModel.ClearAndSelect)

    # endregion

    # region Slots
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

    @QtCore.Slot(str)
    def on_searchLineEdit_textChanged(self, text):
        """
        Slot method for the `searchLineEdit` widget's `textChanged` signal.

        :type text: str
        :rtype: None
        """

        self.layerItemFilterModel.setFilterWildcard(text)

    @QtCore.Slot()
    def on_moveLayerUpPushButton_clicked(self):
        """
        Slot method for the `moveLayerUpPushButton` widget's `clicked` signal.

        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_moveLayerDownPushButton_clicked(self):
        """
        Slot method for the `moveLayerDownPushButton` widget's `clicked` signal.

        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_createEmptyLayerPushButton_clicked(self):
        """
        Slot method for the `createEmptyLayerPushButton` widget's `clicked` signal.

        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_createLayerFromSelectedPushButton_clicked(self):
        """
        Slot method for the `createLayerFromSelectedPushButton` widget's `clicked` signal.

        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_createEmptyLayerAction_triggered(self, checked=False):
        """
        Slot method for the `createEmptyLayerAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_createLayerFromSelectedAction_triggered(self, checked=False):
        """
        Slot method for the `createLayerFromSelectedAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_selectObjectsInSelectedLayersAction_triggered(self, checked=False):
        """
        Slot method for the `selectObjectsInSelectedLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_removeSelectedObjectsFromSelectedLayersAction_triggered(self, checked=False):
        """
        Slot method for the `removeSelectedObjectsFromSelectedLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_membershipAction_triggered(self, checked=False):
        """
        Slot method for the `membershipAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_attributesAction_triggered(self, checked=False):
        """
        Slot method for the `attributesAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_deleteSelectedLayersAction_triggered(self, checked=False):
        """
        Slot method for the `deleteSelectedLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_deleteUnusedLayersAction_triggered(self, checked=False):
        """
        Slot method for the `deleteUnusedLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_setAllLayersAction_triggered(self, checked=False):
        """
        Slot method for the `setAllLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_setSelectedLayersAction_triggered(self, checked=False):
        """
        Slot method for the `setSelectedLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot()
    def on_setOnlySelectedLayersAction_triggered(self, checked=False):
        """
        Slot method for the `setOnlySelectedLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

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

    @QtCore.Slot(bool)
    def on_makeNewLayersCurrentAction_triggered(self, checked=False):
        """
        Slot method for the `makeNewLayersCurrentAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_addNewObjectsToCurrentLayerAction_triggered(self, checked=False):
        """
        Slot method for the `addNewObjectsToCurrentLayerAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_autoOverridesAction_triggered(self, checked=False):
        """
        Slot method for the `autoOverridesAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_showNamespaceAction_triggered(self, checked=False):
        """
        Slot method for the `showNamespaceAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.layerItemModel.setShowNamespaces(checked)

    @QtCore.Slot(bool)
    def on_showNodesAction_triggered(self, checked=False):
        """
        Slot method for the `showNodesAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.layerItemFilterModel.setHideNodes(not checked)

    @QtCore.Slot(bool)
    def on_helpOnDisplayLayersAction_triggered(self, checked=False):
        """
        Slot method for the `helpOnDisplayLayersAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        mc.showHelp('DisplayLayer')
    # endregion
