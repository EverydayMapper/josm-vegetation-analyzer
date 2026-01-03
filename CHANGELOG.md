# Release Notes

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
