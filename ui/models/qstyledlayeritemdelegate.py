from Qt import QtCore, QtWidgets, QtGui
from .qlayeritemmodel import ViewDetail

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QStyledLayerItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Overload of `QStyledItemDelegate` that implements style overloads for check-boxes.
    """

    # region Dunderscores
    __checkbox_icons__ = {
        ViewDetail.NAME: QtGui.QIcon(':layerExplorer/icons/visible.png'),
        ViewDetail.FROZEN: QtGui.QIcon(':layerExplorer/icons/frozen.png'),
        ViewDetail.PLAYBACK: QtGui.QIcon(':layerExplorer/icons/playback.png')
    }
    # endregion

    # region Methods
    def paint(self, painter, option, index):
        """
        Renders the delegate using the given painter and style option for the item specified by index.
        This function paints the item using the view's QStyle.
        When reimplementing paint in a subclass. Use the initStyleOption() to set up the option in the same way as the QStyledItemDelegate.
        See the following for details: https://wiki.qt.io/Center_a_QCheckBox_or_Decoration_in_an_Itemview

        :type painter: QtGui.QPainter
        :type option: QtWidgets.QStyleOptionViewItem
        :type index: QtCore.QModelIndex
        :rtype: None
        """

        # Initialize style option
        #
        self.initStyleOption(option, index)

        # Draw base primitive
        #
        style = QtWidgets.QApplication.instance().style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, option.widget)

        # Evaluate source model
        #
        model = index.model()

        if isinstance(model, QtCore.QSortFilterProxyModel):

            index = model.mapToSource(index)
            model = model.sourceModel()

        # Evaluate current column
        #
        details = model.viewDetails()
        column = index.column()
        detail = details[column]

        isNameColumn = detail == ViewDetail.NAME
        isFrozenColumn = detail == ViewDetail.FROZEN
        isPlaybackColumn = detail == ViewDetail.PLAYBACK

        if isNameColumn:

            # Evaluate item state
            #
            isCheckable = option.features & QtWidgets.QStyleOptionViewItem.HasCheckIndicator
            isChecked = option.checkState == QtCore.Qt.Checked
            isEnabled = option.state & QtWidgets.QStyle.State_Enabled
            isOpen = option.state & QtWidgets.QStyle.State_Open

            # Get item component bounds
            #
            checkBoxRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)
            decorationRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemDecoration, option, option.widget)
            textRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, option, option.widget)

            # Get visibility icon
            #
            iconMode = QtGui.QIcon.Normal if ((isChecked and isCheckable) or (isEnabled and not isCheckable)) else QtGui.QIcon.Disabled
            iconState = QtGui.QIcon.On if isOpen else QtGui.QIcon.Off
            checkBoxIcon = self.__checkbox_icons__[detail]

            # Paint item components
            #
            checkBoxIcon.paint(painter, checkBoxRect, QtCore.Qt.AlignCenter, iconMode, iconState)
            painter.drawText(textRect, index.data(role=QtCore.Qt.TextAlignmentRole), option.text)

            if not option.icon.isNull():

                option.icon.paint(painter, decorationRect, QtCore.Qt.AlignCenter, iconMode, iconState)

        elif isFrozenColumn or isPlaybackColumn:

            isChecked = option.checkState == QtCore.Qt.Checked
            isOpen = option.state & QtWidgets.QStyle.State_Open

            checkBoxRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)
            option.rect = QtWidgets.QStyle.alignedRect(option.direction, QtCore.Qt.Alignment(index.data(role=QtCore.Qt.TextAlignmentRole)), checkBoxRect.size(), option.rect)
            option.state = option.state & ~QtWidgets.QStyle.State_HasFocus

            mode = QtGui.QIcon.Normal if isChecked else QtGui.QIcon.Disabled
            state = QtGui.QIcon.On if isOpen else QtGui.QIcon.Off
            checkBoxIcon = self.__checkbox_icons__[detail]

            checkBoxIcon.paint(painter, option.rect, QtCore.Qt.AlignCenter, mode, state)

        else:

            super(QStyledLayerItemDelegate, self).paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        """
        When editing of an item starts, this function is called with the event that triggered the editing, the model, the index of the item, and the option used for rendering the item.
        Mouse events are sent to editorEvent() even if they don't start editing of the item. This can, for instance, be useful if you wish to open a context menu when the right mouse button is pressed on an item.
        The base implementation returns false (indicating that it has not handled the event).

        :type event: QtCore.QEvent
        :type model: QtCore.QAbstractItemModel
        :type option: QtWidgets.QStyleOptionViewItem
        :type index: QtCore.QModelIndex
        :rtype: bool
        """

        # Evaluate source model
        #
        model = index.model()

        if isinstance(model, QtCore.QSortFilterProxyModel):

            index = model.mapToSource(index)
            model = model.sourceModel()

        # Check if index is checkable
        #
        flags = model.flags(index)
        isCheckable = flags & QtCore.Qt.ItemIsUserCheckable

        if not isCheckable:

            return super(QStyledLayerItemDelegate, self).editorEvent(event, model, option, index)

        # Evaluate affected column
        #
        details = model.viewDetails()
        column = index.column()
        detail = details[column]

        isNameColumn = detail == ViewDetail.NAME

        if isNameColumn:

            return super(QStyledLayerItemDelegate, self).editorEvent(event, model, option, index)  # Name column uses default alignment!

        # Evaluate event type
        #
        isMouseEvent = isinstance(event, QtGui.QMouseEvent)

        if not isMouseEvent:

            return super(QStyledLayerItemDelegate, self).editorEvent(event, model, option, index)

        # Evaluate mouse event type
        #
        mouseEventType = event.type()
        isClickEvent = mouseEventType == QtGui.QMouseEvent.MouseButtonRelease

        if isClickEvent:

            # Initialize style options
            #
            self.initStyleOption(option, index)

            # Check if mouse is inside aligned check-box bounds
            #
            style = QtWidgets.QApplication.instance().style()
            checkBoxRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)
            alignedRect = QtWidgets.QStyle.alignedRect(option.direction, QtCore.Qt.Alignment(index.data(role=QtCore.Qt.TextAlignmentRole)), checkBoxRect.size(), option.rect)

            wasClicked = alignedRect.contains(event.pos())

            if wasClicked:

                checkState = index.data(role=QtCore.Qt.CheckStateRole)
                toggledState = QtCore.Qt.Checked if (checkState == QtCore.Qt.Unchecked) else QtCore.Qt.Unchecked

                return model.setData(index, toggledState, role=QtCore.Qt.CheckStateRole)

            else:

                return False

        else:

            return False
    # endregion
