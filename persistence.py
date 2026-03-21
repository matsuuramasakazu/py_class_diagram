import json
import re
# No typing imports needed for built-in generics
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
        lines.extend(f"        {attr}" for attr in uml_class.attributes)
        lines.extend(f"        {op}" for op in uml_class.operations)
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

def load_diagram(mermaid_str: str, layout_json: str | None = None) -> UMLDiagram:
    diagram = UMLDiagram()
    class_map: dict[str, UMLClass] = {}
    
    # Layout parsing
    layout_data = {}
    if layout_json:
        layout_data = json.loads(layout_json)
        if not isinstance(layout_data, dict):
            raise ValueError("Layout JSON must be a dictionary mapping class names to position objects.")
        
    def _get_or_create_class(name: str) -> UMLClass:
        if name in class_map:
            return class_map[name]
        
        new_class = UMLClass(name=name)
        if name in layout_data:
            layout_info = layout_data[name]
            new_class.x = layout_info.get("x", 0.0)
            new_class.y = layout_info.get("y", 0.0)
            new_class.width = layout_info.get("w", 150.0)
            new_class.height = layout_info.get("h", 100.0)
            
        diagram.add_class(new_class)
        class_map[name] = new_class
        return new_class
    
    # Regex for class definitions
    # Matches: class Name { ... }
    class_regex = re.compile(r"class\s+(\w+)\s*\{([\s\S]*?)\}", re.MULTILINE)
    
    # Find all classes
    for match in class_regex.finditer(mermaid_str):
        class_name = match.group(1)
        content = match.group(2).strip()
        
        uml_class = _get_or_create_class(class_name)
        
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
        
    # Regex for relationships
    # Matches: Source Symbol Target : Label
    # Symbols: --|>, ..|>, --*, --o, -->, --
    # Sort by length descending to ensure longer symbols match first
    sorted_symbols = sorted(REVERSE_RELATIONSHIP_MAP.keys(), key=len, reverse=True)
    rel_symbols = "|".join([re.escape(s) for s in sorted_symbols])
    rel_regex = re.compile(rf"(\w+)\s+({rel_symbols})\s+(\w+)(?:\s*:\s*\w+)?")
    
    for match in rel_regex.finditer(mermaid_str):
        source_name = match.group(1)
        symbol = match.group(2)
        target_name = match.group(3)
        
        source = _get_or_create_class(source_name)
        target = _get_or_create_class(target_name)
            
        rel_type = REVERSE_RELATIONSHIP_MAP.get(symbol, RelationshipType.ASSOCIATION)
        relationship = UMLRelationship(type=rel_type, source=source, target=target)
        diagram.add_relationship(relationship)
        
    return diagram
