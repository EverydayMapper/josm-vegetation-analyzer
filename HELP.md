# Help & Technical Requirements

## Environment & Compatibility
- **Author:** EverydayMapper (OSM Contributor)
- **Version:** 1.0.0
- **Verified OS:**
    - macOS (Sequoia 15.x / 26.2) 
    - Windows 11 (Version 24H2)
- **JOSM Version:** 19277 or newer (Official or Microsoft Store versions)
- **Java Runtime:**
    - Java 21 (macOS Bundled)
    - Java 17 or 21 (Windows)
    - *Note: JOSM's internal runtime is sufficient; no system-wide Java PATH setup is required.*

## Dependencies
This script is a Python-based tool for the JOSM Scripting environment. To run it, you must have two components:

1. **JOSM Scripting Plugin:** - Install "Scripting" via JOSM Plugin Preferences.
   - Tested Plugin Version: v0.3.5

2. **Jython Standalone Engine (Required):**
   - The script requires the **Jython Standalone 2.7.4** JAR file.
   - **Installation:** Download the JAR from [Jython.org](https://www.jython.org/download) and point to it in:
     `Preferences -> Scripting -> Script Engines -> JAR files`.

## How to Run
1. **Prepare Map:** Select a closed way or a multipolygon relation (outer/inner).
2. **Imagery:** Ensure a background imagery layer is visible (the script will guard against blank backgrounds).
3. **Launch:** Open the Scripting Console (**Windows -> Scripting Console**).
4. **Execute:** Load `tree_density_estimator.py` and click **Run**.
5. **Workflow:** Follow the status bar prompts: 
   - Click+Draw (Sample Box)
   - Click+Drag (Diameter Calibration)
   - Shift+Click (Counting)

## Troubleshooting
- **No Imagery Detected:** If the script warns of no imagery despite a layer being visible, try toggling the layer's visibility off and on again.
- **Windows File Saving:** If you cannot save the `.txt` log to a system folder, try a user-created folder or run JOSM with appropriate permissions.
- **Trackpad Issues (macOS):** The script is optimized for modern macOS trackpads; if drawing feels "stuck," ensure you are not holding other modifier keys besides Shift during the counting phase.

## Known Limitations
- **Statistical Extrapolation:** This tool uses representative sampling. Accuracy depends on choosing a sample area that truly reflects the density of the entire polygon.
- **Visual Visibility:** Most accurate in "Open," "Scattered," or "Dense" vegetation. It is not recommended for "Closed Canopy" (rainforest) environments where individual stems cannot be distinguished from above.
- **Performance:** For extremely large polygons (several km²), JOSM's area calculation may experience minor lag during the final tag application.

---
*For support or to report bugs, please contact the author via the OpenStreetMap messaging system.*
