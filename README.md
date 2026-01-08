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
  
**Note on Accuracy:** When drawing the sample box, the script "snaps" the corners to the nearest 0.5 meters. To ensure consistency for density calculations, the area is calculated simply as `Width * Height` (e.g., 100m * 60m = 6000m²). This overrides minor geodesic discrepancies inherent to map projections, ensuring the math matches the visual labels.

## Usage Instructions (v1.4.4)

### 1. Preparation
- Select a single polygon (`natural=wood`, `natural=scrub`, or `landuse=forest`).
- Ensure you have an imagery layer active.
- Run the script.

### 2. Setup & Metadata
- **Imagery Date:** Enter the date of the satellite imagery used (e.g., `2024-06-15`).
- **Vegetation Type:** Choose between **Trees**, **Bushes**, or **Heathland Plants**.
  - *Tip: The script now uses appropriate visual markers (`natural=tree` vs `natural=shrub`) based on this choice.*

### 3. Calibration (The Sample Box)
- **Draw the Box:** Click and drag to create a representative sample area. The script will snap the dimensions to the nearest 0.5m.
- **Measure Diameters:** Draw lines across a few crowns/shrubs to calibrate the average size. 
- **Confirm:** Press `ENTER` to lock in the calibration and move to counting.

### 4. Counting Phase
- **SHIFT + Click** every tree/shrub inside the box.
- Use `BACKSPACE` or `DELETE` to undo the last point if you misclick.
- **Visuals:** You will see small green markers identifying each counted item.
- Press `ENTER` when finished.

### 5. Smart Suggestions & Logging
- **Smart Tags:** If the calculated density contradicts the current tagging (e.g., a "wood" that is actually "scattered scrub"), the script will suggest a tag update.
- **Save Log:** Choose `YES` when prompted to save a detailed `TreeSurvey_{ID}_{Time}.txt` file. This log serves as your proof of survey and includes:
    - Original object tags (Surveyed Type)
    - Calculated canopy percentage and stem count
    - Detailed coordinates of every point counted for audit purposes.

## How to Use (v1.4.4)

1. **Select:** Highlight a **closed way** or a **multipolygon relation** representing the area to be analyzed (e.g., `natural=wood` or `natural=scrub`).
2. **Setup:** Ensure a background imagery layer (Bing, Esri, etc.) is visible and execute the script from the JOSM Scripting Console.
3. **Metadata:** - Enter the **Imagery Date** when prompted (YYYY-MM-DD).
    - Select the **Vegetation Type** (Trees, Bushes, or Heathland). 
    - *Note: Choosing "Bushes" or "Plants" will automatically use `natural=shrub` markers for the counting phase.*
4. **Calibrate:** - **CLICK+DRAW** a sample box over a representative section of the area. (Dimensions will snap to the nearest 0.5m).
    - **CLICK+DRAG** the diameter of several tree crowns or bush widths to establish a high-accuracy average.
    - Press **Enter** to lock calibration.
5. **Count:** - **SHIFT+CLICK** all trees/bushes strictly inside the sample box. 
    - You can use **Backspace/Delete** to remove the last point if you misclick.
    - Press **Enter** when the sample count is complete.
6. **Finalize & Smart Suggestions:** Review the calculated results and the Smart Suggestion prompt:
    - **Yes:** Apply new density tags and update the primary tag (e.g., `natural=scrub` → `natural=wood`) based on canopy cover.
    - **No:** Apply density tags (canopy %, etc.) but keep the existing primary tag.
    - **Cancel:** Exit the script without making any changes to the OSM object.
7. **Log:** Choose **Yes** to export the `TreeSurvey_{ID}_{Time}.txt` log. This file records the **Surveyed Type** (original tags), imagery source, and the exact coordinates of every item counted for audit purposes.

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

## Logging & Data Export
As of v1.4.0, the tool allows you to save a local survey log for your records. After applying tags, you will be prompted to save a `.txt` file containing:
* **Survey Metadata:** Date, Imagery Source, OSM Way ID.
* **Applied Tags:** The exact key/value pairs added to the map.
* **Raw Data Appendix:** * Exact GPS coordinates of your sample box corners.
    * Start and End coordinates for every diameter measurement.
    * Coordinates for every individual tree counted.

---
*Mapping with nuance. Join the effort to move beyond the green blob.*
