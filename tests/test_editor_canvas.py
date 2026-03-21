import unittest
from unittest.mock import MagicMock, call
import tkinter as tk
from model import UMLClass, UMLRelationship, UMLDiagram, RelationshipType
from editor_canvas import UMLCanvas, InteractionMode

class TestEditorCanvas(unittest.TestCase):
    def setUp(self):
        self.root = MagicMock()
        self.diag = UMLDiagram()
        self.c1 = UMLClass("A", x=0, y=0, width=100, height=100)
        self.c2 = UMLClass("B", x=200, y=0, width=100, height=100)
        self.diag.add_class(self.c1)
        self.diag.add_class(self.c2)
        
        # Mocking Tk and Canvas
        # Since UMLCanvas inherits from tk.Canvas, we may need to mock some of its methods
        # but here we can just test the logic by calling the handlers.
        # We'll use a real UMLCanvas but mock the actual tk calls if possible.
        # Alternatively, we just test the state changes.
        self.canvas = UMLCanvas(self.root, self.diag)
        # Mock canvas methods that redraw uses
        self.canvas.delete = MagicMock()
        self.canvas.create_rectangle = MagicMock()
        self.canvas.create_line = MagicMock()
        self.canvas.create_text = MagicMock()
        self.canvas.coords = MagicMock()

    def test_find_class_at(self):
        self.assertEqual(self.canvas.find_class_at(50, 50), self.c1)
        self.assertEqual(self.canvas.find_class_at(250, 50), self.c2)
        self.assertIsNone(self.canvas.find_class_at(150, 50))

    def test_selection_click(self):
        event = MagicMock()
        event.x = 50
        event.y = 50
        event.state = 0 # No shift
        
        self.canvas.on_button_press(event)
        self.assertEqual(self.canvas.selected_classes, [self.c1])
        
        event.x = 250
        self.canvas.on_button_press(event)
        self.assertEqual(self.canvas.selected_classes, [self.c2])
        
        # Shift click
        event.x = 50
        event.state = 0x0001 # Shift
        self.canvas.on_button_press(event)
        self.assertEqual(len(self.canvas.selected_classes), 2)
        self.assertIn(self.c1, self.canvas.selected_classes)
        self.assertIn(self.c2, self.canvas.selected_classes)

    def test_drag_class(self):
        # Select c1
        event = MagicMock()
        event.x = 50
        event.y = 50
        event.state = 0
        self.canvas.on_button_press(event)
        
        # Drag by 10, 20
        event.x = 60
        event.y = 70
        self.canvas.on_mouse_drag(event)
        
        self.assertEqual(self.c1.x, 10)
        self.assertEqual(self.c1.y, 20)

    def test_rubber_band_selection(self):
        # Click on background
        event = MagicMock()
        event.x = 150
        event.y = -50
        event.state = 0
        self.canvas.on_button_press(event)
        
        self.assertIsNotNone(self.canvas.rubber_band_id)
        
        # Mock coords for the rubber band
        self.canvas.coords.return_value = (150, -50, 250, 150)
        
        # Release at 250, 150 (covers c2 which is at 200,0 to 300,100, center at 250, 50)
        event.x = 250
        event.y = 150
        self.canvas.on_button_release(event)
        
        self.assertEqual(self.canvas.selected_classes, [self.c2])

    def test_create_relationship(self):
        self.canvas.set_mode(InteractionMode.CREATE_RELATIONSHIP)
        
        # Press on c1
        event = MagicMock()
        event.x = 50
        event.y = 50
        self.canvas.on_button_press(event)
        self.assertEqual(self.canvas.rel_source_class, self.c1)
        
        # Release on c2
        event.x = 250
        event.y = 50
        self.canvas.on_button_release(event)
        
        self.assertEqual(len(self.diag.relationships), 1)
        rel = self.diag.relationships[0]
        self.assertEqual(rel.source, self.c1)
        self.assertEqual(rel.target, self.c2)

if __name__ == '__main__':
    unittest.main()
