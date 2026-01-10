# ==============================================================================
# Tree Density Estimator
# Version: 1.0.0 (Official Release)
# Date: 2026-01-09
# Author: EverydayMapper (OSM)
# Repository: https://github.com/EverydayMapper/josm-tree-density-estimator
# License: MIT
#
# A JOSM script for statistical sampling and extrapolation of vegetation 
# density. Calculates canopy %, stem counts, and FAO wood:density classes.
#
# REQUIREMENTS:
# - JOSM Scripting Plugin
# - Jython Standalone v2.7.4
# ==============================================================================

import math
import time
import os
from threading import Thread

# --- Java / JOSM API Imports ---
# This script runs via Jython, allowing direct access to Java Swing (UI)
# and JOSM's internal data structures.
from java.awt.event import MouseListener, MouseMotionListener, KeyListener
from java.awt.geom import Path2D
from javax.swing import JOptionPane, SwingUtilities, JFileChooser
from org.openstreetmap.josm.gui import MainApplication
from org.openstreetmap.josm.data.osm import Node, Way
from org.openstreetmap.josm.tools import Geometry
from org.openstreetmap.josm.data.coor import LatLon
from org.openstreetmap.josm.gui.layer import OsmDataLayer
import java.io.File  # Required for JFileChooser default paths

# ------------------------------------------------------------------------------
# GLOBAL CONFIGURATION
# ------------------------------------------------------------------------------
VERSION = "1.0.0"

CONFIG = {
    # Geometric Constants
    "EARTH_RADIUS": 6378137.0,   # Meters (WGS84 approx)
    "SNAP_PRECISION": 0.5,       # Meters (Box dimensions snap to nearest X)
    "CLICK_TOLERANCE": 0.05,     # Meters (Min drag distance to count as a click)
    
    # FAO Density Thresholds (Canopy Coverage %)
    "DENSITY_VERY_DENSE": 70,
    "DENSITY_DENSE": 40,
    "DENSITY_OPEN": 10,
    
    # UI Text
    "STATUS_PREFIX": "[v{}] ".format(VERSION),
}

# ------------------------------------------------------------------------------
# MATH HELPERS
# ------------------------------------------------------------------------------

def project_point(start_lat, start_lon, dist_m, bearing_rad):
    """
    Calculates a destination coordinate given a start point, distance, and bearing.
    Used to generate the 4 corners of the sample box based on user drag distance.
    """
    R = CONFIG["EARTH_RADIUS"]
    lat1 = math.radians(start_lat)
    lon1 = math.radians(start_lon)
    
    # Inverse Haversine formula
    lat2 = math.asin(
        math.sin(lat1) * math.cos(dist_m / R)
        + math.cos(lat1) * math.sin(dist_m / R) * math.cos(bearing_rad)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing_rad) * math.sin(dist_m / R) * math.cos(lat1),
        math.cos(dist_m / R) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def round_to_snap(value):
    """Snaps a float to the nearest configured precision (default 0.5m)."""
    step = CONFIG["SNAP_PRECISION"]
    return round(value / step) * step


# ------------------------------------------------------------------------------
# MAIN LOGIC
# ------------------------------------------------------------------------------

