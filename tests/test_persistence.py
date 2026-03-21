import unittest
import json
from model import UMLDiagram, UMLClass, UMLRelationship, RelationshipType
from persistence import to_mermaid, to_layout_json, load_diagram

class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.diagram = UMLDiagram()
        
        self.class_a = UMLClass(name="ClassA", x=10, y=20, width=100, height=80)
        self.class_a.add_attribute("+attr1")
        self.class_a.add_operation("-op1()")
        
        self.class_b = UMLClass(name="ClassB", x=200, y=150, width=120, height=90)
        self.class_b.add_attribute("#attr2")
        
        self.diagram.add_class(self.class_a)
        self.diagram.add_class(self.class_b)
        
        self.rel = UMLRelationship(
            type=RelationshipType.GENERALIZATION,
            source=self.class_a,
            target=self.class_b
        )
        self.diagram.add_relationship(self.rel)

    def test_to_mermaid(self):
        mermaid = to_mermaid(self.diagram)
        self.assertIn("classDiagram", mermaid)
        self.assertIn("class ClassA {", mermaid)
        self.assertIn("+attr1", mermaid)
        self.assertIn("-op1()", mermaid)
        self.assertIn("ClassA --|> ClassB", mermaid)

    def test_to_layout_json(self):
        layout_json = to_layout_json(self.diagram)
        data = json.loads(layout_json)
        self.assertIn("ClassA", data)
        self.assertEqual(data["ClassA"]["x"], 10)
        self.assertEqual(data["ClassA"]["y"], 20)
        self.assertEqual(data["ClassA"]["w"], 100)
        self.assertEqual(data["ClassA"]["h"], 80)
        self.assertIn("ClassB", data)

    def test_load_diagram_with_layout(self):
        mermaid = to_mermaid(self.diagram)
        layout_json = to_layout_json(self.diagram)
        
        loaded_diagram = load_diagram(mermaid, layout_json)
        
        self.assertEqual(len(loaded_diagram.classes), 2)
        self.assertEqual(len(loaded_diagram.relationships), 1)
        
        loaded_a = next(c for c in loaded_diagram.classes if c.name == "ClassA")
        self.assertEqual(loaded_a.x, 10)
        self.assertEqual(loaded_a.y, 20)
        self.assertEqual(loaded_a.width, 100)
        self.assertEqual(loaded_a.height, 80)
        self.assertIn("+attr1", loaded_a.attributes)
        self.assertIn("-op1()", loaded_a.operations)
        
        rel = loaded_diagram.relationships[0]
        self.assertEqual(rel.type, RelationshipType.GENERALIZATION)
        self.assertEqual(rel.source.name, "ClassA")
        self.assertEqual(rel.target.name, "ClassB")

    def test_load_diagram_without_layout(self):
        mermaid = to_mermaid(self.diagram)
        loaded_diagram = load_diagram(mermaid)
        
        self.assertEqual(len(loaded_diagram.classes), 2)
        loaded_a = next(c for c in loaded_diagram.classes if c.name == "ClassA")
        # Default layout values
        self.assertEqual(loaded_a.x, 0.0)
        self.assertEqual(loaded_a.y, 0.0)

    def test_all_relationship_types(self):
        diag = UMLDiagram()
        c1 = UMLClass(name="C1")
        c2 = UMLClass(name="C2")
        diag.add_class(c1)
        diag.add_class(c2)
        
        types = [
            RelationshipType.GENERALIZATION,
            RelationshipType.REALIZATION,
            RelationshipType.COMPOSITION,
            RelationshipType.AGGREGATION,
            RelationshipType.DEPENDENCY,
            RelationshipType.ASSOCIATION,
        ]
        
        for t in types:
            rel = UMLRelationship(type=t, source=c1, target=c2)
            diag.relationships = [rel]
            mermaid = to_mermaid(diag)
            loaded = load_diagram(mermaid)
            self.assertEqual(loaded.relationships[0].type, t)

if __name__ == "__main__":
    unittest.main()
