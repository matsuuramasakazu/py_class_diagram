import unittest
from unittest.mock import MagicMock, patch
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
        # Mock tkinter.font.Font
        self.font_patcher = patch('tkinter.font.Font')
        self.mock_font = self.font_patcher.start()
        # Mock measure to return some width
        self.mock_font.return_value.measure.return_value = 50
        self.mock_font.return_value.metrics.return_value = 15
        
        self.canvas = UMLCanvas(self.root, self.diag)
        # Mock canvas methods that redraw uses
        self.canvas.delete = MagicMock()
        self.canvas.create_rectangle = MagicMock()
        self.canvas.create_line = MagicMock()
        self.canvas.create_text = MagicMock()
        self.canvas.coords = MagicMock()

    def tearDown(self):
        self.font_patcher.stop()

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

    @patch('editor_canvas.tk.Entry')
    @patch('editor_canvas.tk.Text')
    def test_inline_editing(self, mock_text, mock_entry):
        mock_entry_instance = MagicMock()
        mock_entry.return_value = mock_entry_instance
        mock_text_instance = MagicMock()
        mock_text.return_value = mock_text_instance

        # Select c1 for editing Name
        event = MagicMock()
        event.x = 50
        event.y = 10 # click header
        
        self.canvas.on_double_click(event)
        
        # Verify editor_widget exists and insert was called with "A"
        self.assertIsNotNone(self.canvas.editor_widget)
        mock_entry_instance.insert.assert_called_with(0, "A")
        
        # Change text and commit
        mock_entry_instance.get.return_value = "NewClassName"
        self.canvas.commit_edit()
        
        self.assertEqual(self.c1.name, "NewClassName")
        self.assertIsNone(self.canvas.editor_widget)
        
        # Test cancel edit for attributes
        event.x = 50
        event.y = 40 # click attributes
        self.canvas.on_double_click(event)
        
        self.assertIsNotNone(self.canvas.editor_widget)
        self.canvas.cancel_edit()
        self.assertIsNone(self.canvas.editor_widget)

if __name__ == '__main__':
    unittest.main()
