import math
import tkinter as tk
from model import UMLClass, UMLRelationship, RelationshipType

HEADER_HEIGHT = 25
ATTR_LINE_HEIGHT = 15
ATTR_PADDING = 5

def get_attr_height(uml_class):
    return max(20, len(uml_class.attributes) * ATTR_LINE_HEIGHT + ATTR_PADDING)

def get_angle(x1, y1, x2, y2):
    """Calculate angle of line from (x1, y1) to (x2, y2)"""
    return math.atan2(y2 - y1, x2 - x1)

def draw_arrowhead_generalization(canvas, x1, y1, x2, y2):
    """Draw a white triangle at (x2, y2)"""
    angle = get_angle(x1, y1, x2, y2)
    size = 15
    p1 = (x2, y2)
    p2 = (x2 - size * math.cos(angle - math.pi/6), y2 - size * math.sin(angle - math.pi/6))
    p3 = (x2 - size * math.cos(angle + math.pi/6), y2 - size * math.sin(angle + math.pi/6))
    canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], fill="white", outline="black")

def draw_arrowhead_aggregation(canvas, x1, y1, x2, y2):
    """Draw a white diamond at (x2, y2)"""
    angle = get_angle(x1, y1, x2, y2)
    size = 12
    p1 = (x2, y2)
    p2 = (x2 - size * math.cos(angle - math.pi/6), y2 - size * math.sin(angle - math.pi/6))
    p4 = (x2 - size * math.cos(angle + math.pi/6), y2 - size * math.sin(angle + math.pi/6))
    # Calculate p3 to complete the diamond
    p3 = (p2[0] + p4[0] - x2, p2[1] + p4[1] - y2)
    canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1], fill="white", outline="black")

def draw_arrowhead_composition(canvas, x1, y1, x2, y2):
    """Draw a black diamond at (x2, y2)"""
    angle = get_angle(x1, y1, x2, y2)
    size = 12
    p1 = (x2, y2)
    p2 = (x2 - size * math.cos(angle - math.pi/6), y2 - size * math.sin(angle - math.pi/6))
    p4 = (x2 - size * math.cos(angle + math.pi/6), y2 - size * math.sin(angle + math.pi/6))
    p3 = (p2[0] + p4[0] - x2, p2[1] + p4[1] - y2)
    canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1], fill="black", outline="black")

def draw_arrowhead_dependency(canvas, x1, y1, x2, y2):
    """Draw an open arrow (V-shape) at (x2, y2)"""
    angle = get_angle(x1, y1, x2, y2)
    size = 15
    p2 = (x2 - size * math.cos(angle - math.pi/6), y2 - size * math.sin(angle - math.pi/6))
    p3 = (x2 - size * math.cos(angle + math.pi/6), y2 - size * math.sin(angle + math.pi/6))
    canvas.create_line(x2, y2, p2[0], p2[1], fill="black")
    canvas.create_line(x2, y2, p3[0], p3[1], fill="black")

def get_class_center(uml_class):
    """Return the center (x, y) of the class box"""
    return (uml_class.x + uml_class.width / 2, uml_class.y + uml_class.height / 2)

def calculate_intersection(x1, y1, x2, y2, bx1, by1, bx2, by2):
    """Find intersection of line (x1,y1)-(x2,y2) with box (bx1,by1)-(bx2,by2)
    Assuming (x2,y2) is inside the box and (x1,y1) is outside."""
    if x2 == x1: # Vertical line
        if y1 < by1:
            return (x2, by1)
        return (x2, by2)
    
    m = (y2 - y1) / (x2 - x1)
    
    # Top edge: y = by1
    if y1 < by1:
        ix = (by1 - y1) / m + x1
        if bx1 <= ix <= bx2:
            return (ix, by1)
    # Bottom edge: y = by2
    if y1 > by2:
        ix = (by2 - y1) / m + x1
        if bx1 <= ix <= bx2:
            return (ix, by2)
    # Left edge: x = bx1
    if x1 < bx1:
        iy = m * (bx1 - x1) + y1
        if by1 <= iy <= by2:
            return (bx1, iy)
    # Right edge: x = bx2
    if x1 > bx2:
        iy = m * (bx2 - x1) + y1
        if by1 <= iy <= by2:
            return (bx2, iy)
        
    return (x2, y2)

def draw_class_box(canvas, uml_class):
    """Draw a class box with 3 compartments"""
    x, y, w, h = uml_class.x, uml_class.y, uml_class.width, uml_class.height
    
    # Draw main box
    canvas.create_rectangle(x, y, x + w, y + h, fill="white", outline="black")
    
    # Compartment heights
    header_h = HEADER_HEIGHT
    calculated_attr_h = get_attr_height(uml_class)
    minimal_ops_space = 20
    
    # Constrain attr_h so it doesn't exceed total height
    attr_h = min(calculated_attr_h, h - header_h - minimal_ops_space)
    if attr_h < 0:
        attr_h = 0
    
    # Ensure they don't exceed total height or just draw lines
    # For a basic implementation, we just draw the lines at these offsets
    canvas.create_line(x, y + header_h, x + w, y + header_h, fill="black")
    canvas.create_line(x, y + header_h + attr_h, x + w, y + header_h + attr_h, fill="black")
    
    # Name
    canvas.create_text(x + w/2, y + header_h/2, text=uml_class.name, font=("Arial", 10, "bold"))
    
    # Attributes
    curr_y = y + header_h + 5
    for attr in uml_class.attributes:
        if curr_y + ATTR_LINE_HEIGHT > y + header_h + attr_h:
            break
        canvas.create_text(x + 5, curr_y, text=attr, anchor="nw", font=("Arial", 9))
        curr_y += ATTR_LINE_HEIGHT
        
    # Operations
    curr_y = y + header_h + attr_h + 5
    for op in uml_class.operations:
        if curr_y + 15 > y + h:
            break
        canvas.create_text(x + 5, curr_y, text=op, anchor="nw", font=("Arial", 9))
        curr_y += 15

def draw_relationship_line(canvas, relationship):
    """Draw a line between two classes with correct arrowheads"""
    src = relationship.source
    tgt = relationship.target
    rel_type = relationship.type
    
    sc = get_class_center(src)
    tc = get_class_center(tgt)
    
    # Intersection points
    target_point = calculate_intersection(sc[0], sc[1], tc[0], tc[1], 
                                         tgt.x, tgt.y, tgt.x + tgt.width, tgt.y + tgt.height)
    source_point = calculate_intersection(tc[0], tc[1], sc[0], sc[1], 
                                         src.x, src.y, src.x + src.width, src.y + src.height)
    
    x1, y1 = source_point
    x2, y2 = target_point
    
    dash = None
    if rel_type in [RelationshipType.DEPENDENCY, RelationshipType.REALIZATION]:
        dash = (5, 5)
        
    canvas.create_line(x1, y1, x2, y2, dash=dash, fill="black")
    
    if rel_type in (RelationshipType.GENERALIZATION, RelationshipType.REALIZATION):
        draw_arrowhead_generalization(canvas, x1, y1, x2, y2)
    elif rel_type == RelationshipType.AGGREGATION:
        draw_arrowhead_aggregation(canvas, x1, y1, x2, y2)
    elif rel_type == RelationshipType.COMPOSITION:
        draw_arrowhead_composition(canvas, x1, y1, x2, y2)
    elif rel_type == RelationshipType.DEPENDENCY:
        draw_arrowhead_dependency(canvas, x1, y1, x2, y2)
