import unittest
import json
import os
import re
import tempfile
from model import UMLDiagram, UMLClass, UMLRelationship, RelationshipType
from persistence import (
    to_mermaid, to_layout_json, load_diagram,
    serialize, deserialize, save_to_file, load_from_file,
)


class TestToMermaid(unittest.TestCase):
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


class TestLegacyLoadDiagram(unittest.TestCase):
    """Tests for the legacy load_diagram() function used internally."""

    def setUp(self):
        self.diagram = UMLDiagram()
        self.class_a = UMLClass(name="ClassA", x=10, y=20, width=100, height=80)
        self.class_a.add_attribute("+attr1")
        self.class_a.add_operation("-op1()")
        self.class_b = UMLClass(name="ClassB", x=200, y=150, width=120, height=90)
        self.class_b.add_attribute("#attr2")
        self.diagram.add_class(self.class_a)
        self.diagram.add_class(self.class_b)
        self.diagram.add_relationship(UMLRelationship(
            type=RelationshipType.GENERALIZATION,
            source=self.class_a,
            target=self.class_b,
        ))

    def test_load_diagram_with_layout(self):
        mermaid = to_mermaid(self.diagram)
        layout_json = to_layout_json(self.diagram)
        loaded = load_diagram(mermaid, layout_json)
        self.assertEqual(len(loaded.classes), 2)
        self.assertEqual(len(loaded.relationships), 1)
        loaded_a = next(c for c in loaded.classes if c.name == "ClassA")
        self.assertEqual(loaded_a.x, 10)
        self.assertEqual(loaded_a.y, 20)
        self.assertEqual(loaded_a.width, 100)
        self.assertEqual(loaded_a.height, 80)
        self.assertIn("+attr1", loaded_a.attributes)
        self.assertIn("-op1()", loaded_a.operations)
        rel = loaded.relationships[0]
        self.assertEqual(rel.type, RelationshipType.GENERALIZATION)
        self.assertEqual(rel.source.name, "ClassA")
        self.assertEqual(rel.target.name, "ClassB")

    def test_load_diagram_without_layout(self):
        mermaid = to_mermaid(self.diagram)
        loaded = load_diagram(mermaid)
        self.assertEqual(len(loaded.classes), 2)
        loaded_a = next(c for c in loaded.classes if c.name == "ClassA")
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
            diag.relationships.clear()
            diag.add_relationship(rel)
            mermaid = to_mermaid(diag)
            loaded = load_diagram(mermaid)
            self.assertEqual(loaded.relationships[0].type, t)


class TestSerialize(unittest.TestCase):
    """Tests for the serialize() function."""

    def setUp(self):
        self.diagram = UMLDiagram()
        self.class_a = UMLClass(name="ClassA", x=10.0, y=20.0, width=100.0, height=80.0)
        self.class_a.add_attribute("+name: str")
        self.class_a.add_operation("+get_name()")
        self.class_b = UMLClass(name="ClassB", x=200.0, y=150.0, width=120.0, height=90.0)
        self.diagram.add_class(self.class_a)
        self.diagram.add_class(self.class_b)
        self.diagram.add_relationship(UMLRelationship(
            type=RelationshipType.COMPOSITION,
            source=self.class_a,
            target=self.class_b,
        ))

    def test_serialize_contains_header(self):
        content = serialize(self.diagram, title="My Diagram")
        self.assertTrue(content.startswith("# My Diagram"))

    def test_serialize_contains_mermaid_section(self):
        content = serialize(self.diagram)
        self.assertIn("```mermaid", content)
        self.assertIn("classDiagram", content)
        self.assertIn("class ClassA {", content)
        self.assertIn("+name: str", content)
        self.assertIn("ClassA --* ClassB", content)

    def test_serialize_contains_json_comment_section(self):
        content = serialize(self.diagram)
        self.assertIn("<!--", content)
        self.assertIn("-->", content)
        self.assertIn('"tool": "py_class_diagram"', content)
        self.assertIn('"layout"', content)
        self.assertIn('"ClassA"', content)

    def test_serialize_json_has_correct_coordinates(self):
        content = serialize(self.diagram)
        json_match = re.search(r"<!--\s*(\{.*?\})\s*-->", content, re.DOTALL)
        self.assertIsNotNone(json_match)
        data = json.loads(json_match.group(1))
        layout = data["layout"]
        self.assertEqual(layout["ClassA"]["x"], 10.0)
        self.assertEqual(layout["ClassA"]["y"], 20.0)
        self.assertEqual(layout["ClassA"]["w"], 100.0)
        self.assertEqual(layout["ClassA"]["h"], 80.0)


