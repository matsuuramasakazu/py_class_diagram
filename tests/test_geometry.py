import unittest
import math
from geometry import (
    distance, calculate_bezier_point, calculate_bezier_tangent_angle,
    line_intersection, find_bezier_rect_intersection, get_nearest_connection_points
)

class TestGeometry(unittest.TestCase):
    def test_distance(self):
        self.assertAlmostEqual(distance((0, 0), (3, 4)), 5.0)

    def test_bezier_point_endpoints(self):
        p0, p1, p2, p3 = (0, 0), (10, 0), (10, 10), (20, 10)
        self.assertEqual(calculate_bezier_point(0.0, p0, p1, p2, p3), p0)
        self.assertEqual(calculate_bezier_point(1.0, p0, p1, p2, p3), p3)

    def test_bezier_midpoint(self):
        # Linear bezier (all points on a line)
        p0, p1, p2, p3 = (0, 0), (10, 0), (20, 0), (30, 0)
        mid = calculate_bezier_point(0.5, p0, p1, p2, p3)
        self.assertAlmostEqual(mid[0], 15.0)
        self.assertAlmostEqual(mid[1], 0.0)

    def test_tangent_angle(self):
        # Horizontal line at start
        p0, p1, p2, p3 = (0, 0), (10, 0), (10, 10), (20, 10)
        angle = calculate_bezier_tangent_angle(0.0, p0, p1, p2, p3)
        self.assertAlmostEqual(angle, 0.0)
        
        # Vertical tangent?
        # P2(10, 10) -> P3(10, 20)
        p0, p1, p2, p3 = (0, 0), (10, 0), (10, 10), (10, 20)
        angle_end = calculate_bezier_tangent_angle(1.0, p0, p1, p2, p3)
        self.assertAlmostEqual(angle_end, math.pi / 2)

    def test_line_intersection(self):
        # Crossing lines
        p1 = line_intersection((0, 5), (10, 5), (5, 0), (5, 10))
        self.assertEqual(p1, (5, 5))
        
        # Parallel lines
        p2 = line_intersection((0, 0), (10, 0), (0, 1), (10, 1))
        self.assertIsNone(p2)
        
        # Non-intersecting segments
        p3 = line_intersection((0, 0), (2, 0), (5, 0), (7, 0))
        self.assertIsNone(p3)

    def test_bezier_rect_intersection(self):
        rect = (10, 10, 20, 20) # 10,10 to 30,30
        
        # Curve passing through the box
        p0 = (0, 20)
        p1 = (5, 20)
        p2 = (35, 20)
        p3 = (40, 20)
        
        # Should intersect left wall at (10, 20)
        intersection = find_bezier_rect_intersection(p0, p1, p2, p3, *rect)
        self.assertIsNotNone(intersection)
        self.assertAlmostEqual(intersection[0], 10.0)
        self.assertAlmostEqual(intersection[1], 20.0)

    def test_bezier_rect_intersection_zero_samples(self):
        # Should not crash with num_samples=0
        rect = (10, 10, 20, 20)
        p0, p1, p2, p3 = (0, 20), (5, 20), (35, 20), (40, 20)
        # Should work safely even if we pass num_samples <= 0
        intersection = find_bezier_rect_intersection(p0, p1, p2, p3, *rect, num_samples=0)
        self.assertIsNotNone(intersection)

    def test_nearest_connection_points(self):
        # Box 1 at (0,0, 10,10) -> Center (5,5)
        # Box 2 at (20,0, 10,10) -> Center (25,5)
        # Should connect Right of 1 to Left of 2
        r1 = (0, 0, 10, 10)
        r2 = (20, 0, 10, 10)
        
        p1, p2 = get_nearest_connection_points(r1, r2)
        self.assertEqual(p1, (10, 5)) # Right mid of r1
        self.assertEqual(p2, (20, 5)) # Left mid of r2

if __name__ == '__main__':
    unittest.main()
