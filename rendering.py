import math
import tkinter as tk
from model import UMLClass, UMLRelationship, RelationshipType
import geometry
import relationship_logic

# Layout Constants
HEADER_FONT = ("Arial", 10, "bold")
CONTENT_FONT = ("Arial", 9)
HEADER_HEIGHT = 25
ATTR_LINE_HEIGHT = 18
ATTR_PADDING = 8
MIN_COMPARTMENT_HEIGHT = 20
MIN_WIDTH = 100

def get_attr_height(uml_class):
    return max(MIN_COMPARTMENT_HEIGHT, len(uml_class.attributes) * ATTR_LINE_HEIGHT + ATTR_PADDING)

def get_ops_height(uml_class):
    return max(MIN_COMPARTMENT_HEIGHT, len(uml_class.operations) * ATTR_LINE_HEIGHT + ATTR_PADDING)

def draw_arrowhead_generalization(canvas, x, y, angle):
    """Draw a white triangle at (x, y) with given angle"""
    size = 15
    p1 = (x, y)
    p2 = (x - size * math.cos(angle - math.pi/6), y - size * math.sin(angle - math.pi/6))
    p3 = (x - size * math.cos(angle + math.pi/6), y - size * math.sin(angle + math.pi/6))
    canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], fill="white", outline="black")

def draw_arrowhead_aggregation(canvas, x, y, angle):
    """Draw a white diamond at (x, y) with given angle"""
    size = 12
    p1 = (x, y)
    p2 = (x - size * math.cos(angle - math.pi/6), y - size * math.sin(angle - math.pi/6))
    p4 = (x - size * math.cos(angle + math.pi/6), y - size * math.sin(angle + math.pi/6))
    # Calculate p3 to complete the diamond
    p3 = (p2[0] + p4[0] - x, p2[1] + p4[1] - y)
    canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1], fill="white", outline="black")

def draw_arrowhead_composition(canvas, x, y, angle):
    """Draw a black diamond at (x, y) with given angle"""
    size = 12
    p1 = (x, y)
    p2 = (x - size * math.cos(angle - math.pi/6), y - size * math.sin(angle - math.pi/6))
    p4 = (x - size * math.cos(angle + math.pi/6), y - size * math.sin(angle + math.pi/6))
    p3 = (p2[0] + p4[0] - x, p2[1] + p4[1] - y)
    canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1], fill="black", outline="black")

def draw_arrowhead_dependency(canvas, x, y, angle):
    """Draw an open arrow (V-shape) at (x, y) with given angle"""
    size = 15
    p2 = (x - size * math.cos(angle - math.pi/6), y - size * math.sin(angle - math.pi/6))
    p3 = (x - size * math.cos(angle + math.pi/6), y - size * math.sin(angle + math.pi/6))
    canvas.create_line(x, y, p2[0], p2[1], fill="black")
    canvas.create_line(x, y, p3[0], p3[1], fill="black")

def draw_class_box(canvas, uml_class):
    """Draw a class box with 3 compartments"""
    x, y, w, h = uml_class.x, uml_class.y, uml_class.width, uml_class.height
    
    # Draw main box
    canvas.create_rectangle(x, y, x + w, y + h, fill="white", outline="black")
    
    # Compartment heights
    header_h = HEADER_HEIGHT
    attr_h = get_attr_height(uml_class)
    ops_h = get_ops_height(uml_class)
    
    # Draw horizontal lines for compartments
    canvas.create_line(x, y + header_h, x + w, y + header_h, fill="black")
    canvas.create_line(x, y + header_h + attr_h, x + w, y + header_h + attr_h, fill="black")
    
    # Name
    canvas.create_text(x + w/2, y + header_h/2, text=uml_class.name, font=HEADER_FONT)
    
    # Attributes
    curr_y = y + header_h + 5
    for attr in uml_class.attributes:
        if curr_y + ATTR_LINE_HEIGHT > y + header_h + attr_h:
            break
        canvas.create_text(x + 5, curr_y, text=attr, anchor="nw", font=CONTENT_FONT)
        curr_y += ATTR_LINE_HEIGHT
        
    # Operations
    curr_y = y + header_h + attr_h + 5
    for op in uml_class.operations:
        if curr_y + ATTR_LINE_HEIGHT > y + h:
            break
        canvas.create_text(x + 5, curr_y, text=op, anchor="nw", font=CONTENT_FONT)
        curr_y += ATTR_LINE_HEIGHT

def draw_relationship_line(canvas, relationship):
    """Draw a Bezier curve between two classes with correct arrowheads"""
    relationship_logic.initialize_relationship_handles(relationship)

    src = relationship.source
    tgt = relationship.target
    rel_type = relationship.type

    s_rect = relationship_logic.get_class_rect(src)
    t_rect = relationship_logic.get_class_rect(tgt)

    # 1. Start and End points
    if src == tgt:
        # Self-reference fixed points
        p0 = (s_rect[0] + s_rect[2] / 2, s_rect[1] + s_rect[3]) # Bottom center
        p3 = (s_rect[0] + s_rect[2], s_rect[1] + s_rect[3] / 2) # Right center
    else:
        # Dynamic nearest connection points
        p0, p3 = geometry.get_nearest_connection_points(s_rect, t_rect)

    # 2. Control Points
    p1 = relationship.source_handle
    p2 = relationship.target_handle

    # Safety fallback
    if not p1: p1 = p0
    if not p2: p2 = p3

    # 3. Generate Bezier path
    points = []
    num_segments = 20
    for i in range(num_segments + 1):
        t = i / num_segments
        pt = geometry.calculate_bezier_point(t, p0, p1, p2, p3)
        points.append(pt[0])
        points.append(pt[1])

    # 4. Draw curve
    dash = None
    if rel_type in (RelationshipType.DEPENDENCY, RelationshipType.REALIZATION):
        dash = (5, 5)

    # Using smooth=True for Tkinter to do its own smoothing on top of our points?
    # Or just lines. Our points are dense enough.
    # line join round makes it smoother.
    canvas.create_line(*points, dash=dash, fill="black", width=1, join="round")

    # 5. Draw Arrowhead at End (p3)
    # Angle is tangent at t=1.0
    angle = geometry.calculate_bezier_tangent_angle(1.0, p0, p1, p2, p3)
    
    x2, y2 = p3

    if rel_type in (RelationshipType.GENERALIZATION, RelationshipType.REALIZATION):
        draw_arrowhead_generalization(canvas, x2, y2, angle)
    elif rel_type == RelationshipType.AGGREGATION:
        draw_arrowhead_aggregation(canvas, x2, y2, angle)
    elif rel_type == RelationshipType.COMPOSITION:
        draw_arrowhead_composition(canvas, x2, y2, angle)
    elif rel_type == RelationshipType.DEPENDENCY:
        draw_arrowhead_dependency(canvas, x2, y2, angle)