class TestDeserialize(unittest.TestCase):
    """Tests for the deserialize() function."""

    def setUp(self):
        self.diagram = UMLDiagram()
        self.class_a = UMLClass(name="ClassA", x=10.0, y=20.0, width=100.0, height=80.0)
        self.class_a.add_attribute("+attr1")
        self.class_a.add_operation("-op1()")
        self.class_b = UMLClass(name="ClassB", x=200.0, y=150.0, width=120.0, height=90.0)
        self.diagram.add_class(self.class_a)
        self.diagram.add_class(self.class_b)
        self.diagram.add_relationship(UMLRelationship(
            type=RelationshipType.GENERALIZATION,
            source=self.class_a,
            target=self.class_b,
        ))

    def test_roundtrip_serialize_deserialize(self):
        content = serialize(self.diagram)
        loaded = deserialize(content)
        self.assertEqual(len(loaded.classes), 2)
        self.assertEqual(len(loaded.relationships), 1)
        loaded_a = next(c for c in loaded.classes if c.name == "ClassA")
        self.assertEqual(loaded_a.x, 10.0)
        self.assertEqual(loaded_a.y, 20.0)
        self.assertEqual(loaded_a.width, 100.0)
        self.assertEqual(loaded_a.height, 80.0)
        self.assertIn("+attr1", loaded_a.attributes)
        self.assertIn("-op1()", loaded_a.operations)
        rel = loaded.relationships[0]
        self.assertEqual(rel.type, RelationshipType.GENERALIZATION)
        self.assertEqual(rel.source.name, "ClassA")
        self.assertEqual(rel.target.name, "ClassB")

    def test_deserialize_without_json_section_uses_defaults(self):
        # Mermaidセクションのみで、JSONセクションなし
        content = "# Title\n\n```mermaid\nclassDiagram\n    class ClassA {\n        +attr\n    }\n```\n"
        loaded = deserialize(content)
        self.assertEqual(len(loaded.classes), 1)
        loaded_a = loaded.classes[0]
        self.assertEqual(loaded_a.x, 0.0)
        self.assertEqual(loaded_a.y, 0.0)

    def test_deserialize_raises_on_missing_mermaid(self):
        content = "# Title\n\nNo mermaid section here.\n"
        with self.assertRaises(ValueError):
            deserialize(content)

    def test_deserialize_fallback_for_class_not_in_layout(self):
        """JSONに存在しないクラスはデフォルト座標（0,0）にフォールバックすること"""
        content = serialize(self.diagram)
        # JSONのClassBの座標データを削除したコンテンツを作成
        def remove_classb_from_json(m):
            data = json.loads(m.group(1))
            data["layout"].pop("ClassB", None)
            return f"<!--\n{json.dumps(data, indent=4)}\n-->"
        content = re.sub(r"<!--\s*(\{.*?\})\s*-->", remove_classb_from_json, content, flags=re.DOTALL)
        loaded = deserialize(content)
        loaded_b = next(c for c in loaded.classes if c.name == "ClassB")
        self.assertEqual(loaded_b.x, 0.0)
        self.assertEqual(loaded_b.y, 0.0)

    def test_header_title_is_optional(self):
        """Headerセクションがなくても読み込めること"""
        content = "```mermaid\nclassDiagram\n    class ClassC {\n    }\n```\n"
        loaded = deserialize(content)
        self.assertEqual(len(loaded.classes), 1)
        self.assertEqual(loaded.classes[0].name, "ClassC")

    def test_deserialize_malformed_json_falls_back_to_defaults(self):
        """JSONが壊れていてもMermaidセクションは正常に読み込めること"""
        content = (
            "# Title\n\n"
            "```mermaid\nclassDiagram\n    class ClassD {\n    }\n```\n\n"
            "<!-- {\"layout\": } -->\n"
        )
        loaded = deserialize(content)
        self.assertEqual(len(loaded.classes), 1)
        self.assertEqual(loaded.classes[0].x, 0.0)


class TestSaveAndLoadFile(unittest.TestCase):
    """Tests for save_to_file() and load_from_file() file I/O functions."""

    def setUp(self):
        self.diagram = UMLDiagram()
        self.class_a = UMLClass(name="ClassA", x=10.0, y=20.0, width=100.0, height=80.0)
        self.class_a.add_attribute("+attr1")
        self.class_b = UMLClass(name="ClassB", x=200.0, y=150.0)
        self.diagram.add_class(self.class_a)
        self.diagram.add_class(self.class_b)

    def test_save_and_load_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tf:
            tmp_path = tf.name
        try:
            save_to_file(self.diagram, tmp_path, title="Test Diagram")
            # ファイルが存在し、Markdownとして読めること
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("# Test Diagram", content)
            self.assertIn("```mermaid", content)
            # ロードして内容確認
            loaded = load_from_file(tmp_path)
            self.assertEqual(len(loaded.classes), 2)
            loaded_a = next(c for c in loaded.classes if c.name == "ClassA")
            self.assertEqual(loaded_a.x, 10.0)
            self.assertEqual(loaded_a.y, 20.0)
            self.assertEqual(loaded_a.width, 100.0)
            self.assertIn("+attr1", loaded_a.attributes)
        finally:
            os.unlink(tmp_path)

    def test_load_from_file_raises_on_missing_mermaid(self):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tf:
            tf.write("# No mermaid here\n")
            tmp_path = tf.name
        try:
            with self.assertRaises(ValueError):
                load_from_file(tmp_path)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
