# Layer Explorer
An improved user interface for display layers inside Maya.  
Now you can actually expand layers and select nodes inside of them!  
All referenced layers are now nested inside their associated reference node!  

![image](https://github.com/bhsingleton/layerexplorer/assets/11181168/f8cf6bd6-f38c-42a0-b7d7-7c3fb2a33a26)

Features:
- Layers are nested under their associated reference node for cleaner viewing.
- Nodes are selectable from within their associated display layer.
- Toggle visibility on nodes with incoming connections.
- Quickly search for and filter nodes from the search bar.

Roadmap:  
- Implement logic for menu-bar actions and layer interop buttons.
- Add columns for playback and display type toggling.
  
### How to open:

```
from layerexplorer.ui import qlayerexplorer

window = qlayerexplorer.QLayerExplorer()
window.show()
```
  
Requires: dcc and Qt modules.  
