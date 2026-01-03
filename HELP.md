# Help & Technical Requirements

## Environment
- **Author:** EverydayMapper (OSM Contributor)
- **Primary OS:** macOS 26.2 (Tested)
- **Other OS:** Windows/Linux (Untested)
- **Engine:** Jython (Python for Java)

## Dependencies
This script is not a standalone JOSM plugin yet. It requires the **JOSM Scripting Plugin** to run.
- **Required Plugin:** [JOSM Scripting Plugin](https://github.com/Gubaer/josm-scripting-plugin)
- **Tested Version:** v0.3.5 
- **Direct Download:** [Scripting v0.3.5 Releases](https://github.com/Gubaer/josm-scripting-plugin/releases/tag/v0.3.5)

## How to Run
1. Install the Scripting Plugin in JOSM.
2. Open the Scripting Console (**Windows -> Scripting Console**).
3. Load and run `vegetation_analyzer.py`.

## Known Limitations
This is a **prerelease** tool provided for community testing. It relies on statistical extrapolation and is most accurate in "Open" or "Scattered" vegetation where individual crowns are visible from satellite imagery.
