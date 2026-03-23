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
    layout = {
        "classes": {},
        "relationships": []
    }
    for uml_class in diagram.classes:
        layout["classes"][uml_class.name] = {
            "x": uml_class.x,
            "y": uml_class.y,
            "w": uml_class.width,
            "h": uml_class.height
        }
        
    for rel in diagram.relationships:
        rel_data = {
            "source": rel.source.name,
            "target": rel.target.name,
            "type": rel.type.name,
            "source_handle": rel.source_handle,
            "target_handle": rel.target_handle
        }
        layout["relationships"].append(rel_data)
        
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
    
    Extracts the correct JSON data section and its preceding Mermaid section.
    
    Raises:
        ValueError: If a valid Mermaid classDiagram section cannot be found.
    """
    layout_data = {}
    tool_comment_start = len(file_content)
    
    # 1. Scan for the correct tool JSON comment block
    for match in re.finditer(r"<!--\s*(\{.*?\})\s*-->", file_content, re.DOTALL):
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and parsed.get("tool") == _TOOL_IDENTIFIER:
                layout_data = parsed.get("layout", {})
                if not isinstance(layout_data, dict):
                    layout_data = {}
                tool_comment_start = match.start()
                break  # Pick the first valid tool comment matching our identifier
        except json.JSONDecodeError:
            continue

    # 2. Extract Mermaid section containing 'classDiagram' BEFORE the tool comment
    # Use re.finditer to find all mermaid blocks and pick the one closest to the tool comment
    mermaid_matches = []
    for match in re.finditer(r"```mermaid\s*(.*?)\s*```", file_content[:tool_comment_start], re.DOTALL):
        content = match.group(1).strip()
        # Look for 'classDiagram' at the start or on a new line (with word boundary)
        if re.search(r"(?:^|\n)\s*classDiagram\b", content):
            mermaid_matches.append(content)
    
    if not mermaid_matches:
        raise ValueError("Mermaid classDiagram section not found in file content.")
    
    # Pick the last classDiagram block before the tool comment (in case there are multiple)
    mermaid_str = mermaid_matches[-1]
    
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
    
    # Handle backward compatibility where layout_data might be just the class dict
    classes_layout = layout_data.get("classes", layout_data)
    relationships_layout = layout_data.get("relationships", [])

    def _get_or_create_class(name: str) -> UMLClass:
        if name in class_map:
            return class_map[name]
        
        new_class = UMLClass(name=name)
        if name in classes_layout:
            layout_info = classes_layout[name]
            if isinstance(layout_info, dict):
                def _coerce_float(value: object, default: float) -> float:
                    try:
                        return float(value) # type: ignore
                    except (TypeError, ValueError):
                        return default

                new_class.x = _coerce_float(layout_info.get("x"), new_class.x)
                new_class.y = _coerce_float(layout_info.get("y"), new_class.y)
                new_class.width = _coerce_float(layout_info.get("w"), new_class.width)
                new_class.height = _coerce_float(layout_info.get("h"), new_class.height)
            
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
        
        # Try to find matching layout data
        # We search for the first matching relationship in the layout data that hasn't been used?
        # Or just find one that matches. Since we don't track IDs, we might collide.
        # But iterating through the list is fine.
        
        # Improvement: Filter relationships_layout to find a match
        found_layout = None
        for i, r_data in enumerate(relationships_layout):
            if (r_data.get("source") == source_name and 
                r_data.get("target") == target_name and 
                r_data.get("type") == rel_type.name):
                found_layout = r_data
                # Optional: Remove from list to avoid reusing? 
                # But that modifies the input list which might be bad if we re-parse.
                # Since we rebuild the diagram from scratch, we can just use the first match?
                # If there are duplicates, this strategy always picks the first one.
                # If the json has 2 relationships and mermaid has 2, we want to map 1-1, 2-2.
                # So popping is better.
                relationships_layout.pop(i)
                break
        
        if found_layout:
            sh = found_layout.get("source_handle")
            th = found_layout.get("target_handle")
            if sh and isinstance(sh, (list, tuple)) and len(sh) == 2:
                relationship.source_handle = (float(sh[0]), float(sh[1]))
            if th and isinstance(th, (list, tuple)) and len(th) == 2:
                relationship.target_handle = (float(th[0]), float(th[1]))
            
        if not diagram.add_relationship(relationship):
            print(f"Warning: Failed to add duplicate relationship: {relationship.type.name} between {relationship.source.name} and {relationship.target.name}")
            
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
