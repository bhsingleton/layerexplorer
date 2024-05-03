from Qt import QtCore, QtWidgets, QtGui
from .qlayeritemmodel import ViewDetail

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QStyledLayerItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Overload of `` that implements style delegates for check-boxes.
    """

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

        # Save painter state
        #
        painter.save()

        # Initialize style option
        #
        self.initStyleOption(option, index)

        # Draw base primitive
        #
        style = QtWidgets.QApplication.instance().style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, option.widget)

        # Evaluate current column
        #
        model = index.model()
        details = model.viewDetails()
        column = index.column()

        isNameColumn = details[column] == ViewDetail.NAME
        isFrozenColumn = details[column] == ViewDetail.FROZEN

        if isNameColumn:

            isChecked = option.checkState == QtCore.Qt.Checked
            isEnabled = option.state & QtWidgets.QStyle.State_Enabled
            isOpen = option.state & QtWidgets.QStyle.State_Open

            checkBoxRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)
            decorationRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemDecoration, option, option.widget)
            textRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, option, option.widget)

            mode = QtGui.QIcon.Normal if isEnabled else QtGui.QIcon.Disabled
            state = QtGui.QIcon.On if isOpen else QtGui.QIcon.Off
            checkBoxIcon = QtGui.QIcon(':layerExplorer/icons/visible.png') if isChecked else QtGui.QIcon(':layerExplorer/icons/hidden.png')

            checkBoxIcon.paint(painter, checkBoxRect, QtCore.Qt.AlignCenter, mode, state)
            option.icon.paint(painter, decorationRect, QtCore.Qt.AlignCenter, mode, state)
            painter.drawText(textRect, index.data(role=QtCore.Qt.TextAlignmentRole), option.text)

        elif isFrozenColumn:

            isChecked = option.checkState == QtCore.Qt.Checked
            isEnabled = option.state & QtWidgets.QStyle.State_Enabled
            isOpen = option.state & QtWidgets.QStyle.State_Open

            checkBoxRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)

            mode = QtGui.QIcon.Normal if isEnabled else QtGui.QIcon.Disabled
            state = QtGui.QIcon.On if isOpen else QtGui.QIcon.Off
            checkBoxIcon = QtGui.QIcon(':layerExplorer/icons/frozen.png') if isChecked else QtGui.QIcon(':layerExplorer/icons/unfrozen.png')

            checkBoxIcon.paint(painter, checkBoxRect, QtCore.Qt.AlignCenter, mode, state)

        else:

            super(QStyledLayerItemDelegate, self).paint(painter, option, index)

        # Restore painter
        #
        painter.restore()
