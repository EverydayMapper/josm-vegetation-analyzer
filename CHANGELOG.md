# CHANGELOG

## [1.0.0] - 2026-01-09
### Initial Public Release
This release marks the first stable version of the **Tree Density Estimator**, incorporating all features and fixes from the intensive beta development phase.

### Core Features
* **Statistical Extrapolation:** Automated calculation of `canopy` percentage, total `est:stem_count`, and `wood:density` classes based on FAO Global Forest Resources Assessment standards.
* **Precision Calibration:** High-accuracy average diameter measurement (crown/shrub width) with one-decimal precision and visual "snapping" to 0.5m for box dimensions.
* **Smart Suggestions:** Intelligent logic that prompts for primary tag updates (e.g., `natural=scrub` → `natural=wood`) only when measured density necessitates a change.
* **Advanced Spacing Math:** Automatic calculation of the "Mean Inter-Tree Distance" using the formula $d = \sqrt{\frac{1}{\text{density}}}$ for the `est:avg_spacing` tag.

### Interaction & UI
* **Live HUD:** Real-time Head-Up Display showing box dimensions and measurement lines directly on the map during the drawing phase.
* **Visual Counters:** Numbered markers appear during the counting phase to track progress visually.
* **Contextual Markers:** Dynamically switches between `natural=tree` and `natural=shrub` icons based on the chosen vegetation type.

### Safeguards & Compatibility
* **Imagery Guard:** Built-in verification to ensure a background imagery layer is visible, preventing "blind" surveys and ensuring accurate `source` tagging.
* **Cross-Platform Performance:** Specific fixes for macOS trackpad "focus ghosting" and verified compatibility with Windows 11 (24H2) and Java 21.
* **Area Accuracy:** Logic ensures the calculated area matches the visual "snapped" dimensions, ignoring geodesic distortion for small-scale sampling consistency.

### Data & Logging
* **Full Audit Trail:** Optional export of `.txt` survey logs including metadata, applied tags, and raw GPS coordinates for every item counted.
* **Multipolygon Support:** Native support for JOSM relations, handling 'inner' and 'outer' members to calculate accurate total areas.

---

## [Pre-Release Development History]
*Detailed notes on the iteration path from the original concept to v1.0.0.*

* **v1.4.0 – v1.4.5:** Restored imagery detection logic, added `Surveyed Type` metadata, and finalized the "Smart Suggestion" logic.
* **v1.2.0 – v1.3.3:** UX overhaul including the Live HUD, macOS event loop fixes, and FAO alignment for density classes.
* **v1.0.0 – v1.1.0 (Beta):** Initial project foundation and transition from "Vegetation Analyzer" to the "Tree Density Estimator" branding.
