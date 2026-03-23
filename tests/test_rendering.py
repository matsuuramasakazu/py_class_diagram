import unittest
from unittest.mock import MagicMock, call
import math
from model import UMLClass, UMLRelationship, RelationshipType
from rendering import draw_class_box, draw_relationship_line

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
        self.canvas.create_line.assert_any_call(10, 35, 110, 35, fill="black")
        self.canvas.create_line.assert_any_call(10, 61, 110, 61, fill="black")
        
        # Check if text is drawn
        self.canvas.create_text.assert_any_call(60.0, 22.5, text="User", font=("Arial", 10, "bold"))
        self.canvas.create_text.assert_any_call(15, 40, text="+ id: int", anchor="nw", font=("Arial", 9))
        self.canvas.create_text.assert_any_call(15, 66, text="+ save()", anchor="nw", font=("Arial", 9))

    def test_draw_relationship_line_generalization(self):
        src = UMLClass("Child", x=0, y=0, width=50, height=50)
        tgt = UMLClass("Parent", x=100, y=0, width=50, height=50)
        rel = UMLRelationship(RelationshipType.GENERALIZATION, src, tgt)
        
        draw_relationship_line(self.canvas, rel)
        
        # Should call create_line for the bezier curve
        # We can't predict exact coordinates easily, but we know it's one call with many args
        # And it should start at (50, 25) [Right of Src] and end at (100, 25) [Left of Tgt]
        
        bezier_call = None
        for call_args in self.canvas.create_line.call_args_list:
            args = call_args[0]
            kwargs = call_args[1]
            if kwargs.get("joinstyle") == "round":
                bezier_call = call_args
                break
        
        self.assertIsNotNone(bezier_call)
        args = bezier_call[0]
        # Start point (x, y)
        self.assertAlmostEqual(args[0], 50.0)
        self.assertAlmostEqual(args[1], 25.0)
        # End point (x, y) -> Last two args
        self.assertAlmostEqual(args[-2], 100.0)
        self.assertAlmostEqual(args[-1], 25.0)
        
        # Generalization arrowhead (white triangle) at (100, 25)
        self.canvas.create_polygon.assert_called()
        args, kwargs = self.canvas.create_polygon.call_args
        self.assertEqual(kwargs['fill'], "white")
        self.assertEqual(kwargs['outline'], "black")
        # Point 1 should be (100, 25)
        self.assertAlmostEqual(args[0], 100.0)
        self.assertAlmostEqual(args[1], 25.0)

    def test_draw_relationship_line_dependency(self):
        src = UMLClass("A", x=0, y=0, width=50, height=50)
        tgt = UMLClass("B", x=100, y=0, width=50, height=50)
        rel = UMLRelationship(RelationshipType.DEPENDENCY, src, tgt)
        
        draw_relationship_line(self.canvas, rel)
        
        # Find dashed line
        bezier_call = None
        for call_args in self.canvas.create_line.call_args_list:
            args = call_args[0]
            kwargs = call_args[1]
            if kwargs.get("dash") == (5, 5) and kwargs.get("joinstyle") == "round":
                bezier_call = call_args
                break
        self.assertIsNotNone(bezier_call)
        
        # Dependency arrowhead (open arrow)
        # We check if there's a line starting at 100, 25 (End point)
        found_arrow_line = False
        for call_args in self.canvas.create_line.call_args_list:
            args = call_args[0]
            # Arrow lines are usually 4 args: x1, y1, x2, y2
            if len(args) == 4 and abs(args[0] - 100.0) < 0.1 and abs(args[1] - 25.0) < 0.1:
                found_arrow_line = True
                break
        self.assertTrue(found_arrow_line)

if __name__ == '__main__':
    unittest.main()
