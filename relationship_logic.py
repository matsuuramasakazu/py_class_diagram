from typing import List, Dict, Tuple
import math
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
            # 10% from start and end
            factor = 0.3 # increased to 30% for better bezier curve visibility by default
            # Actually user requirement says 10%.
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
    groups: Dict[Tuple[str, str], List[UMLRelationship]] = {}
    
    for rel in diagram.relationships:
        # Sort names to treat A->B and B->A as same group?
        # User requirement: "Class and Class between multiple relationship lines exist"
        # Usually overlap happens if they are perfectly on top of each other.
        # A->B and B->A are on same path if drawn straight.
        
        # Use sorted names as key
        key = tuple(sorted((rel.source.name, rel.target.name)))
        if key not in groups:
            groups[key] = []
        groups[key].append(rel)
        
    for key, rels in groups.items():
        if len(rels) <= 1:
            continue
            
        # If any of them is self-ref, we handle differently?
        # Self-refs usually don't overlap as much unless distinct types.
        if key[0] == key[1]:
            # Self-reference overlap handling
            # Just increment the loop size?
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
        # Calculate midpoint of the straight line connecting centers
        # We need to offset the control points perpendicular to the main vector.
        
        # However, handles are stored as absolute coordinates.
        # Simplest approach: Reset handles to default line, then add perpendicular offset.
        # BUT, if user manually moved them, we shouldn't overwrite?
        # User requirement: "Adjust center control point offset... so lines don't overlap".
        # If we imply automatic layout, we might overwrite user changes.
        # But this function is likely called on creation or "auto layout".
        # Let's assume we only touch them if they look "default" (straight).
        # Or simpler: always recalculate for now as per "Advanced relationship lines" might imply auto-routing.
        
        # Let's apply offsets centered around 0.
        # e.g. 2 lines: +10, -10
        # 3 lines: +15, 0, -15
        
        count = len(rels)
        # 0, 1, -1, 2, -2 ...
        # Or just space them out: index - (count-1)/2
        
        step_size = 40 # pixels offset
        
        for i, rel in enumerate(rels):
            # Direction check: Is it A->B or B->A?
            # We want the offset to be consistent relative to the "sorted" pair.
            # So if A->B, and we offset 'right', then B->A offset 'right' (relative to B->A) would be opposite.
            
            # Let's define the canonical vector from key[0] to key[1].
            c1 = next(c for c in diagram.classes if c.name == key[0])
            c2 = next(c for c in diagram.classes if c.name == key[1])
            
            p1_c, p2_c = geometry.get_nearest_connection_points(get_class_rect(c1), get_class_rect(c2))
            
            # Vector V
            vx = p2_c[0] - p1_c[0]
            vy = p2_c[1] - p1_c[1]
            dist = math.sqrt(vx*vx + vy*vy)
            if dist == 0: continue
            
            # Perpendicular vector (-y, x) normalized
            px = -vy / dist
            py = vx / dist
            
            # Calculate offset magnitude
            # center index = (count - 1) / 2
            # i = 0, count=2 -> -0.5 * step
            # i = 1, count=2 -> 0.5 * step
            offset_idx = i - (count - 1) / 2
            offset_dist = offset_idx * step_size
            
            # New control points relative to straight line
            # Base start/end
            if rel.source == c1:
                base_start, base_end = p1_c, p2_c
                # Control points at 10% and 90%
                # H1 = Start + V*0.1 + P*offset
                # H2 = Start + V*0.9 + P*offset
                
                h1_x = base_start[0] + vx * 0.1 + px * offset_dist
                h1_y = base_start[1] + vy * 0.1 + py * offset_dist
                
                h2_x = base_start[0] + vx * 0.9 + px * offset_dist
                h2_y = base_start[1] + vy * 0.9 + py * offset_dist
                
            else: # rel.source == c2 (Reversed)
                # We want the same visual curve.
                # The "canonical" curve is defined relative to c1->c2.
                # So the offset pushes "up/right" relative to c1->c2.
                
                # Rel is c2->c1.
                # Start is c2, End is c1.
                # Canonical V is c1->c2.
                # Rel V is c2->c1 = -V.
                
                base_start, base_end = p2_c, p1_c # Start at c2, End at c1
                
                # We want the curve to follow the same "lane" as if it were c1->c2 with that offset.
                # Lane is defined by P * offset_dist.
                
                # c1->c2 path: P(t) ... + P * offset
                # We are drawing c2->c1.
                
                # H1 (near source c2) corresponds to 90% of c1->c2
                # H1 = c1 + V*0.9 + P*offset
                h1_x = p1_c[0] + vx * 0.9 + px * offset_dist
                h1_y = p1_c[1] + vy * 0.9 + py * offset_dist
                
                # H2 (near target c1) corresponds to 10% of c1->c2
                # H2 = c1 + V*0.1 + P*offset
                h2_x = p1_c[0] + vx * 0.1 + px * offset_dist
                h2_y = p1_c[1] + vy * 0.1 + py * offset_dist
                
            rel.source_handle = (h1_x, h1_y)
            rel.target_handle = (h2_x, h2_y)

