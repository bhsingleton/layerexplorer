from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui
from enum import IntEnum
from collections import defaultdict, deque
from dcc.maya.libs import dagutils, layerutils, plugutils

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ViewDetail(IntEnum):
    """
    Enum class of all available layer details.
    """

    NAME = 0
    FROZEN = 1
    PLAYBACK = 2


class QLayerItemModel(QtCore.QAbstractItemModel):
    """
    Overload of `QAbstractItemModel` that interfaces with display layers.
    """

    # region Dunderscores
    def __init__(self, **kwargs):
        """
        Private method called after a new instance has been created.

        :type parent: QtCore.QObject
        :rtype: None
        """

        # Call parent method
        #
        parent = kwargs.get('parent', None)
        super(QLayerItemModel, self).__init__(parent=parent)

        # Declare private variables
        #
        self._viewDetails = [ViewDetail.NAME, ViewDetail.FROZEN, ViewDetail.PLAYBACK]
        self._headerLabels = [detail.name.title().replace('_', ' ') for detail in self._viewDetails]
        self._uniformRowHeight = kwargs.get('uniformRowHeight', 24.0)
        self._showNamespaces = True
        self._layerManagers = deque()  # type: deque[int]
        self._displayLayers = defaultdict(deque)  # type: defaultdict[int, deque[int]]
        self._layerNodes = defaultdict(deque)  # type: defaultdict[int, deque[int]]
        self._internalIds = {}
    # endregion

    # region Mutators
    def layerManagers(self):
        """
        Returns the root layer managers.

        :rtype: deque[int]
        """

        return self._layerManagers

    def setLayerManagers(self, layerManagers):
        """
        Updates the root layer managers.

        :type layerManagers: List[Union[str, om.MObject, om.MObjectHandle]]
        :rtype: None
        """

        # Notify model reset
        #
        self.beginResetModel()

        # Reset internal trackers
        #
        self._layerManagers.clear()
        self._internalIds.clear()

        for layerManager in layerManagers:

            layerManagerHandle = dagutils.getMObjectHandle(layerManager)
            layerManagerHashCode = layerManagerHandle.hashCode()

            self._layerManagers.append(layerManagerHashCode)
            self._internalIds[layerManagerHashCode] = layerManagerHandle

        # Notify end of model reset
        #
        self.endResetModel()

    def viewDetails(self):
        """
        Returns the view details for this model.

        :rtype: List[ViewDetail]
        """

        return self._viewDetails

    def setViewDetails(self, viewDetails):
        """
        Updates the view details for this model.

        :type viewDetails: List[ViewDetail]
        :rtype: None
        """

        # Notify model reset
        #
        self.beginResetModel()

        # Reset internal trackers
        #
        self._viewDetails.clear()
        self._viewDetails.extend(viewDetails)

        self._headerLabels = [detail.name.title().replace('_', ' ') for detail in self._viewDetails]

        # Notify end of model reset
        #
        self.endResetModel()

    def headerLabels(self):
        """
        Returns the header labels for this model.

        :rtype: List[str]
        """

        return self._headerLabels

    def showNamespaces(self):
        """
        Returns the `showNamespaces` flag.

        :rtype: bool
        """

        return self._showNamespaces

    def setShowNamespaces(self, showNamespaces):
        """
        Updates the `showNamespaces` flag.

        :type showNamespaces: bool
        :rtype: None
        """

        self._showNamespaces = showNamespaces
    # endregion

    # region Methods
    def getDisplayLayers(self, layerManager):
        """
        Returns the display layers associated with the supplied layer manager.

        :type layerManager: om.MObject
        :rtype: deque[int]
        """

        # Get cached layers
        #
        layerManager = dagutils.getMObject(layerManager)
        layerManagerHandle = dagutils.getMObjectHandle(layerManager)
        layerManagerHashCode = layerManagerHandle.hashCode()

        displayLayers = self._displayLayers[layerManagerHashCode]
        numDisplayLayers = len(displayLayers)

        # Check if cache requires updating
        #
        displayLayerIdPlug = plugutils.findPlug(layerManager, 'displayLayerId')
        numConnectedElements = displayLayerIdPlug.numConnectedElements()

        if numDisplayLayers != numConnectedElements:

            displayLayers.clear()

            for i in range(numConnectedElements):

                displayLayerIdElement = displayLayerIdPlug.connectionByPhysicalIndex(i)
                displayLayer = displayLayerIdElement.destinations()[0].node()
                displayLayerHandle = dagutils.getMObjectHandle(displayLayer)
                displayLayerHashCode = displayLayerHandle.hashCode()

                displayLayers.append(displayLayerHashCode)
                self._internalIds[displayLayerHashCode] = displayLayerHandle

        return displayLayers

    def getLayerNodes(self, displayLayer):
        """
        Returns the nodes associated with the supplied display layer.

        :type displayLayer: om.MObject
        :rtype: List[om.MObjectHandle]
        """

        # Get cached layer nodes
        #
        displayLayer = dagutils.getMObject(displayLayer)
        displayLayerHandle = dagutils.getMObjectHandle(displayLayer)
        displayLayerHashCode = displayLayerHandle.hashCode()

        layerNodes = self._layerNodes[displayLayerHashCode]
        numLayerNodes = len(layerNodes)

        # Check if cache requires updating
        #
        drawInfoPlug = plugutils.findPlug(displayLayer, 'drawInfo')
        destinations = drawInfoPlug.destinations()

        numDestinations = len(destinations)

        if numLayerNodes != numDestinations:

            layerNodes.clear()

            for destination in destinations:

                layerNode = destination.node()
                layerNodeHandle = dagutils.getMObjectHandle(layerNode)
                layerNodeHashCode = layerNodeHandle.hashCode()

                layerNodes.append(layerNodeHashCode)
                self._internalIds[layerNodeHashCode] = layerNodeHandle

        return layerNodes

    def nodeFromIndex(self, index):
        """
        Returns the node associated with the supplied index.

        :type index: QtCore.QModelIndex
        :rtype: om.MObject
        """

        internalId = index.internalId()
        handle = self._internalIds.get(internalId, None)

        if isinstance(handle, om.MObjectHandle):

            return handle.object() if handle.isAlive() else om.MObject.kNullObj

        else:

            return om.MObject.kNullObj

    def indexFromNode(self, node):
        """
        Returns the index of the supplied node.

        :type node: om.MObject
        :rtype: QtCore.QModelIndex
        """

        # Evaluate supplied node
        #
        if node.isNull():

            return QtCore.QModelIndex()

        # Evaluate node type
        #
        if node.hasFn(om.MFn.kDagNode):

            displayLayer = layerutils.getLayerFromNode(node)
            layerNodes = self.getLayerNodes(displayLayer)
            layerNodeHashCode = dagutils.getMObjectHandle(node).hashCode()
            row = layerNodes.index(layerNodeHashCode)

            return self.createIndex(row, 0, id=layerNodeHashCode)

        elif node.hasFn(om.MFn.kDisplayLayer):

            layerManager = layerutils.getManagerFromLayer(node)
            displayLayers = self.getDisplayLayers(layerManager)
            displayLayerHashCode = dagutils.getMObjectHandle(node).hashCode()
            row = displayLayers.index(displayLayerHashCode)

            return self.createIndex(row, 0, id=displayLayerHashCode)

        elif node.hasFn(om.MFn.kDisplayLayerManager):

            layerManagerHashCode = dagutils.getMObjectHandle(node).hashCode()
            row = self._layerManagers.index(layerManagerHashCode)

            return self.createIndex(row, 0, id=layerManagerHashCode)

        else:

            return QtCore.QModelIndex()

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """
        Returns the index of the item in the model specified by the given row, column and parent index.

        :type row: int
        :type column: int
        :type parent: QtCore.QModelIndex
        :rtype: QtCore.QModelIndex
        """

        # Check if this is a top-level index
        #
        isTopLevel = not parent.isValid()

        if isTopLevel:

            # Check if layer manager is in range
            #
            maxRow = len(self._layerManagers)

            if 0 <= row < maxRow:

                return self.createIndex(row, column, id=self._layerManagers[row])

            else:

                return QtCore.QModelIndex()

        else:

            # Evaluate associated node
            #
            node = self.nodeFromIndex(parent)

            if node.isNull():

                return QtCore.QModelIndex()

            # Evaluate node type
            #
            if node.hasFn(om.MFn.kDisplayLayerManager):

                # Check if row is in range
                #
                displayLayers = self.getDisplayLayers(node)
                maxRow = len(displayLayers)

                if 0 <= row < maxRow:

                    return self.createIndex(row, column, id=displayLayers[row])

                else:

                    return QtCore.QModelIndex()

            elif node.hasFn(om.MFn.kDisplayLayer):

                # Check if row is in range
                #
                layerNodes = self.getLayerNodes(node)
                maxRow = len(layerNodes)

                if 0 <= row < maxRow:

                    return self.createIndex(row, column, id=layerNodes[row])

                else:

                    return QtCore.QModelIndex()

            else:

                return QtCore.QModelIndex()

    def parent(self, *args):
        """
        Returns the parent of the model item with the given index.
        If the item has no parent, an invalid QModelIndex is returned.

        :type index: QtCore.QModelIndex
        :rtype: QtCore.QModelIndex
        """

        # Evaluate supplied arguments
        #
        numArgs = len(args)

        if numArgs == 0:

            return super(QtCore.QAbstractItemModel, self).parent()

        # Evaluate associated node
        #
        index = args[0]
        node = self.nodeFromIndex(index)

        if node.isNull():

            return QtCore.QModelIndex()

        # Evaluate node type
        #
        if node.hasFn(om.MFn.kDagNode):

            layer = layerutils.getLayerFromNode(node)
            return self.indexFromNode(layer)

        elif node.hasFn(om.MFn.kDisplayLayer):

            manager = layerutils.getManagerFromLayer(node)
            return self.indexFromNode(manager)

        else:

            return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        Returns the number of rows under the given parent.

        :type parent: QtCore.QModelIndex
        :rtype: int
        """

        # Check if this is a top-level index
        #
        isTopLevel = not parent.isValid()

        if isTopLevel:

            return len(self._layerManagers)

        # Evaluate associated node
        #
        node = self.nodeFromIndex(parent)

        if node.isNull():

            return 0

        # Evaluate node type
        #
        if node.hasFn(om.MFn.kDisplayLayerManager):

            displayLayers = self.getDisplayLayers(node)
            numDisplayLayers = len(displayLayers)

            return numDisplayLayers

        elif node.hasFn(om.MFn.kDisplayLayer):

            layerNodes = self.getLayerNodes(node)
            numLayerNodes = len(layerNodes)

            return numLayerNodes

        else:

            return 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        Returns the number of columns under the given parent.

        :type parent: QtCore.QModelIndex
        :rtype: int
        """

        return len(self._viewDetails)

    def hasChildren(self, parent=None):
        """
        Returns true if parent has any children; otherwise returns false.
        Use rowCount() on the parent to find out the number of children.
        Note that it is undefined behavior to report that a particular index hasChildren with this method if the same index has the flag Qt::ItemNeverHasChildren set!

        :type parent: QtCore.QModelIndex
        :rtype: bool
        """

        node = self.nodeFromIndex(parent)

        if node.isNull():

            return True  # All top-level items have children!

        else:

            return node.hasFn(om.MFn.kDisplayLayerManager) or node.hasFn(om.MFn.kDisplayLayer)

    def flags(self, index):
        """
        Returns the item flags for the given index.

        :type index: QtCore.QModelIndex
        :rtype: QtCore.Qt.ItemFlag
        """

        # Evaluate associated node
        #
        node = self.nodeFromIndex(index)

        if node.isNull():

            return QtCore.Qt.NoItemFlags

        # Evaluate if index is draggable
        #
        isLayerManager = node.hasFn(om.MFn.kDisplayLayerManager)
        isLayer = node.hasFn(om.MFn.kDisplayLayer)
        isNode = node.hasFn(om.MFn.kDagNode)

        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        if isNode:

            flags |= QtCore.Qt.ItemIsDragEnabled

        # Evaluate if index is droppable
        #
        if isLayer:

            flags |= QtCore.Qt.ItemIsDropEnabled

        # Evaluate if index has children
        #
        if isNode:

            flags |= QtCore.Qt.ItemNeverHasChildren
        
        # Evaluate if index is editable
        #
        column = index.column()
        isNameColumn = self._viewDetails[column] == ViewDetail.NAME
        isReferenced = om.MFnDependencyNode(node).isFromReferencedFile

        if isNameColumn and not isReferenced:

            flags |= QtCore.Qt.ItemIsEditable
        
        # Evaluate if index is checkable
        #
        isCheckable = (isNode and isNameColumn) or isLayer

        if isCheckable:

            flags |= QtCore.Qt.ItemIsUserCheckable

        return flags

    def detail(self, node, detail=ViewDetail.NAME):
        """
        Returns the detail for the supplied node in the specified column.

        :type node: om.MObject
        :type detail: ViewDetail
        :rtype: Any
        """

        if detail == ViewDetail.NAME:

            return dagutils.getNodeName(node, includeNamespace=self.showNamespaces())

        else:

            return ''

    def setDetail(self, node, value, detail=ViewDetail.NAME):
        """
        Updates the detail for the supplied node in the specified column.

        :type node: om.MObject
        :type value: Any
        :type detail: ViewDetail
        :rtype: Any
        """

        if detail == ViewDetail.NAME:

            dagutils.renameNode(node, value)
            return True

        else:

            return False

    def decoration(self, node, detail=ViewDetail.NAME):
        """
        Returns the decoration for the supplied node in the specified column.

        :type node: om.MObject
        :type detail: ViewDetail
        :rtype: Union[QtGui.QIcon, None]
        """

        if detail == ViewDetail.NAME:

            isLayerManager = node.hasFn(om.MFn.kDisplayLayerManager)
            iconPath = ':/out_reference.png' if isLayerManager else f':/out_{om.MFnDependencyNode(node).typeName}.png'

            return QtGui.QIcon(iconPath)

        else:

            return None

    def sizeHint(self, index):
        """
        Returns the size-hint for the specified index.

        :type index: QtCore.QModelIndex
        :rtype: QtCore.Qt.QSize
        """

        text = self.data(index, role=QtCore.Qt.DisplayRole)
        fontMetrics = QtGui.QFontMetrics(self.parent().font())
        textWidth = fontMetrics.boundingRect(text).width()

        columnWidth = textWidth if textWidth > self._uniformRowHeight else self._uniformRowHeight
        columnWidth += self.parent().indentation()

        return QtCore.QSize(columnWidth, self._uniformRowHeight)

    def checkState(self, node, detail=ViewDetail.NAME):
        """
        Returns the check-state for the supplied node in the specified column.

        :type node: om.MObject
        :type detail: ViewDetail
        :rtype: QtCore.Qt.CheckState
        """

        # Evaluate supplied node
        #
        isLayer = node.hasFn(om.MFn.kDisplayLayer)
        isNode = node.hasFn(om.MFn.kDagNode)

        if not (isLayer or isNode):

            return

        # Evaluate requested column
        #
        if detail == ViewDetail.NAME:

            plug = plugutils.findPlug(node, 'visibility')
            isVisible = plug.asBool()

            return QtCore.Qt.Checked if isVisible else QtCore.Qt.Unchecked

        elif detail == ViewDetail.PLAYBACK:

            plug = plugutils.findPlug(node, 'hideOnPlayback')
            isHidden = plug.asBool()

            return QtCore.Qt.Checked if isHidden else QtCore.Qt.Unchecked

        elif detail == ViewDetail.FROZEN:

            if isLayer:

                plug = plugutils.findPlug(node, 'displayType')
                displayType = plug.asInt()

                return QtCore.Qt.Unchecked if (displayType == 0) else QtCore.Qt.Checked

            elif isNode:

                plug = plugutils.findPlug(node, 'template')
                isTemplate = plug.asBool()

                return QtCore.Qt.Checked if isTemplate else QtCore.Qt.Unchecked

            else:

                raise TypeError(f'checkState() expects a valid node ({node.apiTypeStr} given)!')

        else:

            raise TypeError(f'checkState() expects a valid column ({detail} given)!')

    def setCheckState(self, node, isChecked, detail=ViewDetail.NAME):
        """
        Updates the check-state for the supplied node for the specified detail.

        :type node: om.MObject
        :type isChecked: Union[bool, int]
        :type detail: ViewDetail
        :rtype: bool
        """

        # Evaluate supplied node
        #
        isLayer = node.hasFn(om.MFn.kDisplayLayer)
        isNode = node.hasFn(om.MFn.kDagNode)

        if not (isLayer or isNode):

            return False

        # Evaluate requested column
        #
        if detail == ViewDetail.NAME:

            plug = plugutils.findPlug(node, 'visibility')

            if plug.isConnected:

                sourcePlug = plug.source()
                sourcePlug.setBool(isChecked)

            else:

                plug.setBool(isChecked)

        elif detail == ViewDetail.PLAYBACK:

            plug = plugutils.findPlug(node, 'hideOnPlayback')

            if plug.isConnected:

                sourcePlug = plug.source()
                sourcePlug.setBool(isChecked)

            else:

                plug.setBool(isChecked)

        elif detail == ViewDetail.FROZEN:

            if isLayer:

                displayType = 2 if isChecked else 0

                plug = plugutils.findPlug(node, 'displayType')
                plug.setInt(displayType)

            elif isNode:

                plug = plugutils.findPlug(node, 'template')
                plug.setBool(isChecked)

            else:

                return False

        else:

            return False

        return True

    def data(self, index, role=None):
        """
        Returns the data stored under the given role for the item referred to by the index.

        :type index: QtCore.QModelIndex
        :type role: QtCore.Qt.ItemDataRole
        :rtype: Any
        """

        # Evaluate associated node
        #
        node = self.nodeFromIndex(index)

        if node.isNull():

            return

        # Evaluate data role
        #
        column = index.column()
        detail = self._viewDetails[column]

        if role == QtCore.Qt.DisplayRole:

            return str(self.data(index, role=QtCore.Qt.EditRole))

        elif role == QtCore.Qt.EditRole:

            return self.detail(node, detail=detail)

        elif role == QtCore.Qt.DecorationRole:

            return self.decoration(node, detail=detail)

        elif role == QtCore.Qt.SizeHintRole:

            return self.sizeHint(index)

        elif role == QtCore.Qt.CheckStateRole:

            return self.checkState(node, detail=detail)

        elif role == QtCore.Qt.TextAlignmentRole:

            isNameColumn = detail == ViewDetail.NAME
            alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter if isNameColumn else QtCore.Qt.AlignCenter

            return alignment

        else:

            return None

    def setData(self, index, value, role=None):
        """
        Sets the role data for the item at index to value.
        Returns true if successful; otherwise returns false.

        :type index: QtCore.QModelIndex
        :type value: Any
        :type role: QtCore.Qt.ItemDataRole
        :rtype: bool
        """

        # Evaluate associated node
        #
        node = self.nodeFromIndex(index)

        if node.isNull():

            return False

        # Evaluate data role
        #
        column = index.column()
        detail = self._viewDetails[column]

        if role == QtCore.Qt.EditRole:

            success = self.setDetail(node, value, detail=detail)

            if success:

                self.dataChanged.emit(index, index, [role])

            return success

        elif role == QtCore.Qt.CheckStateRole:

            success = self.setCheckState(node, value, detail=detail)

            if success:

                self.dataChanged.emit(index, index, [role])

            return success

        else:

            return False

    def headerData(self, section, orientation, role=None):
        """
        Returns the data for the given role and section in the header with the specified orientation.

        :type section: int
        :type orientation: QtCore.Qt.Orientation
        :type role: QtCore.Qt.ItemDataRole
        :rtype: Any
        """

        # Evaluate orientation type
        #
        if orientation == QtCore.Qt.Horizontal:

            # Evaluate data role
            #
            if role == QtCore.Qt.DisplayRole:

                return self._headerLabels[section]

            elif role == QtCore.Qt.TextAlignmentRole:

                isNameColumn = self._viewDetails[section] == ViewDetail.NAME
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter if isNameColumn else QtCore.Qt.AlignCenter

            else:

                return super(QLayerItemModel, self).headerData(section, orientation, role=role)

        elif orientation == QtCore.Qt.Vertical:

            # Evaluate data role
            #
            if role == QtCore.Qt.DisplayRole:

                return str(section)

            else:

                return super(QLayerItemModel, self).headerData(section, orientation, role=role)

        else:

            return super(QLayerItemModel, self).headerData(section, orientation, role=role)
    # endregion
