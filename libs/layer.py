from dcc.json import psonobject
from dcc.collections import notifylist

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Layer(psonobject.PSONObject):

    # region Dunderscores
    __slots__ = ('_name', '_parent', '_children', '_nodes', '_visible')

    def __init__(self, *args, **kwargs):

        super(Layer, self).__init__(*args, **kwargs)

        self._name = kwargs.get('name', '')
        self._parent = self.nullWeakReference
        self._children = notifylist.NotifyList()
        self._nodes = notifylist.NotifyList()
        self._visible = kwargs.get('visible', True)
    # endregion

    # region Properties
    @property
    def name(self):
        """
        Getter method that returns the layer name.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the layer name.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def parent(self):

        return self._parent()

    @parent.setter
    def parent(self, parent):

        self._parent = parent.weakReference()

    @property
    def children(self):

        return self._children

    @property
    def nodes(self):

        return self._nodes

    @property
    def visible(self):

        return self._visible
    # endregion

    # region Methods
    # endregion
