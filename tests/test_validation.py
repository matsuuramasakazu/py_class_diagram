import unittest
import json
import persistence
from model import UMLDiagram, UMLClass
from editor_canvas import MERMAID_NAME_REGEX

class TestValidation(unittest.TestCase):
    def test_persistence_layout_validation(self):
        mermaid_str = "classDiagram\n    class ClassA {\n    }"
        
        # Valid layout
        layout_json_valid = json.dumps({"ClassA": {"x": 10, "y": 20}})
        try:
            persistence.load_diagram(mermaid_str, layout_json_valid)
        except ValueError:
            self.fail("persistence.load_diagram raised ValueError unexpectedly!")

        # Invalid layout (list)
        layout_json_list = json.dumps([{"name": "ClassA", "x": 10}])
        with self.assertRaises(ValueError) as cm:
            persistence.load_diagram(mermaid_str, layout_json_list)
        self.assertEqual(str(cm.exception), "Layout JSON must be a dictionary mapping class names to position objects.")

        # Invalid layout (string)
        layout_json_str = json.dumps("just a string")
        with self.assertRaises(ValueError):
            persistence.load_diagram(mermaid_str, layout_json_str)

    def test_mermaid_name_regex(self):
        import re
        regex = MERMAID_NAME_REGEX
        self.assertTrue(re.match(regex, "MyClass"))
        self.assertTrue(re.match(regex, "_InternalClass"))
        self.assertTrue(re.match(regex, "Class123"))
        
        self.assertFalse(re.match(regex, "123Class"))
        self.assertFalse(re.match(regex, "My Class"))
        self.assertFalse(re.match(regex, "My-Class"))
        self.assertFalse(re.match(regex, ""))

if __name__ == "__main__":
    unittest.main()
