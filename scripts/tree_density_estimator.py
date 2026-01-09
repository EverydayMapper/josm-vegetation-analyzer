# ==============================================================================
# Tree Density Estimator
# Version: 1.4.5
# Date: 2026-01-09
# Author: EverydayMapper (OSM)
# License: MIT
# 
# UPDATE v1.4.5:
# - FIXED: Restored the "Missing Imagery" check. The script now warns the user
#   if no background imagery layer is detected before starting the survey.
# ==============================================================================

import math
import time
import os
from threading import Thread
from java.awt.event import MouseListener, MouseMotionListener, KeyListener
from java.awt.geom import Path2D 
from javax.swing import JOptionPane, SwingUtilities, JFileChooser
from org.openstreetmap.josm.gui import MainApplication
from org.openstreetmap.josm.data.osm import Node, Way
from org.openstreetmap.josm.tools import Geometry
from org.openstreetmap.josm.data.coor import LatLon
from org.openstreetmap.josm.gui.layer import OsmDataLayer

def project_point(start_lat, start_lon, dist_m, bearing_rad):
    R = 6378137.0 
    lat1 = math.radians(start_lat)
    lon1 = math.radians(start_lon)
    lat2 = math.asin(math.sin(lat1) * math.cos(dist_m / R) +
                     math.cos(lat1) * math.sin(dist_m / R) * math.cos(bearing_rad))
    lon2 = lon1 + math.atan2(math.sin(bearing_rad) * math.sin(dist_m / R) * math.cos(lat1),
                             math.cos(dist_m / R) - math.sin(lat1) * math.sin(lat2))
    return math.degrees(lat2), math.degrees(lon2)

def round_to_half(value):
    return round(value * 2) / 2.0

