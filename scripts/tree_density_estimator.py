# ==============================================================================
# Tree Density Estimator
# Version: 1.2.1
# Date: 2026-01-04
# Author: EverydayMapper (OSM)
# License: MIT
# 
# Description:
# A statistical sampling tool for JOSM to estimate tree/scrub density and canopy 
# cover. Supports Closed Ways and Multipolygon Relations.
#
# NEW IN V1.2.1:
# - Improved Source Detection: Correctly identifies Bing, Mapbox, and local 
#   layers by checking visibility rather than keyword filters.
# - Metadata: Standardized 'source' tag: [Imagery] ([Date]); tree_density_estimator
# - Integrity: Added 'est:source_area' to help detect geometry-related bias.
# ==============================================================================

import math
from threading import Thread
from org.openstreetmap.josm.gui import MainApplication
from org.openstreetmap.josm.data.osm import Node, Way
from org.openstreetmap.josm.tools import Geometry
from org.openstreetmap.josm.data.coor import LatLon
from org.openstreetmap.josm.gui.layer import OsmDataLayer
from java.awt.event import MouseListener, KeyListener
from java.awt.geom import Path2D 
from javax.swing import JOptionPane, SwingUtilities

def run_analyzer():
    # 1. Start with Disclaimer
    disclaimer = ("PRECISION & SOURCE NOTICE:\n"
                  "- Best for 'Open' or 'Scattered' vegetation.\n"
                  "- Shift+Click to count (prevents accidental selection).\n"
                  "- Please verify imagery dates for accuracy!")
    JOptionPane.showMessageDialog(None, disclaimer, "Tool Disclaimer", JOptionPane.WARNING_MESSAGE)

    layer = MainApplication.getLayerManager().getEditLayer()
    if not layer or not layer.data: return
    selection = layer.data.getSelected()
    if selection.isEmpty():
        JOptionPane.showMessageDialog(None, "Select the main area polygon first.")
        return
    
    target = selection.iterator().next()
    try:
        total_area = abs(Geometry.computeArea(target))
    except:
        JOptionPane.showMessageDialog(None, "Invalid area geometry.")
        return

    # 2. Metadata & Imagery Source (FIXED V1.2.1)
    # We default to "Imagery" only if nothing else is found.
    active_layer_name = "Imagery"
    
    # Iterate through all layers to find the visible background (non-data) layer
    for l in MainApplication.getLayerManager().getLayers():
        # Skip the layer we are currently editing (Data Layer)
        if isinstance(l, OsmDataLayer):
            continue
        # If the layer is visible, we assume it is the source
        if l.isVisible():
            active_layer_name = l.getName()
            # We don't break here; if multiple are visible, usually the top-most 
            # (last in list) is the one the user sees.
            
    # Updated Date Prompt Logic
    date_prompt_msg = ("Date of Imagery (Optional)\n\n"
                       "Enter the capture date (YYYY-MM-DD) if known.\n"
                       "Leave blank if unknown.\n\n"
                       "Click OK to continue or Cancel to exit script.")
    
    img_date = JOptionPane.showInputDialog(None, date_prompt_msg, 
                                           "Imagery Metadata", JOptionPane.QUESTION_MESSAGE)
    
    # Graceful exit if Cancel is clicked
    if img_date is None:
        return
    
    # Updated Source Tag Standard
    if img_date and img_date.strip():
        imagery_source = "{} ({}); tree_density_estimator".format(active_layer_name, img_date.strip())
    else:
        imagery_source = "{}; tree_density_estimator".format(active_layer_name)

    options = ["Trees", "Bushes", "Heathland Plants"]
    choice = JOptionPane.showOptionDialog(None, "What are you counting?", "Vegetation Type",
                                          JOptionPane.DEFAULT_OPTION, JOptionPane.QUESTION_MESSAGE,
                                          None, options, options[0])
    if choice == -1: return
    singular, plural, tag_suffix = ("Tree", "Trees", "crown") if choice == 0 else ("Bush", "Bushes", "shrub") if choice == 1 else ("Plant", "Plants", "shrub")

    class PrecisionSampler(MouseListener, KeyListener):
        def __init__(self):
            self.step = "DRAW_BOX"
            self.start_p = None
            self.sample_way = None
            self.sample_poly = None
            self.diameters = []
            self.temp_lines = [] 
            self.tree_nodes = []
            self.finished = False
            self.sample_area_sqm = 0
            self.avg_diameter = 0

        def update_status(self, message):
            area_info = "| Area: {:.1f}m2 ".format(self.sample_area_sqm) if self.sample_area_sqm > 0 else ""
            MainApplication.getMap().statusLine.setHelpText("[Analyzer] " + area_info + "| " + message)

        def mousePressed(self, e):
            mv = MainApplication.getMap().mapView
            if not e.isShiftDown(): self.start_p = mv.getLatLon(e.getX(), e.getY())

        def mouseReleased(self, e):
            mv = MainApplication.getMap().mapView
            if not self.start_p: return
            end_p = mv.getLatLon(e.getX(), e.getY())
            
            if self.step == "DRAW_BOX":
                dist = self.start_p.greatCircleDistance(end_p)
                if dist < 1.0: return 
                n1 = Node(self.start_p); n2 = Node(LatLon(self.start_p.lat(), end_p.lon()))
                n3 = Node(end_p); n4 = Node(LatLon(end_p.lat(), self.start_p.lon()))
                self.sample_way = Way()
                self.sample_way.setNodes([n1, n2, n3, n4, n1])
                layer.data.addPrimitive(n1); layer.data.addPrimitive(n2); layer.data.addPrimitive(n3); layer.data.addPrimitive(n4); layer.data.addPrimitive(self.sample_way)
                self.sample_area_sqm = abs(Geometry.computeArea(self.sample_way))
                poly = Path2D.Double()
                poly.moveTo(n1.coor.lat(), n1.coor.lon()); poly.lineTo(n2.coor.lat(), n2.coor.lon()); poly.lineTo(n3.coor.lat(), n3.coor.lon()); poly.lineTo(n4.coor.lat(), n4.coor.lon()); poly.closePath()
                self.sample_poly = poly
                
                msg = ("Sample Area: {:.1f} m2\n\n"
                       "CALIBRATION STEP:\n"
                       "Drag your mouse from one side of a {} to the other to measure its diameter.\n"
                       "Measure 3-5 different ones for a better average, then press ENTER.").format(self.sample_area_sqm, singular)
                JOptionPane.showMessageDialog(None, msg)
                
                self.step = "CALIBRATE"
                self.start_p = None
                self.update_status("Drag across a {} crown, then ENTER.".format(singular))

            elif self.step == "CALIBRATE":
                dist = self.start_p.greatCircleDistance(end_p)
                if dist > 0.05:
                    self.diameters.append(dist)
                    self.avg_diameter = sum(self.diameters) / len(self.diameters)
                    self.update_status("Last: {:.2f}m | Avg: {:.2f}m (n={}) | ENTER".format(dist, self.avg_diameter, len(self.diameters)))
                    l1 = Node(self.start_p); l2 = Node(end_p); line = Way(); line.setNodes([l1, l2])
                    layer.data.addPrimitive(l1); layer.data.addPrimitive(l2); layer.data.addPrimitive(line)
                    self.temp_lines.append((line, l1, l2))
                self.start_p = None

        def mouseClicked(self, e):
            if self.step == "COUNTING" and e.isShiftDown():
                mv = MainApplication.getMap().mapView
                click_ll = mv.getLatLon(e.getX(), e.getY())
                if self.sample_poly and self.sample_poly.contains(click_ll.lat(), click_ll.lon()):
                    node = Node(click_ll); layer.data.addPrimitive(node); self.tree_nodes.append(node)
                    self.update_status("{} Counted: {} | ENTER to finish".format(plural, len(self.tree_nodes)))

        def keyPressed(self, e):
            if e.getKeyCode() == 10: 
                if self.step == "CALIBRATE" and self.diameters:
                    self.avg_diameter = sum(self.diameters) / len(self.diameters)
                    for line, n1, n2 in self.temp_lines: layer.data.removePrimitive(line); layer.data.removePrimitive(n1); layer.data.removePrimitive(n2)
                    self.temp_lines = []; self.step = "COUNTING"
                    self.update_status("SHIFT+CLICK to count {} inside the box.".format(plural))
                    JOptionPane.showMessageDialog(None, "Calibration Done: {:.2f}m\n\nNow SHIFT+CLICK every {} inside the sample box.".format(self.avg_diameter, singular))
                elif self.step == "COUNTING": self.finished = True
            elif e.getKeyCode() in [8, 127]: 
                if self.step == "CALIBRATE" and self.diameters:
                    self.diameters.pop(); line, n1, n2 = self.temp_lines.pop()
                    layer.data.removePrimitive(line); layer.data.removePrimitive(n1); layer.data.removePrimitive(n2)
                elif self.step == "COUNTING" and self.tree_nodes: layer.data.removePrimitive(self.tree_nodes.pop())

        def mouseEntered(self, e): pass
        def mouseExited(self, e): pass
        def keyReleased(self, e): pass
        def keyTyped(self, e): pass

    JOptionPane.showMessageDialog(None, "STEP 1: Draw your sample box area on the map.")
    tool = PrecisionSampler(); view = MainApplication.getMap().mapView
    view.addMouseListener(tool); view.addKeyListener(tool); view.requestFocusInWindow()

    def monitor():
        import time
        while not tool.finished: time.sleep(0.1)
        view.removeMouseListener(tool); view.removeKeyListener(tool)
        def finalize():
            layer.data.beginUpdate()
            try:
                count = len(tool.tree_nodes)
                if count > 0:
                    indiv_area = math.pi * ((tool.avg_diameter / 2)**2)
                    density_ratio = float(count) / tool.sample_area_sqm
                    est_total = int(density_ratio * total_area)
                    avg_spacing = math.sqrt(1.0 / density_ratio)
                    
                    canopy_pc = int(round(((est_total * indiv_area) / total_area) * 100 / 5.0) * 5)
                    canopy_pc = max(0, min(100, canopy_pc))
                    density_class = "very_dense" if canopy_pc >= 70 else "dense" if canopy_pc >= 40 else "open" if canopy_pc >= 10 else "scattered"
                    
                    target.put("wood:density", density_class)
                    target.put("canopy", str(canopy_pc) + "%")
                    target.put("est:stem_count", str(est_total))
                    target.put("est:avg_{}".format(tag_suffix), "{:.1f}m".format(tool.avg_diameter))
                    target.put("est:avg_spacing", "{:.1f}m".format(avg_spacing))
                    
                    # Added est:source_area in V1.2.1
                    target.put("est:source_area", str(round(total_area, 1)))
                    target.put("source", imagery_source)
                    
                    # Smart Suggestion Logic (scrub <-> wood)
                    current_tag = target.get("natural")
                    if density_class in ["dense", "very_dense"] and current_tag == "scrub":
                        change_msg = "Density is {}%.\nSuggest changing natural=scrub to natural=wood.\n\nProceed?".format(canopy_pc)
                        if JOptionPane.showConfirmDialog(None, change_msg) == JOptionPane.YES_OPTION:
                            target.put("natural", "wood")
                    elif density_class in ["scattered", "open"] and current_tag == "wood":
                        change_msg = "Density is {}%.\nSuggest changing natural=wood to natural=scrub.\n\nProceed?".format(canopy_pc)
                        if JOptionPane.showConfirmDialog(None, change_msg) == JOptionPane.YES_OPTION:
                            target.put("natural", "scrub")
                    
                    summary = ("ANALYSIS COMPLETE\n"
                               "-----------------\n"
                               "Avg Size: {:.1f}m\n"
                               "Avg Spacing: {:.1f}m\n"
                               "Est. Total: {}\n"
                               "Canopy Cover: {}%").format(tool.avg_diameter, avg_spacing, est_total, canopy_pc)
                    JOptionPane.showMessageDialog(None, summary)
                for n in tool.tree_nodes: layer.data.removePrimitive(n)
                if tool.sample_way:
                    nodes = tool.sample_way.getNodes()
                    layer.data.removePrimitive(tool.sample_way)
                    for n in nodes: layer.data.removePrimitive(n)
                MainApplication.getMap().statusLine.setHelpText("")
            finally: layer.data.endUpdate(); layer.invalidate()
        SwingUtilities.invokeLater(finalize)
    Thread(target=monitor).start()

run_analyzer()
