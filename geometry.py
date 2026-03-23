import math
from typing import Optional

Point = tuple[float, float]

def distance(p1: Point, p2: Point) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def add_points(p1: Point, p2: Point) -> Point:
    return (p1[0] + p2[0], p1[1] + p2[1])

def subtract_points(p1: Point, p2: Point) -> Point:
    return (p1[0] - p2[0], p1[1] - p2[1])

def multiply_point(p: Point, scalar: float) -> Point:
    return (p[0] * scalar, p[1] * scalar)

def calculate_bezier_point(t: float, p0: Point, p1: Point, p2: Point, p3: Point) -> Point:
    """
    Calculate point on Cubic Bezier curve at t (0.0 <= t <= 1.0).
    B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
    """
    mt = 1.0 - t
    mt2 = mt * mt
    mt3 = mt2 * mt
    t2 = t * t
    t3 = t2 * t

    x = mt3 * p0[0] + 3 * mt2 * t * p1[0] + 3 * mt * t2 * p2[0] + t3 * p3[0]
    y = mt3 * p0[1] + 3 * mt2 * t * p1[1] + 3 * mt * t2 * p2[1] + t3 * p3[1]
    return (x, y)

def calculate_bezier_tangent_angle(t: float, p0: Point, p1: Point, p2: Point, p3: Point) -> float:
    """
    Calculate the tangent angle (in radians) of the Cubic Bezier curve at t.
    Derivative B'(t) = 3(1-t)^2(P1-P0) + 6(1-t)t(P2-P1) + 3t^2(P3-P2)
    """
    mt = 1.0 - t
    mt2 = mt * mt
    t2 = t * t

    # Derivative components
    # dx/dt
    dx = (3 * mt2 * (p1[0] - p0[0]) +
          6 * mt * t * (p2[0] - p1[0]) +
          3 * t2 * (p3[0] - p2[0]))
    
    # dy/dt
    dy = (3 * mt2 * (p1[1] - p0[1]) +
          6 * mt * t * (p2[1] - p1[1]) +
          3 * t2 * (p3[1] - p2[1]))

    mag = math.hypot(dx, dy)
    if mag < 1e-9:
        # Fallback for degenerate cases (e.g., P2 == P3 at t=1.0)
        if t >= 0.5:
            # Use vector from P2 to P3
            dx = p3[0] - p2[0]
            dy = p3[1] - p2[1]
        else:
            # Use vector from P0 to P1
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
        
        mag = math.hypot(dx, dy)
        if mag < 1e-9:
            # Last resort fallback if control points also coincide
            return 0.0

    return math.atan2(dy, dx)

def line_intersection(p1: Point, p2: Point, p3: Point, p4: Point) -> Optional[Point]:
    """
    Find intersection of two line segments p1-p2 and p3-p4.
    Returns None if parallel or no intersection within segments.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if abs(denom) < 1e-9:
        return None  # Parallel or nearly parallel

    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

    if 0 <= ua <= 1 and 0 <= ub <= 1:
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        return (x, y)
    return None

def get_rect_segments(x: float, y: float, w: float, h: float) -> list[tuple[Point, Point]]:
    """Return the 4 segments of a rectangle: Top, Right, Bottom, Left."""
    tl = (x, y)
    tr = (x + w, y)
    br = (x + w, y + h)
    bl = (x, y + h)
    return [
        (tl, tr), # Top
        (tr, br), # Right
        (br, bl), # Bottom
        (bl, tl)  # Left
    ]

def find_bezier_rect_intersection(p0: Point, p1: Point, p2: Point, p3: Point, 
                                  rect_x: float, rect_y: float, rect_w: float, rect_h: float,
                                  num_samples: int = 20) -> Optional[Point]:
    """
    Find the intersection of a Bezier curve and a rectangle.
    Approximates the Bezier curve as line segments.
    """
    if num_samples < 1:
        num_samples = 1
        
    segments = get_rect_segments(rect_x, rect_y, rect_w, rect_h)
    
    # Sample points along the bezier curve
    curve_points = []
    for i in range(num_samples + 1):
        t = i / num_samples
        curve_points.append(calculate_bezier_point(t, p0, p1, p2, p3))
    
    # Check intersection for each segment of the curve against each side of the rect
    for i in range(len(curve_points) - 1):
        cp1 = curve_points[i]
        cp2 = curve_points[i+1]
        
        for rp1, rp2 in segments:
            intersection = line_intersection(cp1, cp2, rp1, rp2)
            if intersection:
                return intersection
                
    return None

def get_rect_center(x: float, y: float, w: float, h: float) -> Point:
    return (x + w / 2, y + h / 2)

def get_nearest_connection_points(rect1: tuple[float, float, float, float], 
                                  rect2: tuple[float, float, float, float]) -> tuple[Point, Point]:
    """
    Determine the best start and end points for a connection between two rectangles.
    It selects the midpoints of the sides that are closest to each other.
    rect format: (x, y, w, h)
    """
    r1_x, r1_y, r1_w, r1_h = rect1
    r2_x, r2_y, r2_w, r2_h = rect2

    # Midpoints of 4 sides for Rect 1
    r1_mids = [
        (r1_x + r1_w / 2, r1_y),          # Top
        (r1_x + r1_w, r1_y + r1_h / 2),   # Right
        (r1_x + r1_w / 2, r1_y + r1_h),   # Bottom
        (r1_x, r1_y + r1_h / 2)           # Left
    ]

    # Midpoints of 4 sides for Rect 2
    r2_mids = [
        (r2_x + r2_w / 2, r2_y),          # Top
        (r2_x + r2_w, r2_y + r2_h / 2),   # Right
        (r2_x + r2_w / 2, r2_y + r2_h),   # Bottom
        (r2_x, r2_y + r2_h / 2)           # Left
    ]

    min_dist = float('inf')
    best_p1 = r1_mids[0]
    best_p2 = r2_mids[0]

    for p1 in r1_mids:
        for p2 in r2_mids:
            d = distance(p1, p2)
            if d < min_dist:
                min_dist = d
                best_p1 = p1
                best_p2 = p2

    return best_p1, best_p2
