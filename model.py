from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

class RelationshipType(Enum):
    GENERALIZATION = auto()
    AGGREGATION = auto()
    COMPOSITION = auto()
    ASSOCIATION = auto()
    DEPENDENCY = auto()
    REALIZATION = auto()

@dataclass
class UMLClass:
    name: str
    attributes: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    width: float = 150.0
    height: float = 100.0

    def add_attribute(self, attribute: str) -> None:
        if attribute not in self.attributes:
            self.attributes.append(attribute)

    def remove_attribute(self, attribute: str) -> None:
        if attribute in self.attributes:
            self.attributes.remove(attribute)

    def add_operation(self, operation: str) -> None:
        if operation not in self.operations:
            self.operations.append(operation)

    def remove_operation(self, operation: str) -> None:
        if operation in self.operations:
            self.operations.remove(operation)

@dataclass
class UMLRelationship:
    type: RelationshipType
    source: UMLClass
    target: UMLClass

@dataclass
class UMLDiagram:
    classes: List[UMLClass] = field(default_factory=list)
    relationships: List[UMLRelationship] = field(default_factory=list)

    def add_class(self, uml_class: UMLClass) -> None:
        if uml_class not in self.classes:
            self.classes.append(uml_class)

    def remove_class(self, uml_class: UMLClass) -> None:
        if uml_class in self.classes:
            self.classes.remove(uml_class)
            # Also remove associated relationships
            self.relationships = [
                r for r in self.relationships 
                if r.source != uml_class and r.target != uml_class
            ]

    def add_relationship(self, relationship: UMLRelationship) -> None:
        if relationship not in self.relationships:
            self.relationships.append(relationship)

    def remove_relationship(self, relationship: UMLRelationship) -> None:
        if relationship in self.relationships:
            self.relationships.remove(relationship)
