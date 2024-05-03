from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui
from enum import IntEnum
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
    LEVEL_OF_DETAIL = 3


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
        self._viewDetails = [ViewDetail.NAME]
        self._headerLabels = [detail.name.title().replace('_', ' ') for detail in self._viewDetails]
        self._uniformRowHeight = kwargs.get('uniformRowHeight', 24.0)
        self._showNamespaces = True
        self._layerManagers = []
        self._internalIds = {}
    # endregion

    # region Mutators
    def layerManagers(self):
        """
        Returns the root layer managers.

        :rtype: List[om.MObjectHandle]
        """

        return self._layerManagers

    def setLayerManagers(self, layerManagers):
        """
        Updates the root layer managers.

        :type layerManagers: List[om.MObjectHandle]
        :rtype: None
        """

        # Notify model reset
        #
        self.beginResetModel()

        # Reset internal trackers
        #
        self._layerManagers.clear()
        self._layerManagers.extend(map(dagutils.getMObjectHandle, layerManagers))

        self._internalIds.clear()
        self._internalIds.update({handle.hashCode(): handle for handle in self._layerManagers})

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
    def nodeFromIndex(self, index):
        """
        Returns the node associated with the supplied index.

        :type index: QtCore.QModelIndex
        :rtype: om.MObject
        """

        internalId = index.internalId()
        handle = self._internalIds.get(internalId, om.MObjectHandle())

        if handle.isValid():

            return handle.object()

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

            drawOverridePlug = plugutils.findPlug(node, 'drawOverride')
            sourcePlug = drawOverridePlug.source()
            destinations = sourcePlug.destinations()
            row = destinations.index(drawOverridePlug)

            hashCode = om.MObjectHandle(node).hashCode()

            return self.createIndex(row, 0, id=hashCode)

        elif node.hasFn(om.MFn.kDisplayLayer):

            identificationPlug = plugutils.findPlug(node, 'identification')
            sourcePlug = identificationPlug.source()
            arrayPlug = sourcePlug.array()
            connectionCount = arrayPlug.numConnectedElements()
            elements = [arrayPlug.connectionByPhysicalIndex(i) for i in range(connectionCount)]
            row = elements.index(sourcePlug)

            hashCode = om.MObjectHandle(node).hashCode()

            return self.createIndex(row, 0, id=hashCode)

        elif node.hasFn(om.MFn.kDisplayLayerManager):

            row = self._layerManagers.index(node)
            hashCode = om.MObjectHandle(node).hashCode()

            return self.createIndex(row, 0, id=hashCode)

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

                handle = self._layerManagers[row]
                hashCode = handle.hashCode()

                return self.createIndex(row, column, id=hashCode)

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
                plug = plugutils.findPlug(node, 'displayLayerId')
                maxRow = plug.numConnectedElements()

                if not (0 <= row < maxRow):

                    return QtCore.QModelIndex()

                # Check if plug element is valid
                #
                element = plug.connectionByPhysicalIndex(row)

                destinations = element.destinations()
                numDestinations = len(destinations)

                if numDestinations == 1:

                    destination = destinations[0]
                    childNode = destination.node()
                    childHandle = om.MObjectHandle(childNode)
                    hashCode = childHandle.hashCode()
                    self._internalIds[hashCode] = childHandle

                    return self.createIndex(row, column, id=hashCode)

                else:

                    return QtCore.QModelIndex()

            elif node.hasFn(om.MFn.kDisplayLayer):

                # Check if row is in range
                #
                plug = plugutils.findPlug(node, 'drawInfo')

                destinations = plug.destinations()
                maxRow = len(destinations)

                if 0 <= row < maxRow:

                    destination = destinations[row]
                    childNode = destination.node()
                    childHandle = om.MObjectHandle(childNode)
                    hashCode = childHandle.hashCode()
                    self._internalIds[hashCode] = childHandle

                    return self.createIndex(row, column, id=hashCode)

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

            plug = plugutils.findPlug(node, 'displayLayerId')
            connectionCount = plug.numConnectedElements()

            return connectionCount

        elif node.hasFn(om.MFn.kDisplayLayer):

            plug = plugutils.findPlug(node, 'drawInfo')
            destinations = plug.destinations()

            return len(destinations)

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
        hasChildren = not node.hasFn(om.MFn.kDagNode)

        return hasChildren

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
        isFrozenColumn = self._viewDetails[column] == ViewDetail.FROZEN
        supportsTriState = isLayer and isFrozenColumn

        isCheckable = (isNode and isNameColumn) or isLayer

        if supportsTriState:

            flags |= QtCore.Qt.ItemIsUserTristate

        elif isCheckable:

            flags |= QtCore.Qt.ItemIsUserCheckable

        else:

            pass

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

                return QtCore.Qt.Checked if (displayType == 0) else QtCore.Qt.PartiallyChecked if (displayType == 1) else QtCore.Qt.Unchecked

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
        :type isChecked: bool
        :type detail: ViewDetail
        :rtype: None
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
            plug.setBool(isChecked)

        elif detail == ViewDetail.PLAYBACK:

            plug = plugutils.findPlug(node, 'hideOnPlayback')
            plug.setBool(isChecked)

        elif detail == ViewDetail.FROZEN:

            plugName = 'displayType' if isLayer else 'template'
            plug = plugutils.findPlug(node, plugName)
            plug.setBool(isChecked)

        else:

            raise TypeError(f'setCheckState() expects a valid column ({detail} given)!')

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

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):

            return str(self.detail(node, detail=detail))

        elif role == QtCore.Qt.DecorationRole:

            return self.decoration(node, detail=detail)

        elif role == QtCore.Qt.SizeHintRole:

            return self.sizeHint(index)

        elif role == QtCore.Qt.CheckStateRole:

            return self.checkState(node, detail=detail)

        elif role == QtCore.Qt.TextAlignmentRole:

            isNameColumn = detail == ViewDetail.NAME
            alignment = QtCore.Qt.AlignVCenter if isNameColumn else QtCore.Qt.AlignCenter

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

            return False

        elif role == QtCore.Qt.CheckStateRole:

            self.setCheckState(node, value, detail=detail)
            return True

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
