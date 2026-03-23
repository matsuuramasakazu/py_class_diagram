import math
from typing import Tuple, List, Dict, Optional
from model import UMLDiagram, UMLRelationship, UMLClass, RelationshipType
import geometry

def get_class_rect(uml_class: UMLClass) -> Tuple[float, float, float, float]:
    return (uml_class.x, uml_class.y, uml_class.width, uml_class.height)

def initialize_relationship_handles(rel: UMLRelationship) -> None:
    """
    Initialize handles for a relationship if they are not already set.
    """
    if rel.source_handle and rel.target_handle:
        return

    s_rect = get_class_rect(rel.source)
    t_rect = get_class_rect(rel.target)

    if rel.source == rel.target:
        # Self-reference
        # Start: Bottom center
        # End: Right center
        # Curve: Around bottom-right
        
        # Start point (Bottom center)
        p1 = (s_rect[0] + s_rect[2] / 2, s_rect[1] + s_rect[3])
        # End point (Right center)
        p2 = (s_rect[0] + s_rect[2], s_rect[1] + s_rect[3] / 2)
        
        # Control points to make a nice loop
        # P_handle1: Downwards from P1
        # P_handle2: Rightwards from P2
        
        loop_size = 30
        h1 = (p1[0], p1[1] + loop_size)
        h2 = (p2[0] + loop_size, p2[1])
        
        rel.source_handle = h1
        rel.target_handle = h2
        
    else:
        # Normal relationship
        p1, p2 = geometry.get_nearest_connection_points(s_rect, t_rect)
        
        # Vector from p1 to p2
        v = geometry.subtract_points(p2, p1)
        d = geometry.distance(p1, p2)
        
        if d > 0:
            # 10% from start and end (as per user requirement)
            factor = 0.1
            
            # h1 = p1 + v * 0.1
            h1 = geometry.add_points(p1, geometry.multiply_point(v, factor))
            # h2 = p2 - v * 0.1
            h2 = geometry.subtract_points(p2, geometry.multiply_point(v, factor))
            
            rel.source_handle = h1
            rel.target_handle = h2
        else:
            rel.source_handle = p1
            rel.target_handle = p2

def update_multiple_relationship_offsets(diagram: UMLDiagram) -> None:
    """
    Adjust handles for relationships that share the same source and target
    to prevent overlap.
    """
    # Group relationships by (source, target) pair (order-independent for grouping)
    groups: dict[tuple[str, str], list[UMLRelationship]] = {}
    
    for rel in diagram.relationships:
        # Use sorted names as key
        key = tuple(sorted((rel.source.name, rel.target.name)))
        if key not in groups:
            groups[key] = []
        groups[key].append(rel)
    
    # Create name to class map for efficient lookup
    class_map = {c.name: c for c in diagram.classes}
        
    for key, rels in groups.items():
        if len(rels) <= 1:
            continue
            
        # If any of them is self-ref, we handle differently?
        if key[0] == key[1]:
            # Self-reference overlap handling
            base_loop = 30
            step = 20
            for i, rel in enumerate(rels):
                # Recalculate based on index
                s_rect = get_class_rect(rel.source)
                p1 = (s_rect[0] + s_rect[2] / 2, s_rect[1] + s_rect[3])
                p2 = (s_rect[0] + s_rect[2], s_rect[1] + s_rect[3] / 2)
                
                offset = base_loop + i * step
                rel.source_handle = (p1[0], p1[1] + offset)
                rel.target_handle = (p2[0] + offset, p2[1])
            continue

        # Normal relationship overlap
        count = len(rels)
        step_size = 40 # pixels offset
        
        # Lookup classes safely
        c1 = class_map.get(key[0])
        c2 = class_map.get(key[1])
        
        if not c1 or not c2:
            continue
        
        for i, rel in enumerate(rels):
            # Direction check: Is it A->B or B->A?
            p1_c, p2_c = geometry.get_nearest_connection_points(get_class_rect(c1), get_class_rect(c2))
            
            # Vector V
            vx = p2_c[0] - p1_c[0]
            vy = p2_c[1] - p1_c[1]
            dist = math.sqrt(vx*vx + vy*vy)
            if dist == 0:
                continue
            
            # Perpendicular vector (-y, x) normalized
            px = -vy / dist
            py = vx / dist
            
            # Calculate offset magnitude
            offset_idx = i - (count - 1) / 2
            offset_dist = offset_idx * step_size
            
            # New control points relative to straight line
            if rel.source == c1:
                base_start, base_end = p1_c, p2_c
                
                h1_x = base_start[0] + vx * 0.1 + px * offset_dist
                h1_y = base_start[1] + vy * 0.1 + py * offset_dist
                
                h2_x = base_start[0] + vx * 0.9 + px * offset_dist
                h2_y = base_start[1] + vy * 0.9 + py * offset_dist
                
            else: # rel.source == c2 (Reversed)
                base_start, base_end = p2_c, p1_c
                
                h1_x = p1_c[0] + vx * 0.9 + px * offset_dist
                h1_y = p1_c[1] + vy * 0.9 + py * offset_dist
                
                h2_x = p1_c[0] + vx * 0.1 + px * offset_dist
                h2_y = p1_c[1] + vy * 0.1 + py * offset_dist
                
            rel.source_handle = (h1_x, h1_y)
            rel.target_handle = (h2_x, h2_y)

def rewire_relationship(diagram: UMLDiagram, rel: UMLRelationship, new_source: Optional[UMLClass] = None, new_target: Optional[UMLClass] = None) -> bool:
    """
    Safely rewires a relationship to a new source or target class.
    Validates self-reference constraints and updates layout.
    
    Returns:
        bool: True if rewiring was successful, False otherwise.
    """
    proposed_source = new_source if new_source else rel.source
    proposed_target = new_target if new_target else rel.target
    
    is_self = (proposed_source == proposed_target)
    allowed_self = rel.type in (
        RelationshipType.ASSOCIATION, 
        RelationshipType.AGGREGATION, 
        RelationshipType.COMPOSITION
    )
    
    if is_self and not allowed_self:
        return False
        
    rel.source = proposed_source
    rel.target = proposed_target
    
    # Reset handles to default because geometry changed
    rel.source_handle = None
    rel.target_handle = None
    initialize_relationship_handles(rel)
    
    update_multiple_relationship_offsets(diagram)
    return True
