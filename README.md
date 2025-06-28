# Layer Explorer
An improved user interface for display layers inside Maya.  
Now you can actually expand layers and select nodes inside of them!  
All referenced layers are now nested inside their associated reference node!  
  
![image](https://github.com/user-attachments/assets/36634354-e321-4aa5-80a4-5bf605f22312)
  
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
