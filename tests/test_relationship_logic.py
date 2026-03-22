import unittest
from model import UMLDiagram, UMLClass, UMLRelationship, RelationshipType
import relationship_logic
import geometry

class TestRelationshipLogic(unittest.TestCase):
    def setUp(self):
        self.diagram = UMLDiagram()
        self.c1 = UMLClass(name="A", x=0, y=0, width=100, height=100)
        self.c2 = UMLClass(name="B", x=200, y=0, width=100, height=100)
        self.diagram.add_class(self.c1)
        self.diagram.add_class(self.c2)

    def test_initialize_simple_relationship(self):
        rel = UMLRelationship(RelationshipType.ASSOCIATION, self.c1, self.c2)
        relationship_logic.initialize_relationship_handles(rel)
        
        self.assertIsNotNone(rel.source_handle)
        self.assertIsNotNone(rel.target_handle)
        
        # Expected straight line connection from Right of A to Left of B
        # A center: 50, 50. Right edge mid: 100, 50.
        # B center: 250, 50. Left edge mid: 200, 50.
        # Dist = 100.
        # Handle1 = 100,50 + (100,0)*0.1 = 110, 50
        # Handle2 = 200,50 - (100,0)*0.1 = 190, 50
        
        self.assertAlmostEqual(rel.source_handle[0], 110.0)
        self.assertAlmostEqual(rel.target_handle[0], 190.0)

    def test_initialize_self_reference(self):
        rel = UMLRelationship(RelationshipType.ASSOCIATION, self.c1, self.c1)
        relationship_logic.initialize_relationship_handles(rel)
        
        # Should start at bottom center (50, 100)
        # End at right center (100, 50)
        # Handles should push out
        
        # Check if handles are set
        self.assertIsNotNone(rel.source_handle)
        self.assertIsNotNone(rel.target_handle)
        
        # Handle1 y > 100 (below bottom)
        self.assertGreater(rel.source_handle[1], 100)
        # Handle2 x > 100 (right of right)
        self.assertGreater(rel.target_handle[0], 100)

    def test_multiple_relationship_offsets(self):
        # Add 3 relationships between A and B
        r1 = UMLRelationship(RelationshipType.ASSOCIATION, self.c1, self.c2)
        r2 = UMLRelationship(RelationshipType.ASSOCIATION, self.c1, self.c2)
        r3 = UMLRelationship(RelationshipType.ASSOCIATION, self.c2, self.c1) # Reversed direction
        
        self.diagram.add_relationship(r1)
        self.diagram.add_relationship(r2)
        self.diagram.add_relationship(r3)
        
        # Initialize default first (straight)
        for r in [r1, r2, r3]:
            relationship_logic.initialize_relationship_handles(r)
            
        # Apply offsets
        relationship_logic.update_multiple_relationship_offsets(self.diagram)
        
        # Check y-coordinates of handles. They should be different.
        # Center line is y=50.
        
        # Since we have 3, one should be roughly 50 (middle), one < 50, one > 50.
        ys = sorted([r1.source_handle[1], r2.source_handle[1], r3.target_handle[1]])
        
        # Note: r3 is reversed, so its target handle is near A (source of r1/r2).
        # We compare handles near A.
        
        self.assertNotAlmostEqual(ys[0], ys[1])
        self.assertNotAlmostEqual(ys[1], ys[2])
        
        # Check symmetry roughly
        # One should be ~50 (offset 0 if count is odd? Wait logic: i - (count-1)/2)
        # 0 - 1 = -1
        # 1 - 1 = 0
        # 2 - 1 = 1
        # So yes, middle one is 0 offset.
        
        # Find the middle one
        middle_y = [y for y in ys if abs(y - 50.0) < 1.0]
        self.assertEqual(len(middle_y), 1)

if __name__ == "__main__":
    unittest.main()
