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

_TOOL_IDENTIFIER = "py_class_diagram"


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


def _to_layout_dict(diagram: UMLDiagram) -> dict:
    layout = {}
    for uml_class in diagram.classes:
        layout[uml_class.name] = {
            "x": uml_class.x,
            "y": uml_class.y,
            "w": uml_class.width,
            "h": uml_class.height
        }
    return layout


def to_layout_json(diagram: UMLDiagram) -> str:
    return json.dumps(_to_layout_dict(diagram), indent=4)


def serialize(diagram: UMLDiagram, title: str = "Class Diagram") -> str:
    """Serialize a UMLDiagram to the 3-section Markdown format.
    
    Format:
        # <title>
        
        ```mermaid
        <mermaid content>
        ```
        
        <!-- {"tool": ..., "layout": {...}} -->
    """
    mermaid_content = to_mermaid(diagram)
    data_section = {
        "tool": _TOOL_IDENTIFIER,
        "layout": _to_layout_dict(diagram),
    }
    json_str = json.dumps(data_section, indent=4)
    
    return (
        f"# {title}\n\n"
        f"```mermaid\n{mermaid_content}\n```\n\n"
        f"<!--\n{json_str}\n-->\n"
    )


def save_to_file(diagram: UMLDiagram, file_path: str, title: str = "Class Diagram") -> None:
    """Serialize a UMLDiagram and write it to a file."""
    content = serialize(diagram, title)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def deserialize(file_content: str) -> UMLDiagram:
    """Deserialize a UMLDiagram from the 3-section Markdown format.
    
    Extracts the Mermaid section and the JSON data section using regex,
    then reconstructs the UMLDiagram with layout information.
    Falls back to (0, 0) placement for classes missing layout data.
    
    Raises:
        ValueError: If the Mermaid section cannot be found in the content.
    """
    # Extract Mermaid section
    mermaid_match = re.search(r"```mermaid\s+(.*?)\s+```", file_content, re.DOTALL)
    if not mermaid_match:
        raise ValueError("Mermaid section not found in file content.")
    mermaid_str = mermaid_match.group(1)
    
    # Extract JSON data section (HTML comment)
    layout_data = {}
    json_match = re.search(r"<!--\s*(\{.*?\})\s*-->", file_content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, dict):
                layout_data = parsed.get("layout", {})
                if not isinstance(layout_data, dict):
                    layout_data = {}
        except json.JSONDecodeError:
            layout_data = {}
    
    return _parse_mermaid(mermaid_str, layout_data)


def load_from_file(file_path: str) -> UMLDiagram:
    """Read a Markdown file and deserialize a UMLDiagram from it."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return deserialize(content)


def _parse_mermaid(mermaid_str: str, layout_data: dict) -> UMLDiagram:
    """Parse Mermaid classDiagram text and layout data into a UMLDiagram."""
    diagram = UMLDiagram()
    class_map: dict[str, UMLClass] = {}

    def _get_or_create_class(name: str) -> UMLClass:
        if name in class_map:
            return class_map[name]
        
        new_class = UMLClass(name=name)
        if name in layout_data:
            layout_info = layout_data[name]
            new_class.x = float(layout_info.get("x", 0.0))
            new_class.y = float(layout_info.get("y", 0.0))
            new_class.width = float(layout_info.get("w", 150.0))
            new_class.height = float(layout_info.get("h", 100.0))
        # Fallback: classes not in layout_data stay at default (0.0, 0.0)
            
        diagram.add_class(new_class)
        class_map[name] = new_class
        return new_class
    
    # Regex for class definitions: class Name { ... }
    class_regex = re.compile(r"class\s+(\w+)\s*\{([\s\S]*?)\}", re.MULTILINE)
    
    for match in class_regex.finditer(mermaid_str):
        class_name = match.group(1)
        content = match.group(2).strip()
        
        uml_class = _get_or_create_class(class_name)
        
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


# --- Legacy API (kept for backward compatibility within tests) ---
def load_diagram(mermaid_str: str, layout_json: str | None = None) -> UMLDiagram:
    """Load a UMLDiagram from a Mermaid string and optional layout JSON string.
    
    This function is kept for use in unit tests.
    For file I/O, use load_from_file() instead.
    """
    layout_data = {}
    if layout_json:
        parsed = json.loads(layout_json)
        if not isinstance(parsed, dict):
            raise ValueError("Layout JSON must be a dictionary mapping class names to position objects.")
        layout_data = parsed
    return _parse_mermaid(mermaid_str, layout_data)
