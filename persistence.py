import json
import re
from typing import Optional, Dict
from model import UMLDiagram, UMLClass, UMLRelationship, RelationshipType

RELATIONSHIP_MAP = {
    RelationshipType.GENERALIZATION: "--|>",
    RelationshipType.REALIZATION: "..|>",
    RelationshipType.COMPOSITION: "--*",
    RelationshipType.AGGREGATION: "--o",
    RelationshipType.DEPENDENCY: "-->",
    RelationshipType.ASSOCIATION: "--",
}

REVERSE_RELATIONSHIP_MAP = {v: k for k, v in RELATIONSHIP_MAP.items()}

def to_mermaid(diagram: UMLDiagram) -> str:
    lines = ["classDiagram"]
    
    # Add classes
    for uml_class in diagram.classes:
        lines.append(f"    class {uml_class.name} {{")
        for attr in uml_class.attributes:
            lines.append(f"        {attr}")
        for op in uml_class.operations:
            lines.append(f"        {op}")
        lines.append("    }")
    
    # Add relationships
    for rel in diagram.relationships:
        symbol = RELATIONSHIP_MAP.get(rel.type, "--")
        lines.append(f"    {rel.source.name} {symbol} {rel.target.name} : {rel.type.name.lower()}")
        
    return "\n".join(lines)

def to_layout_json(diagram: UMLDiagram) -> str:
    layout = {}
    for uml_class in diagram.classes:
        layout[uml_class.name] = {
            "x": uml_class.x,
            "y": uml_class.y,
            "w": uml_class.width,
            "h": uml_class.height
        }
    return json.dumps(layout, indent=4)

def load_diagram(mermaid_str: str, layout_json: Optional[str] = None) -> UMLDiagram:
    diagram = UMLDiagram()
    class_map: Dict[str, UMLClass] = {}
    
    # Layout parsing
    layout_data = {}
    if layout_json:
        layout_data = json.loads(layout_json)
    
    # Regex for class definitions
    # Matches: class Name { ... }
    class_regex = re.compile(r"class\s+(\w+)\s*\{([\s\S]*?)\}", re.MULTILINE)
    
    # Find all classes
    for match in class_regex.finditer(mermaid_str):
        class_name = match.group(1)
        content = match.group(2).strip()
        
        uml_class = UMLClass(name=class_name)
        
        # Split content into lines and extract attributes/operations
        # Simple heuristic: if it ends with (), it's an operation
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if "(" in line and ")" in line:
                uml_class.add_operation(line)
            else:
                uml_class.add_attribute(line)
        
        # Apply layout if available
        if class_name in layout_data:
            l = layout_data[class_name]
            uml_class.x = l.get("x", 0.0)
            uml_class.y = l.get("y", 0.0)
            uml_class.width = l.get("w", 150.0)
            uml_class.height = l.get("h", 100.0)
            
        diagram.add_class(uml_class)
        class_map[class_name] = uml_class
        
    # Regex for relationships
    # Matches: Source Symbol Target : Label
    # Symbols: --|>, ..|>, --*, --o, -->, --
    rel_symbols = "|".join([re.escape(s) for s in REVERSE_RELATIONSHIP_MAP.keys()])
    rel_regex = re.compile(rf"(\w+)\s+({rel_symbols})\s+(\w+)(?:\s*:\s*\w+)?")
    
    for match in rel_regex.finditer(mermaid_str):
        source_name = match.group(1)
        symbol = match.group(2)
        target_name = match.group(3)
        
        source = class_map.get(source_name)
        target = class_map.get(target_name)
        
        if not source:
            source = UMLClass(name=source_name)
            if source_name in layout_data:
                l = layout_data[source_name]
                source.x = l.get("x", 0.0)
                source.y = l.get("y", 0.0)
                source.width = l.get("w", 150.0)
                source.height = l.get("h", 100.0)
            diagram.add_class(source)
            class_map[source_name] = source
            
        if not target:
            target = UMLClass(name=target_name)
            if target_name in layout_data:
                l = layout_data[target_name]
                target.x = l.get("x", 0.0)
                target.y = l.get("y", 0.0)
                target.width = l.get("w", 150.0)
                target.height = l.get("h", 100.0)
            diagram.add_class(target)
            class_map[target_name] = target
            
        rel_type = REVERSE_RELATIONSHIP_MAP.get(symbol, RelationshipType.ASSOCIATION)
        relationship = UMLRelationship(type=rel_type, source=source, target=target)
        diagram.add_relationship(relationship)
        
    return diagram
