# Release Notes

## [1.2.3] - 2026-01-05
### Changed
- **Refined Smart Suggestions:** The script now respects "Silent Mapping" for specialized areas. Suggestions to switch between `scrub` and `wood` only trigger if those specific tags (or `landuse=forest`) are present. This prevents the script from incorrectly suggesting a tag change for surveys performed on `grassland`, `heath`, or `wetland`.
- **Improved Feedback:** The suggestion dialog now explicitly mentions the Density Class (e.g., "Open", "Dense") to educate the user on FAO terminology.

## [1.2.2] - 2026-01-04
### Fixed
- **Mouse Event Ghosting:** Resolved a rare but annoying bug where the cursor would remain stuck in "selection mode" (red line following cursor) after releasing the mouse button. Fixed by forcing a UI focus reset (`requestFocusInWindow`) and immediate state clearing in the `mouseReleased` event.

### Changed
- **Documentation:** Updated the internal HOW-TO guide to include the Esri World Imagery Wayback (Living Atlas) workflow for retrieving precise imagery capture dates.

## [1.2.1] - 2026-01-04
### Fixed
- **Source Layer Detection:** Replaced keyword-based filtering ("Imagery"/"Satellite") with a visibility-check logic. The script now correctly identifies Bing, Mapbox, and local WMS layers as the source.
- **Multipolygon Area Accuracy:** Refined the area calculation to ensure it consistently accounts for the total area of all outer members minus inner members.

### Added
- **Smart Tagging Logic:** Added prompts to suggest switching primary tags between `natural=scrub` and `natural=wood` based on the calculated canopy density (10% threshold).

### Changed
- **Documentation:** Updated README and internal documentation to clarify behavior regarding complex multipolygons with multiple independent outer rings.

## [1.2.0] - 2026-01-04
### Added
- **`est:source_area` tag:** Records the exact area used for the calculation to help future mappers identify geometry bias.
- **Graceful Exit:** Added logic to stop the script safely if the user clicks "Cancel" on the date prompt.

## [1.1.0] - 2026-01-04
### Changed
- **Renamed Project:** Changed from "Vegetation Analyzer" to **Tree Density Estimator** for better clarity and impact.
- **Improved Logic:** Enhanced the area calculation to support JOSM Multipolygon Relations (handles 'inner' and 'outer' members correctly).

### Added
- **Smart Tag Suggestions:** The tool now prompts the mapper to switch between `natural=wood` and `natural=scrub` if density thresholds are met.
- **Mean Inter-Tree Distance:** Added calculation for the average gap between plants.
- **FAO Standards:** Tagging thresholds for `wood:density` are now officially aligned with FAO Global Forest Resources Assessment classes.
- **Imagery Metadata:** Support for adding Esri Wayback capture dates to the `source` tag.

## [1.0.0] - 2026-01-03
### Added
- Initial official release by **EverydayMapper**.
- Statistical extrapolation logic for `canopy` and `wood:density`.
- Live diameter calibration tool.
- Average spacing calculation (`est:avg_spacing`).
- Support for Esri Wayback imagery date metadata.
- Precision sampler with Shift+Click counting.
