from Qt import QtCore, QtWidgets, QtGui
from . import qlayeritemmodel

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QLayerItemFilterModel(QtCore.QSortFilterProxyModel):
    """
    Overload of `QSortFilterProxyModel` that filters display layers.
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
        super(QLayerItemFilterModel, self).__init__(parent=parent)

        # Declare private variables
        #
        self._hideDefaultLayer = kwargs.get('hideDefaultLayer', True)
    # endregion

    # region Methods
    def filterAcceptsRow(self, row, parent):
        """
        Returns true if the item in the row indicated by the given row and parent should be included in the model.

        :type row: int
        :type parent: QtCore.QModelIndex
        :rtype: bool
        """

        # Check if default layer should be hidden
        #
        if self._hideDefaultLayer:

            model = self.sourceModel()  # type: qlayeritemmodel.QLayerItemModel
            index = model.index(row, 0, parent=parent)
            text = index.data(role=QtCore.Qt.DisplayRole)

            name = text if text is not None else ''

            if name.endswith('defaultLayer'):

                return False

        # Call parent method
        #
        return super(QLayerItemFilterModel, self).filterAcceptsRow(row, parent)
    # endregion
