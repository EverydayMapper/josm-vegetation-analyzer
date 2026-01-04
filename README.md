# Tree Density Estimator for JOSM

**Version:** 1.2.1  
**Author:** EverydayMapper  
**Platform:** macOS 26.2 (Tested), JOSM v19439, Java 21

## Overview

The **Tree Density Estimator** is a JOSM script designed to bridge the gap between "Scrub" and "Wood" in OpenStreetMap. Instead of relying on binary choices or solid green fills, this tool allows mappers to provide nuanced data such as canopy percentage, stem counts, and wood density classes based on FAO standards.

It uses a **sampling and extrapolation** method: measure a small representative area, count the individuals, and let the script handle the complex math for the entire polygon.



## Key Features

* **Statistical Extrapolation:** Calculates total counts and canopy cover based on a sample area.
* **Mean Inter-Tree Distance:** Automatically calculates the average gap between plants using the formula: $d = \sqrt{\frac{1}{\text{density}}}$.
* **Multipolygon Support:** Handles complex relations with 'inner' and 'outer' members.
* **Smart Tagging:** Suggests changing primary tags (e.g., `natural=scrub` to `natural=wood`) based on density thresholds.
* **Standardized Output:** Uses FAO Global Forest Resources Assessment classes for `wood:density`.

## Installation & Requirements

This is a Python-based script for the **JOSM Scripting Plugin**.

1.  **Install the Scripting Plugin:** Find it in the JOSM Plugin Preferences.
2.  **Jython Standalone:** Download the Jython standalone jar (e.g., from [Gubaer's releases](https://github.com/Gubaer/josm-scripting-plugin/releases)) and point the Scripting Plugin to it in JOSM Preferences.
3.  **Download this Script:** Place `tree_density_estimator.py` in your local scripts folder.

## How to Use

1.  **Select:** Highlight a **closed way** or a **multipolygon relation**.
2.  **Run:** Execute the script from the JOSM Scripting Console.
3.  **Calibrate:** * Draw a sample box on a representative area.
    * Measure the diameter of several tree crowns to get a high-accuracy average.
    * Press **Enter**.
4.  **Count:** Shift+Click **all** trees/bushes inside the sample box.
5.  **Finalize:** Press **Enter** to calculate results and apply tags.

## Tagging Applied

The tool applies the following tags to the selected object:
* `canopy=*` (Percentage)
* `wood:density=*` (Scattered, Open, Dense, Very Dense)
* `est:stem_count=*` (Total estimated plants)
* `est:avg_spacing=*` (Mean Inter-Tree Distance)
* `source=*` (Includes imagery source and Wayback capture date)

## Limitations

This tool is a **proposal for better vegetation mapping**. It is most accurate in "Open" to "Dense" areas where individual crowns are visible. It is not recommended for closed-canopy forests where the ground is invisible, as visual counting becomes guesswork.

## Contributing

This script is a functional proposal for moving OSM vegetation mapping beyond binary tags. I welcome feedback, bug reports, and pull requests!

### Known Limitations & Roadmap
* **Per-Ring Statistics:** Currently, for Multipolygon Relations with multiple 'outer' members, the script calculates a global density for the entire relation. For isolated patches with significantly different densities, it is recommended to map them as simple Closed Ways first, run the tool, and then re-incorporate them into the relation.
* **UI Stability:** Version 1.2.2 addresses an intermittent JOSM "ghosting" bug where the cursor would remain attached to a red selection line after drawing the sample box. 
* **Automation:** Exploring the potential for basic computer-vision assisted counting (though human verification remains a priority to avoid "node bombing").

If you find a bug or have a suggestion for the mathematical model, please open an **Issue**.

---
*Mapping with nuance. Join the effort to move beyond the green blob.*