def run_analyzer():
    layer = MainApplication.getLayerManager().getEditLayer()
    if not layer or not layer.data: return
    selection = layer.data.getSelected()
    if selection.isEmpty():
        JOptionPane.showMessageDialog(None, "Select the main area polygon first.")
        return
    
    target = selection.iterator().next()
    total_area = abs(Geometry.computeArea(target))
    target_id = target.getId()
    target_type = "Way" if isinstance(target, Way) else "Relation"

    # --- IMAGERY DETECTION & CHECK (FIXED v1.4.5) ---
    active_layer_name = None
    for l in MainApplication.getLayerManager().getLayers():
        if isinstance(l, OsmDataLayer): continue
        if l.isVisible(): active_layer_name = l.getName()
    
    # If no imagery is found, warn the user
    if active_layer_name is None:
        warn_msg = "No active imagery layer detected!\n\nAccurate density estimation requires visible satellite imagery.\nDo you want to proceed anyway?"
        choice = JOptionPane.showConfirmDialog(None, warn_msg, "Missing Imagery Warning", JOptionPane.YES_NO_OPTION, JOptionPane.WARNING_MESSAGE)
        if choice != JOptionPane.YES_OPTION:
            return
        active_layer_name = "Unknown Source"
    # ------------------------------------------------

    img_date = JOptionPane.showInputDialog(None, "Imagery Date (YYYY-MM-DD):", "Metadata", JOptionPane.QUESTION_MESSAGE)
    if img_date is None: return
    clean_date = img_date.strip() if img_date else "Unknown Date"
    source_tag_val = "{} ({}); tree_density_estimator".format(active_layer_name, clean_date) if img_date else "{}; tree_density_estimator".format(active_layer_name)

    options = ["Trees", "Bushes", "Heathland Plants"]
    choice = JOptionPane.showOptionDialog(None, "What are you counting?", "Vegetation Type", 0, JOptionPane.QUESTION_MESSAGE, None, options, options[0])
    if choice == -1: return
    
    singular, tag_suffix = ("Tree", "crown") if choice == 0 else ("Bush", "shrub") if choice == 1 else ("Plant", "shrub")
    marker_natural = "tree" if choice == 0 else "shrub"

    class PrecisionSampler(MouseListener, MouseMotionListener, KeyListener):
        def __init__(self):
            self.step = "DRAW_BOX"
            self.start_p = None
            self.sample_way = None
            self.sample_nodes = [] 
            self.label_node = None 
            self.temp_lines = [] 
            self.tree_nodes = [] 
            self.sample_poly = None
            self.finished = False
            self.sample_area_sqm = 0.0
            self.avg_diameter = 0.0
            self.diameters = []
            self.log_box_dims = (0.0, 0.0) 
            self.log_calibration_data = [] 

        def update_status(self, message):
            MainApplication.getMap().statusLine.setHelpText("[v1.4.5] " + message)

        def get_label_node(self, latlon, text):
            if self.label_node is None:
                self.label_node = Node(latlon); self.label_node.put("name", text); self.label_node.put("place", "point") 
                layer.data.addPrimitive(self.label_node)
            else: self.label_node.setCoor(latlon); self.label_node.put("name", text)
            return self.label_node

        def mousePressed(self, e):
            if not e.isShiftDown():
                mv = MainApplication.getMap().mapView
                self.start_p = mv.getLatLon(e.getX(), e.getY())
                if self.step == "DRAW_BOX":
                    n1=Node(self.start_p); n2=Node(self.start_p); n3=Node(self.start_p); n4=Node(self.start_p)
                    w = Way(); w.setNodes([n1, n2, n3, n4, n1])
                    self.sample_nodes = [n1, n2, n3, n4]; self.sample_way = w
                    for n in self.sample_nodes: layer.data.addPrimitive(n)
                    layer.data.addPrimitive(w)

        def mouseDragged(self, e):
            mv = MainApplication.getMap().mapView
            curr_p = mv.getLatLon(e.getX(), e.getY())
            if self.step == "DRAW_BOX" and self.start_p and self.sample_way:
                w_dist = round_to_half(self.start_p.greatCircleDistance(LatLon(self.start_p.lat(), curr_p.lon())))
                h_dist = round_to_half(self.start_p.greatCircleDistance(LatLon(curr_p.lat(), self.start_p.lon())))
                self.sample_nodes[1].setCoor(LatLon(self.start_p.lat(), curr_p.lon()))
                self.sample_nodes[2].setCoor(curr_p)
                self.sample_nodes[3].setCoor(LatLon(curr_p.lat(), self.start_p.lon()))
                txt = "{:.1f}m x {:.1f}m".format(w_dist, h_dist)
                self.get_label_node(curr_p, txt); self.update_status("Drawing Sample Box: " + txt); layer.invalidate() 
            elif self.step == "CALIBRATE" and self.start_p:
                dist = self.start_p.greatCircleDistance(curr_p)
                self.update_status("Measuring Diameter: {:.1f}m".format(dist))

        def mouseReleased(self, e):
            mv = MainApplication.getMap().mapView
            if not self.start_p: return
            end_p = mv.getLatLon(e.getX(), e.getY()); p1 = self.start_p; self.start_p = None
            def process_release():
                mv.requestFocusInWindow()
                if self.step == "DRAW_BOX":
                    start_lat = self.sample_nodes[0].coor.lat(); start_lon = self.sample_nodes[0].coor.lon()
                    w_raw = self.sample_nodes[0].coor.greatCircleDistance(LatLon(start_lat, end_p.lon()))
                    h_raw = self.sample_nodes[0].coor.greatCircleDistance(LatLon(end_p.lat(), start_lon))
                    final_w = round_to_half(w_raw); final_h = round_to_half(h_raw)
                    self.sample_area_sqm = final_w * final_h
                    self.log_box_dims = (final_w, final_h)
                    b_w = math.radians(90) if end_p.lon() > start_lon else math.radians(270)
                    b_h = math.radians(180) if end_p.lat() < start_lat else math.radians(0)
                    l2, o2 = project_point(start_lat, start_lon, final_w, b_w); self.sample_nodes[1].setCoor(LatLon(l2, o2))
                    l4, o4 = project_point(start_lat, start_lon, final_h, b_h); self.sample_nodes[3].setCoor(LatLon(l4, o4))
                    l3, o3 = project_point(l4, o4, final_w, b_w); self.sample_nodes[2].setCoor(LatLon(l3, o3))
                    poly = Path2D.Double(); nodes = self.sample_way.getNodes(); poly.moveTo(nodes[0].coor.lat(), nodes[0].coor.lon())
                    for i in range(1, 4): poly.lineTo(nodes[i].coor.lat(), nodes[i].coor.lon())
                    poly.closePath(); self.sample_poly = poly; self.step = "CALIBRATE"
                    JOptionPane.showMessageDialog(None, "Box: {:.1f}m x {:.1f}m ({:.1f} m2).\nNext: Measure {} diameters.".format(final_w, final_h, self.sample_area_sqm, singular))
                elif self.step == "CALIBRATE":
                    dist = p1.greatCircleDistance(end_p)
                    if dist > 0.05:
                        self.diameters.append(dist); self.log_calibration_data.append((p1.lat(), p1.lon(), end_p.lat(), end_p.lon(), dist))
                        l1=Node(p1); l2=Node(end_p); line=Way(); line.setNodes([l1, l2]); lbl=Node(end_p); lbl.put("name", "{:.1f}m".format(dist)); lbl.put("place", "point")
                        layer.data.addPrimitive(l1); layer.data.addPrimitive(l2); layer.data.addPrimitive(line); layer.data.addPrimitive(lbl); self.temp_lines.append((line, l1, l2, lbl))
                        self.update_status("Avg: {:.1f}m (n={}) | ENTER to start counting.".format(sum(self.diameters)/len(self.diameters), len(self.diameters))); layer.invalidate()
            SwingUtilities.invokeLater(process_release)

        def mouseClicked(self, e):
            if self.step == "COUNTING" and e.isShiftDown():
                mv = MainApplication.getMap().mapView; ll = mv.getLatLon(e.getX(), e.getY())
                if self.sample_poly.contains(ll.lat(), ll.lon()):
                    node = Node(ll); node.put("name", str(len(self.tree_nodes)+1)); node.put("natural", marker_natural)
                    layer.data.addPrimitive(node); self.tree_nodes.append(node)
                    self.update_status("Count: {} | ENTER to finish".format(len(self.tree_nodes))); layer.invalidate()

        def keyPressed(self, e):
            if e.getKeyCode() == 10: 
                if self.step == "CALIBRATE" and self.diameters:
                    self.avg_diameter = sum(self.diameters) / len(self.diameters)
                    if self.label_node: layer.data.removePrimitive(self.label_node); self.label_node = None
                    for l, n1, n2, lb in self.temp_lines: layer.data.removePrimitive(l); layer.data.removePrimitive(n1); layer.data.removePrimitive(n2); layer.data.removePrimitive(lb)
                    self.temp_lines = []; self.step = "COUNTING"; JOptionPane.showMessageDialog(None, "Now SHIFT+CLICK every {} inside the box.".format(singular)); self.update_status("SHIFT+CLICK to count."); layer.invalidate()
                elif self.step == "COUNTING": self.finished = True
            elif e.getKeyCode() in [8, 127]:
                if self.step == "COUNTING" and self.tree_nodes: layer.data.removePrimitive(self.tree_nodes.pop()); layer.invalidate()

        def mouseMoved(self, e): pass
        def mouseEntered(self, e): pass
        def mouseExited(self, e): pass
        def keyReleased(self, e): pass
        def keyTyped(self, e): pass

    tool = PrecisionSampler(); view = MainApplication.getMap().mapView; view.addMouseListener(tool); view.addMouseMotionListener(tool); view.addKeyListener(tool); view.requestFocusInWindow()

    def monitor():
        while not tool.finished: time.sleep(0.1)
        view.removeMouseListener(tool); view.removeMouseMotionListener(tool); view.removeKeyListener(tool)
        def finalize():
            layer.data.beginUpdate()
            try:
                count = len(tool.tree_nodes)
                if count > 0:
                    indiv_area = math.pi * ((tool.avg_diameter / 2)**2)
                    density_ratio = float(count) / tool.sample_area_sqm
                    est_total = int(density_ratio * total_area)
                    avg_spacing = math.sqrt(1.0 / density_ratio)
                    canopy_pc = min(100, int(round(((est_total * indiv_area) / total_area) * 100 / 5.0) * 5))
                    density_class = "very_dense" if canopy_pc >= 70 else "dense" if canopy_pc >= 40 else "open" if canopy_pc >= 10 else "scattered"
                    
                    final_tags = {
                        "wood:density": density_class, "canopy": str(canopy_pc) + "%", "est:stem_count": str(est_total),
                        "est:avg_{}".format(tag_suffix): "{:.1f}m".format(tool.avg_diameter),
                        "est:avg_spacing": "{:.1f}m".format(avg_spacing), "est:source_area": str(round(total_area, 1)), "source": source_tag_val
                    }

                    # --- SMART SUGGESTION LOGIC ---
                    perform_save = True
                    suggestion_note = "None"
                    curr_nat = target.get("natural")
                    curr_land = target.get("landuse")
                    
                    surveyed_type_str = "None"
                    if curr_nat: surveyed_type_str = "natural=" + curr_nat
                    elif curr_land: surveyed_type_str = "landuse=" + curr_land

                    if density_class in ["dense", "very_dense"] and curr_nat == "scrub":
                        msg = "Density is {}% ({}).\nSuggest changing natural=scrub to natural=wood?".format(canopy_pc, density_class)
                        res = JOptionPane.showConfirmDialog(None, msg, "Smart Suggestion", JOptionPane.YES_NO_CANCEL_OPTION)
                        if res == JOptionPane.YES_OPTION: 
                            final_tags["natural"] = "wood"
                            suggestion_note = "Accepted: Changed scrub -> wood"
                        elif res == JOptionPane.CANCEL_OPTION or res == -1: perform_save = False
                    
                    elif density_class in ["scattered", "open"] and curr_nat == "wood" and curr_land != "forest":
                        msg = "Density is {}% ({}).\nSuggest changing natural=wood to natural=scrub?".format(canopy_pc, density_class)
                        res = JOptionPane.showConfirmDialog(None, msg, "Smart Suggestion", JOptionPane.YES_NO_CANCEL_OPTION)
                        if res == JOptionPane.YES_OPTION: 
                            final_tags["natural"] = "scrub"
                            suggestion_note = "Accepted: Changed wood -> scrub"
                        elif res == JOptionPane.CANCEL_OPTION or res == -1: perform_save = False

                    if perform_save:
                        for k, v in final_tags.items(): target.put(k, v)
                        
                        import datetime
                        timestamp_str = str(int(time.time()))
                        
                        log = "=========================================================================\n"
                        log += " TREE DENSITY SURVEY LOG\n"
                        log += " Script: Tree Density Estimator v1.4.5\n"
                        log += " Author: EverydayMapper (OSM)\n"
                        log += "=========================================================================\n\n"
                        
                        log += "METADATA\n--------\n"
                        log += "Survey Date:       {}\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        log += "Imagery Source:    {}\n".format(active_layer_name)
                        log += "OSM Object ID:     {} ({})\n".format(target_id, target_type)
                        log += "Surveyed Type:     {}\n".format(surveyed_type_str)
                        log += "Target Area Size:  {:.1f} m2\n\n".format(total_area)
                        
                        log += "SMART SUGGESTIONS\n-----------------\nStatus: {}\n\n".format(suggestion_note)
                        
                        log += "RESULTING TAGS\n--------------\n"
                        for k, v in final_tags.items(): log += "{}: {}\n".format(k, v)
                        
                        log += "\nAPPENDIX\n--------\n[1] Sample Box: {:.1f}m x {:.1f}m | {:.1f}m2\n".format(tool.log_box_dims[0], tool.log_box_dims[1], tool.sample_area_sqm)
                        log += "[2] Calibrations (Diameters):\n"
                        for i, d in enumerate(tool.log_calibration_data): log += "  #{}: {:.1f}m | ({:.6f},{:.6f})->({:.6f},{:.6f})\n".format(i+1, d[4], d[0], d[1], d[2], d[3])
                        log += "[3] Tree Counters:\n"
                        for i, n in enumerate(tool.tree_nodes): log += "  #{}: {:.6f}, {:.6f}\n".format(i+1, n.coor.lat(), n.coor.lon())

                        summary = "ANALYSIS COMPLETE\n-----------------\nAvg Size: {:.1f}m\nAvg Spacing: {:.1f}m\nEst. Total: {}\nCanopy: {}%".format(tool.avg_diameter, avg_spacing, est_total, canopy_pc)
                        JOptionPane.showMessageDialog(None, summary)

                        if JOptionPane.showConfirmDialog(None, "Save log to text file?", "Save Log", JOptionPane.YES_NO_OPTION) == JOptionPane.YES_OPTION:
                            fc = JFileChooser(); 
                            fc.setSelectedFile(java.io.File("TreeSurvey_{}_{}.txt".format(target_id, timestamp_str)))
                            if fc.showSaveDialog(None) == JFileChooser.APPROVE_OPTION:
                                with open(fc.getSelectedFile().getAbsolutePath(), 'w') as f: f.write(log)

                for n in tool.tree_nodes: layer.data.removePrimitive(n)
                if tool.sample_way:
                    for n in tool.sample_way.getNodes(): layer.data.removePrimitive(n)
                    layer.data.removePrimitive(tool.sample_way)
                if tool.label_node: layer.data.removePrimitive(tool.label_node)
                MainApplication.getMap().statusLine.setHelpText("")
            finally: layer.data.endUpdate(); layer.invalidate()
        import java.io.File
        SwingUtilities.invokeLater(finalize)
    Thread(target=monitor).start()

run_analyzer()
