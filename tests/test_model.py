import unittest
from model import UMLClass, UMLRelationship, UMLDiagram, RelationshipType

class TestUMLModel(unittest.TestCase):
    def test_uml_class_creation(self):
        cls = UMLClass("User", x=10, y=20, width=100, height=80)
        self.assertEqual(cls.name, "User")
        self.assertEqual(cls.x, 10)
        self.assertEqual(cls.y, 20)
        self.assertEqual(cls.width, 100)
        self.assertEqual(cls.height, 80)
        self.assertEqual(len(cls.attributes), 0)
        self.assertEqual(len(cls.operations), 0)

    def test_uml_class_attributes(self):
        cls = UMLClass("User")
        cls.add_attribute("id: int")
        cls.add_attribute("name: str")
        self.assertIn("id: int", cls.attributes)
        self.assertIn("name: str", cls.attributes)
        
        # Test duplicate addition
        cls.add_attribute("id: int")
        self.assertEqual(len(cls.attributes), 2)
        
        cls.remove_attribute("id: int")
        self.assertNotIn("id: int", cls.attributes)
        self.assertEqual(len(cls.attributes), 1)

    def test_uml_class_operations(self):
        cls = UMLClass("User")
        cls.add_operation("save()")
        cls.add_operation("delete()")
        self.assertIn("save()", cls.operations)
        self.assertIn("delete()", cls.operations)
        
        # Test duplicate addition
        cls.add_operation("save()")
        self.assertEqual(len(cls.operations), 2)
        
        cls.remove_operation("save()")
        self.assertNotIn("save()", cls.operations)
        self.assertEqual(len(cls.operations), 1)

    def test_uml_relationship(self):
        cls1 = UMLClass("User")
        cls2 = UMLClass("Profile")
        rel = UMLRelationship(RelationshipType.ASSOCIATION, cls1, cls2)
        self.assertEqual(rel.type, RelationshipType.ASSOCIATION)
        self.assertEqual(rel.source, cls1)
        self.assertEqual(rel.target, cls2)

    def test_uml_diagram(self):
        diagram = UMLDiagram()
        cls1 = UMLClass("User")
        cls2 = UMLClass("Profile")
        
        diagram.add_class(cls1)
        diagram.add_class(cls2)
        self.assertEqual(len(diagram.classes), 2)
        
        rel = UMLRelationship(RelationshipType.ASSOCIATION, cls1, cls2)
        diagram.add_relationship(rel)
        self.assertEqual(len(diagram.relationships), 1)
        
        # Test removal of class and its relationships
        diagram.remove_class(cls1)
        self.assertEqual(len(diagram.classes), 1)
        self.assertEqual(len(diagram.relationships), 0)

    def test_remove_relationship(self):
        diagram = UMLDiagram()
        cls1 = UMLClass("User")
        cls2 = UMLClass("Profile")
        rel = UMLRelationship(RelationshipType.ASSOCIATION, cls1, cls2)
        
        diagram.add_class(cls1)
        diagram.add_class(cls2)
        diagram.add_relationship(rel)
        
        diagram.remove_relationship(rel)
        self.assertEqual(len(diagram.relationships), 0)
        self.assertEqual(len(diagram.classes), 2)

if __name__ == '__main__':
    unittest.main()