def run_analyzer():
    # --- 1. JOSM CONTEXT SETUP ---
    # Retrieve the active data layer where the user is currently working.
    layer = MainApplication.getLayerManager().getEditLayer()
    if not layer or not layer.data:
        return # No data layer open
        
    selection = layer.data.getSelected()
    if selection.isEmpty():
        JOptionPane.showMessageDialog(None, "Select the main area polygon first.")
        return

    # Grab the first selected object (Way or Relation) to serve as the target.
    target = selection.iterator().next()
    
    # JOSM's Geometry.computeArea handles complex multipolygons correctly.
    total_area = abs(Geometry.computeArea(target))
    target_id = target.getId()
    target_type = "Way" if isinstance(target, Way) else "Relation"

    # --- 2. IMAGERY GUARD ---
    # Prevent "blind" surveys by ensuring a background layer (Bing, Esri, etc.) is visible.
    active_layer_name = None
    for l in MainApplication.getLayerManager().getLayers():
        # Skip OSM Data layers, look for imagery/WMS layers
        if isinstance(l, OsmDataLayer):
            continue
        if l.isVisible():
            active_layer_name = l.getName()

    if active_layer_name is None:
        warn_msg = "No active imagery layer detected!\n\nAccurate density estimation requires visible satellite imagery.\nDo you want to proceed anyway?"
        choice = JOptionPane.showConfirmDialog(
            None, warn_msg, "Missing Imagery Warning",
            JOptionPane.YES_NO_OPTION, JOptionPane.WARNING_MESSAGE
        )
        if choice != JOptionPane.YES_OPTION:
            return
        active_layer_name = "Unknown Source"

    # --- 3. USER INPUT (METADATA) ---
    img_date = JOptionPane.showInputDialog(
        None, "Imagery Date (YYYY-MM-DD):", "Metadata", JOptionPane.QUESTION_MESSAGE
    )
    if img_date is None:
        return # User clicked Cancel
        
    clean_date = img_date.strip() if img_date else "Unknown Date"
    
    # Construct the 'source' tag value
    source_tag_val = (
        "{} ({}); tree_density_estimator".format(active_layer_name, clean_date)
        if img_date
        else "{}; tree_density_estimator".format(active_layer_name)
    )

    options = ["Trees", "Bushes", "Heathland Plants"]
    choice = JOptionPane.showOptionDialog(
        None, "What are you counting?", "Vegetation Type",
        0, JOptionPane.QUESTION_MESSAGE, None, options, options[0]
    )
    if choice == -1:
        return

    # Configure visuals/naming based on selection
    # tuple: (Singular Name for UI, Tag Suffix for metadata)
    singular, tag_suffix = (
        ("Tree", "crown") if choice == 0
        else ("Bush", "shrub") if choice == 1
        else ("Plant", "shrub")
    )
    # Determine which map icon to use during counting (natural=tree vs natural=shrub)
    marker_natural = "tree" if choice == 0 else "shrub"

    # --- 4. INTERACTIVE TOOL (STATE MACHINE) ---
    # This class implements Java Event Listeners to handle Mouse/Keyboard on the map canvas.
    class PrecisionSampler(MouseListener, MouseMotionListener, KeyListener):
        def __init__(self):
            # State Machine: DRAW_BOX -> CALIBRATE -> COUNTING -> FINISHED
            self.step = "DRAW_BOX"
            
            # Runtime Data
            self.start_p = None       # LatLon where drag started
            self.sample_way = None    # The visual box on the map
            self.sample_nodes = []    # The 4 corners of the box
            self.label_node = None    # Floating text label
            self.temp_lines = []      # Lines drawn during calibration
            self.tree_nodes = []      # Individual items counted
            self.sample_poly = None   # Java AWT Shape for "contains" hit-testing
            self.finished = False     # Signal to main thread to wrap up
            
            # Calculation Data
            self.sample_area_sqm = 0.0
            self.avg_diameter = 0.0
            self.diameters = []
            
            # Audit Log Data
            self.log_box_dims = (0.0, 0.0)
            self.log_calibration_data = []

        def update_status(self, message):
            """Updates the bottom-left JOSM status bar."""
            MainApplication.getMap().statusLine.setHelpText(CONFIG["STATUS_PREFIX"] + message)

        def get_label_node(self, latlon, text):
            """Creates or updates a temporary floating text node on the map."""
            if self.label_node is None:
                self.label_node = Node(latlon)
                self.label_node.put("name", text)
                self.label_node.put("place", "point") # Force rendering in standard styles
                layer.data.addPrimitive(self.label_node)
            else:
                self.label_node.setCoor(latlon)
                self.label_node.put("name", text)
            return self.label_node

        def mousePressed(self, e):
            # START DRAWING
            if not e.isShiftDown():
                mv = MainApplication.getMap().mapView
                self.start_p = mv.getLatLon(e.getX(), e.getY())
                
                if self.step == "DRAW_BOX":
                    # Initialize the 4 corners of the sample box at start point
                    n1 = Node(self.start_p)
                    n2 = Node(self.start_p)
                    n3 = Node(self.start_p)
                    n4 = Node(self.start_p)
                    w = Way()
                    w.setNodes([n1, n2, n3, n4, n1]) # Close the loop
                    self.sample_nodes = [n1, n2, n3, n4]
                    self.sample_way = w
                    
                    # Add to JOSM data layer so they become visible
                    for n in self.sample_nodes:
                        layer.data.addPrimitive(n)
                    layer.data.addPrimitive(w)

        def mouseDragged(self, e):
            # LIVE VISUALS
            mv = MainApplication.getMap().mapView
            curr_p = mv.getLatLon(e.getX(), e.getY())
            
            if self.step == "DRAW_BOX" and self.start_p and self.sample_way:
                # Calculate Distance and round to configured precision
                w_dist = round_to_snap(
                    self.start_p.greatCircleDistance(LatLon(self.start_p.lat(), curr_p.lon()))
                )
                h_dist = round_to_snap(
                    self.start_p.greatCircleDistance(LatLon(curr_p.lat(), self.start_p.lon()))
                )
                
                # Visual update only (Final geometric snap happens on release)
                self.sample_nodes[1].setCoor(LatLon(self.start_p.lat(), curr_p.lon()))
                self.sample_nodes[2].setCoor(curr_p)
                self.sample_nodes[3].setCoor(LatLon(curr_p.lat(), self.start_p.lon()))
                
                txt = "{:.1f}m x {:.1f}m".format(w_dist, h_dist)
                self.get_label_node(curr_p, txt)
                self.update_status("Drawing Sample Box: " + txt)
                layer.invalidate() # Force JOSM to redraw canvas
                
            elif self.step == "CALIBRATE" and self.start_p:
                dist = self.start_p.greatCircleDistance(curr_p)
                self.update_status("Measuring Diameter: {:.1f}m".format(dist))

        def mouseReleased(self, e):
            # COMMIT ACTION
            mv = MainApplication.getMap().mapView
            if not self.start_p:
                return
            end_p = mv.getLatLon(e.getX(), e.getY())
            p1 = self.start_p
            self.start_p = None

            # Logic wrapped in inner function to pass to SwingUtilities
            def process_release():
                mv.requestFocusInWindow() # Fix for macOS focus loss
                
                if self.step == "DRAW_BOX":
                    # --- BOX FINALIZATION LOGIC ---
                    start_lat = self.sample_nodes[0].coor.lat()
                    start_lon = self.sample_nodes[0].coor.lon()
                    
                    # 1. Calculate raw dimensions
                    w_raw = self.sample_nodes[0].coor.greatCircleDistance(LatLon(start_lat, end_p.lon()))
                    h_raw = self.sample_nodes[0].coor.greatCircleDistance(LatLon(end_p.lat(), start_lon))
                    
                    # 2. Round to configured precision
                    final_w = round_to_snap(w_raw)
                    final_h = round_to_snap(h_raw)
                    
                    # 3. GEOMETRIC SNAP: 
                    # Re-calculate exact corner coordinates based on the rounded meters.
                    # This ensures the mathematical area matches the visual label perfectly.                                                                        
                    self.sample_area_sqm = final_w * final_h
                    
                    # --- SAFETY GUARD: PREVENT 0x0m BOX ---
                    if self.sample_area_sqm < 1.0:
                        # If user just clicked or barely dragged, cleanup and let them retry
                        for n in self.sample_way.getNodes():
                            layer.data.removePrimitive(n)
                        layer.data.removePrimitive(self.sample_way)
                        if self.label_node:
                            layer.data.removePrimitive(self.label_node)
                            self.label_node = None
                        
                        self.sample_way = None
                        self.sample_nodes = []
                        layer.invalidate()
                        JOptionPane.showMessageDialog(None, "Area too small (0x0m). Please drag to create a box.")
                        return # Exit here, do not transition to CALIBRATE
                    
                    # If Valid: Proceed to setup box
                    self.log_box_dims = (final_w, final_h)
                    
                    # Determine Bearings (East/West, North/South)
                    b_w = math.radians(90) if end_p.lon() > start_lon else math.radians(270)
                    b_h = math.radians(180) if end_p.lat() < start_lat else math.radians(0)
                    
                    # Project corners
                    l2, o2 = project_point(start_lat, start_lon, final_w, b_w)
                    self.sample_nodes[1].setCoor(LatLon(l2, o2))
                    
                    l4, o4 = project_point(start_lat, start_lon, final_h, b_h)
                    self.sample_nodes[3].setCoor(LatLon(l4, o4))
                    
                    l3, o3 = project_point(l4, o4, final_w, b_w)
                    self.sample_nodes[2].setCoor(LatLon(l3, o3))
                    
                    # Create Hit-Test Polygon (Path2D) for checking clicks later
                    poly = Path2D.Double()
                    nodes = self.sample_way.getNodes()
                    poly.moveTo(nodes[0].coor.lat(), nodes[0].coor.lon())
                    for i in range(1, 4):
                        poly.lineTo(nodes[i].coor.lat(), nodes[i].coor.lon())
                    poly.closePath()
                    self.sample_poly = poly
                    
                    # Transition State
                    self.step = "CALIBRATE"
                    
                    # --- HELP DIALOG ---
                    help_msg = (
                        "Box: {:.1f}m x {:.1f}m ({:.1f} m2).\n"
                        "Next: Measure average {} diameter.\n\n"
                        "INSTRUCTIONS:\n"
                        "1. CLICK+DRAG from one edge of a {} to the other.\n"
                        "2. Repeat a few times to improve accuracy.\n"
                        "3. Press DELETE to undo last measurement."
                    ).format(final_w, final_h, self.sample_area_sqm, singular, singular)
                    
                    JOptionPane.showMessageDialog(None, help_msg)
                        
                elif self.step == "CALIBRATE":
                    # --- DIAMETER MEASUREMENT LOGIC ---
                    dist = p1.greatCircleDistance(end_p)
                    if dist > CONFIG["CLICK_TOLERANCE"]: # Ignore accidental micro-clicks
                        self.diameters.append(dist)
                        self.log_calibration_data.append((p1.lat(), p1.lon(), end_p.lat(), end_p.lon(), dist))
                        
                        # Draw temporary measurement line
                        l1 = Node(p1); l2 = Node(end_p)
                        line = Way(); line.setNodes([l1, l2])
                        lbl = Node(end_p); lbl.put("name", "{:.1f}m".format(dist)); lbl.put("place", "point")
                        
                        layer.data.addPrimitive(l1); layer.data.addPrimitive(l2)
                        layer.data.addPrimitive(line); layer.data.addPrimitive(lbl)
                        self.temp_lines.append((line, l1, l2, lbl))
                        
                        avg = sum(self.diameters) / len(self.diameters)
                        self.update_status("Avg: {:.1f}m (n={}) | ENTER to start counting.".format(avg, len(self.diameters)))
                        layer.invalidate()

            # Execute safely on the Event Dispatch Thread (EDT)
            SwingUtilities.invokeLater(process_release)

        def mouseClicked(self, e):
            # COUNTING LOGIC (Shift + Click)
            if self.step == "COUNTING" and e.isShiftDown():
                mv = MainApplication.getMap().mapView
                ll = mv.getLatLon(e.getX(), e.getY())
                
                # Only allow points strictly inside the sample box
                if self.sample_poly.contains(ll.lat(), ll.lon()):
                    node = Node(ll)
                    node.put("name", str(len(self.tree_nodes) + 1)) # Visual Counter
                    node.put("natural", marker_natural)             # Icon type
                    layer.data.addPrimitive(node)
                    self.tree_nodes.append(node)
                    self.update_status("Count: {} | ENTER to finish".format(len(self.tree_nodes)))
                    layer.invalidate()

        def keyPressed(self, e):
            # STATE TRANSITIONS
            if e.getKeyCode() == 10: # Enter Key
                if self.step == "CALIBRATE" and self.diameters:
                    # Finish Calibration -> Start Counting
                    self.avg_diameter = sum(self.diameters) / len(self.diameters)
                    
                    # Cleanup UI
                    if self.label_node:
                        layer.data.removePrimitive(self.label_node)
                        self.label_node = None
                    for l, n1, n2, lb in self.temp_lines:
                        layer.data.removePrimitive(l); layer.data.removePrimitive(n1)
                        layer.data.removePrimitive(n2); layer.data.removePrimitive(lb)
                    self.temp_lines = []
                    
                    self.step = "COUNTING"
                    JOptionPane.showMessageDialog(None, "Now SHIFT+CLICK every {} inside the box.".format(singular))
                    self.update_status("SHIFT+CLICK to count.")
                    layer.invalidate()
                    
                elif self.step == "COUNTING":
                    # Finish Counting -> End Script
                    self.finished = True
                    
            elif e.getKeyCode() in [8, 127]: # Backspace / Delete
                # --- UNDO LOGIC ---
                if self.step == "CALIBRATE" and self.temp_lines:
                    # Remove last measurement
                    line, n1, n2, lb = self.temp_lines.pop()
                    self.diameters.pop()
                    self.log_calibration_data.pop()
                    
                    # Clean visuals
                    layer.data.removePrimitive(line)
                    layer.data.removePrimitive(n1)
                    layer.data.removePrimitive(n2)
                    layer.data.removePrimitive(lb)
                    
                    # Update status
                    if self.diameters:
                        avg = sum(self.diameters) / len(self.diameters)
                        self.update_status("Avg: {:.1f}m (n={})".format(avg, len(self.diameters)))
                    else:
                        self.update_status("Measure diameter of {}s (Drag)".format(singular))
                    layer.invalidate()

                elif self.step == "COUNTING" and self.tree_nodes:
                    # Remove last counted tree
                    layer.data.removePrimitive(self.tree_nodes.pop())
                    self.update_status("Count: {} | ENTER to finish".format(len(self.tree_nodes)))
                    layer.invalidate()

        # Unused Interface Methods (Required by Java Interface)
        def mouseMoved(self, e): pass
        def mouseEntered(self, e): pass
        def mouseExited(self, e): pass
        def keyReleased(self, e): pass
        def keyTyped(self, e): pass

    # --- 5. INITIALIZE TOOL ---
    tool = PrecisionSampler()
    view = MainApplication.getMap().mapView
    view.addMouseListener(tool)
    view.addMouseMotionListener(tool)
    view.addKeyListener(tool)
    view.requestFocusInWindow()

    # --- 6. BACKGROUND MONITOR (THREAD) ---
    # Python threads prevent blocking JOSM's UI while we wait for the user to finish.
    def monitor():
        while not tool.finished:
            time.sleep(0.1)
            
        # Cleanup Listeners
        view.removeMouseListener(tool)
        view.removeMouseMotionListener(tool)
        view.removeKeyListener(tool)

        def finalize():
            # --- 7. FINAL CALCULATIONS & TAGGING ---
            layer.data.beginUpdate() # Batch operation for undo buffer
            try:
                count = len(tool.tree_nodes)
                if count > 0:
                    # A. EXTRAPOLATION
                    indiv_area = math.pi * ((tool.avg_diameter / 2) ** 2)
                    density_ratio = float(count) / tool.sample_area_sqm
                    est_total = int(density_ratio * total_area)
                    
                    # Mean Inter-Tree Distance Formula: d = sqrt(1 / density)
                    avg_spacing = math.sqrt(1.0 / density_ratio)
                    
                    # Canopy % Logic (Rounded to nearest 5%)
                    canopy_pc = min(100, int(round(((est_total * indiv_area) / total_area) * 100 / 5.0) * 5))
                    
                    # B. FAO DENSITY CLASSIFICATION
                    density_class = (
                        "very_dense" if canopy_pc >= CONFIG["DENSITY_VERY_DENSE"]
                        else "dense" if canopy_pc >= CONFIG["DENSITY_DENSE"]
                        else "open" if canopy_pc >= CONFIG["DENSITY_OPEN"]
                        else "scattered"
                    )

                    final_tags = {
                        "wood:density": density_class,
                        "canopy": str(canopy_pc) + "%",
                        "est:stem_count": str(est_total),
                        "est:avg_{}".format(tag_suffix): "{:.1f}m".format(tool.avg_diameter),
                        "est:avg_spacing": "{:.1f}m".format(avg_spacing),
                        "est:source_area": str(round(total_area, 1)),
                        "source": source_tag_val,
                    }

                    # --- SMART SUGGESTION LOGIC ---
                    perform_save = True
                    suggestion_note = "None"
                    curr_nat = target.get("natural")
                    curr_land = target.get("landuse")

                    # Metadata for log
                    surveyed_type_str = "None"
                    if curr_nat: surveyed_type_str = "natural=" + curr_nat
                    elif curr_land: surveyed_type_str = "landuse=" + curr_land

                    # Suggest: Scrub -> Wood?
                    if density_class in ["dense", "very_dense"] and curr_nat == "scrub":
                        msg = "Density is {}% ({}).\nSuggest changing natural=scrub to natural=wood?".format(canopy_pc, density_class)
                        res = JOptionPane.showConfirmDialog(None, msg, "Smart Suggestion", JOptionPane.YES_NO_CANCEL_OPTION)
                        if res == JOptionPane.YES_OPTION:
                            final_tags["natural"] = "wood"
                            suggestion_note = "Accepted: Changed scrub -> wood"
                        elif res == JOptionPane.CANCEL_OPTION or res == -1:
                            perform_save = False

                    # Suggest: Wood -> Scrub?
                    elif density_class in ["scattered", "open"] and curr_nat == "wood" and curr_land != "forest":
                        msg = "Density is {}% ({}).\nSuggest changing natural=wood to natural=scrub?".format(canopy_pc, density_class)
                        res = JOptionPane.showConfirmDialog(None, msg, "Smart Suggestion", JOptionPane.YES_NO_CANCEL_OPTION)
                        if res == JOptionPane.YES_OPTION:
                            final_tags["natural"] = "scrub"
                            suggestion_note = "Accepted: Changed wood -> scrub"
                        elif res == JOptionPane.CANCEL_OPTION or res == -1:
                            perform_save = False

                    if perform_save:
                        for k, v in final_tags.items():
                            target.put(k, v)
                        
                        # --- LOG GENERATION ---
                        import datetime
                        timestamp_str = str(int(time.time()))

                        log = "=========================================================================\n"
                        log += " TREE DENSITY SURVEY LOG\n"
                        log += " Script: Tree Density Estimator v{}\n".format(VERSION)
                        log += " Author: EverydayMapper (OSM)\n"
                        log += " Source: https://github.com/EverydayMapper/josm-tree-density-estimator\n"
                        log += "=========================================================================\n\n"
                        log += "METADATA\n--------\n"
                        log += "Survey Date:       {}\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        log += "Imagery Source:    {}\n".format(active_layer_name)
                        log += "OSM Object ID:     {} ({})\n".format(target_id, target_type)
                        log += "Surveyed Type:     {}\n".format(surveyed_type_str)
                        log += "Target Area Size:  {:.1f} m2\n\n".format(total_area)
                        log += "SMART SUGGESTIONS\n-----------------\nStatus: {}\n\n".format(suggestion_note)
                        log += "RESULTING TAGS\n--------------\n"
                        for k, v in final_tags.items():
                            log += "{}: {}\n".format(k, v)
                        log += "\nAPPENDIX\n--------\n[1] Sample Box: {:.1f}m x {:.1f}m | {:.1f}m2\n".format(
                            tool.log_box_dims[0], tool.log_box_dims[1], tool.sample_area_sqm)
                        log += "[2] Calibrations (Diameters):\n"
                        for i, d in enumerate(tool.log_calibration_data):
                            log += "  #{}: {:.1f}m | ({:.6f},{:.6f})->({:.6f},{:.6f})\n".format(
                                i + 1, d[4], d[0], d[1], d[2], d[3])
                        log += "[3] Tree Counters:\n"
                        for i, n in enumerate(tool.tree_nodes):
                            log += "  #{}: {:.6f}, {:.6f}\n".format(i + 1, n.coor.lat(), n.coor.lon())
                        
                        # --- SUMMARY DIALOG ---
                        summary = "ANALYSIS COMPLETE\n-----------------\nAvg Size: {:.1f}m\nAvg Spacing: {:.1f}m\nEst. Total: {}\nCanopy: {}%".format(
                            tool.avg_diameter, avg_spacing, est_total, canopy_pc)
                        JOptionPane.showMessageDialog(None, summary)
                        
                        # Log Save Prompt
                        if JOptionPane.showConfirmDialog(None, "Save log to text file?", "Save Log", JOptionPane.YES_NO_OPTION) == JOptionPane.YES_OPTION:
                            fc = JFileChooser()
                            fc.setSelectedFile(java.io.File("TreeSurvey_{}_{}.txt".format(target_id, timestamp_str)))
                            if fc.showSaveDialog(None) == JFileChooser.APPROVE_OPTION:
                                with open(fc.getSelectedFile().getAbsolutePath(), "w") as f:
                                    f.write(log)

                # --- CLEANUP TEMP VISUALS ---
                for n in tool.tree_nodes:
                    layer.data.removePrimitive(n)
                if tool.sample_way:
                    for n in tool.sample_way.getNodes():
                        layer.data.removePrimitive(n)
                    layer.data.removePrimitive(tool.sample_way)
                if tool.label_node:
                    layer.data.removePrimitive(tool.label_node)
                MainApplication.getMap().statusLine.setHelpText("")
                
            finally:
                layer.data.endUpdate() # Commit undo buffer
                layer.invalidate()

        # Execute final logic on UI Thread
        SwingUtilities.invokeLater(finalize)

    Thread(target=monitor).start()

# Run the script
run_analyzer()
