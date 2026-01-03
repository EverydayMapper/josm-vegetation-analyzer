# JOSM Vegetation Analyzer

A Python tool for the JOSM Scripting Plugin that helps mappers scientifically estimate vegetation density and canopy cover from satellite imagery samples.

## Why use this?
Mapping individual trees in a forest is time-consuming and can bloat the OSM database. This tool uses a statistical "sample and extrapolate" method to provide accurate tagging without mapping every single stem.

## Features
- **Live Diameter Calibration:** Measure crown sizes with real-time averaging.
- **Sample Box Statistics:** Automatically calculates area-based density.
- **Tagging Automation:** Applies `canopy`, `wood:density`, `est:stem_count`, and `est:avg_spacing`.
- **Imagery Sourcing:** Supports adding Esri Wayback dates to the `source` tag.

## Installation
1. Install the **Scripting** plugin in JOSM.
2. Ensure you have a Python engine configured (e.g., Jython or a local Python install).
3. Download `vegetation_analyzer.py` from the `/scripts` folder in this repo.
4. Open the Scripting console in JOSM and run the file.

## How to Use
1. **Select** your main forest/scrub polygon.
2. **Draw** a sample box within the polygon.
3. **Calibrate** by dragging from one side of a tree crown to the other.
4. **Count** by using `Shift+Click` on individuals inside the box.
5. **Finish** by pressing `Enter` to apply tags to the main polygon.

### Requirements
1. **JOSM** (Tested on v19439)
2. **Scripting Plugin** (Tested on v0.3.5)
3. **Jython Standalone** (Available via [Gubaer's GitHub](https://github.com/Gubaer/josm-scripting-plugin/releases))
