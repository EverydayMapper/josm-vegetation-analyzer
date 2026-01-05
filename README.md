# Tree Density Estimator for JOSM

**Version:** 1.2.6  
**Author:** EverydayMapper  
**Platform:** macOS 26.2 (Tested), JOSM v19439, Java 21

## Overview

The **Tree Density Estimator** is a JOSM script designed to bridge the gap between "Scrub" and "Wood" in OpenStreetMap. Instead of relying on binary choices or solid green fills, this tool allows mappers to provide nuanced data such as canopy percentage, stem counts, and wood density classes based on FAO standards.

It uses a **sampling and extrapolation** method: measure a small representative area, count the individuals, and let the script handle the complex math for the entire polygon.

## Key Features

* **Statistical Extrapolation:** Calculates total counts and canopy cover based on a sample area.
* **Imagery Enforcement:** Requires an active, visible imagery layer to start, ensuring surveys are conducted against a visual source.
* **Silent Suggestions:** Intelligent logic that only prompts for a primary tag change (e.g., `natural=scrub` to `natural=wood`) if the measured density conflicts with existing tags.
* **macOS Optimization:** Wrapped in `invokeLater` logic to prevent "ghosting" or "stuck red lines" common with trackpads and modern macOS versions.
* **Mean Inter-Tree Distance:** Automatically calculates the average gap between plants using the formula: $d = \sqrt{\frac{1}{\text{density}}}$.
* **Multipolygon Support:** Handles complex relations with 'inner' and 'outer' members.
* **Standardized Output:** Uses FAO Global Forest Resources Assessment classes for `wood:density`.

## Installation & Requirements

This is a Python-based script for the **JOSM Scripting Plugin**.

1.  **Install the Scripting Plugin:** Find it in the JOSM Plugin Preferences.
2.  **Jython Standalone:** Download the Jython standalone jar and point the Scripting Plugin to it in JOSM Preferences.
3.  **Download this Script:** Place `tree_density_estimator.py` in your local scripts folder.

## How to Use

1.  **Select:** Highlight a **closed way** or a **multipolygon relation**.
2.  **Imagery Check:** Ensure a background imagery layer (Bing, Esri, etc.) is visible.
3.  **Run:** Execute the script from the JOSM Scripting Console.
4.  **Calibrate:** * CLICK+DRAW a sample box on a representative area.
    * CLICK+DRAG the diameter of several tree crowns to get a high-accuracy average.
    * Press **Enter**.
5.  **Count:** SHIFT+CLICK **all** trees/bushes inside the sample box.
6.  **Finalize:** Press **Enter**. Review the Smart Suggestion prompt:
    * **Yes:** Apply new density tags and update the primary tag (e.g., scrub → wood).
    * **No:** Apply density tags but keep the existing primary tag.
    * **Cancel:** Exit the script without making any changes.

## Tagging Applied

The tool applies the following tags to the selected object:
* `canopy=*` (Percentage rounded to nearest 5%)
* `wood:density=*` (Scattered, Open, Dense, Very Dense)
* `est:stem_count=*` (Total estimated plants)
* `est:avg_crown` or `est:avg_shrub` (Mean diameter measured)
* `est:avg_spacing=*` (Mean Inter-Tree Distance)
* `est:source_area=*` (The total area in $m^2$ used for the calculation)
* `source=*` (Imagery name, capture date if provided, and tool attribution)

## Vital Best Practices

### 1. The "Time Travel" Trap
Vegetation changes significantly over time. WMS services (like Esri World Imagery) may provide tiles that are over 10–15 years old in certain regions. 
* **Always verify the capture date** using tools like Esri Wayback. 
* If imagery is significantly outdated (e.g., from 2011), treat results with caution as they may no longer reflect ground reality.

### 2. Area Verification
After the script finishes, it is good practice to compare the `est:source_area` tag against the value shown in the **JOSM Measurement Plugin**. 
* If the polygon geometry is modified later, these values will drift.
* Periodically cross-referencing these ensures the density data remains linked to the correct spatial extent.



## Limitations

This tool is most accurate in "Open" to "Dense" areas where individual crowns are visible. It is not recommended for closed-canopy forests where the ground is invisible, as visual counting becomes guesswork.

---
*Mapping with nuance. Join the effort to move beyond the green blob.*
