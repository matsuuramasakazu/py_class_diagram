import unittest
from unittest.mock import MagicMock, call
import math
from model import UMLClass, UMLRelationship, RelationshipType
from rendering import draw_class_box, draw_relationship_line, calculate_intersection

class TestRendering(unittest.TestCase):
    def setUp(self):
        self.canvas = MagicMock()

    def test_draw_class_box(self):
        cls = UMLClass("User", x=10, y=10, width=100, height=80)
        cls.add_attribute("+ id: int")
        cls.add_operation("+ save()")
        
        draw_class_box(self.canvas, cls)
        
        # Check if rectangle is drawn
        self.canvas.create_rectangle.assert_called_with(10, 10, 110, 90, fill="white", outline="black")
        
        # Check if horizontal dividers are drawn
        # Header line at y + 25 = 35
        # Attribute separator at y + 25 + attr_h = 10 + 25 + 26 = 61
        self.canvas.create_line.assert_any_call(10, 35, 110, 35, fill="black")
        self.canvas.create_line.assert_any_call(10, 61, 110, 61, fill="black")
        
        # Check if text is drawn
        self.canvas.create_text.assert_any_call(60.0, 22.5, text="User", font=("Arial", 10, "bold"))
        self.canvas.create_text.assert_any_call(15, 40, text="+ id: int", anchor="nw", font=("Arial", 9))
        self.canvas.create_text.assert_any_call(15, 66, text="+ save()", anchor="nw", font=("Arial", 9))

    def test_calculate_intersection(self):
        # Line from (0,0) to (100,100), box at (50,50) to (150,150)
        # Center of box is (100,100). Intersection should be at (50,50)
        res = calculate_intersection(0, 0, 100, 100, 50, 50, 150, 150)
        self.assertEqual(res, (50, 50))
        
        # Line from (200,100) to (100,100), box at (50,50) to (150,150)
        # Intersection at (150, 100)
        res = calculate_intersection(200, 100, 100, 100, 50, 50, 150, 150)
        self.assertEqual(res, (150, 100))

    def test_draw_relationship_line_generalization(self):
        src = UMLClass("Child", x=0, y=0, width=50, height=50)
        tgt = UMLClass("Parent", x=100, y=0, width=50, height=50)
        rel = UMLRelationship(RelationshipType.GENERALIZATION, src, tgt)
        
        draw_relationship_line(self.canvas, rel)
        
        # Source center (25, 25), Target center (125, 25)
        # Line from (50, 25) to (100, 25)
        self.canvas.create_line.assert_called_with(50.0, 25.0, 100.0, 25.0, dash=None, fill="black")
        
        # Generalization arrowhead (white triangle) at (100, 25)
        self.canvas.create_polygon.assert_called()
        args, kwargs = self.canvas.create_polygon.call_args
        self.assertEqual(kwargs['fill'], "white")
        self.assertEqual(kwargs['outline'], "black")
        # Point 1 should be (100, 25)
        self.assertEqual(args[0], 100.0)
        self.assertEqual(args[1], 25.0)

    def test_draw_relationship_line_dependency(self):
        src = UMLClass("A", x=0, y=0, width=50, height=50)
        tgt = UMLClass("B", x=100, y=0, width=50, height=50)
        rel = UMLRelationship(RelationshipType.DEPENDENCY, src, tgt)
        
        draw_relationship_line(self.canvas, rel)
        
        # Dashed line
        self.canvas.create_line.assert_any_call(50.0, 25.0, 100.0, 25.0, dash=(5, 5), fill="black")
        
        # Dependency arrowhead (open arrow)
        # In my implementation, open arrow is 2 lines
        # One line from (100, 25) to p2, another from (100, 25) to p3
        # We check if there's a line starting at 100, 25
        found = False
        for call_args in self.canvas.create_line.call_args_list:
            args = call_args[0]
            if args[0] == 100.0 and args[1] == 25.0 and len(args) == 4:
                found = True
        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
