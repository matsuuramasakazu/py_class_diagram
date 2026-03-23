from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

Point = tuple[float, float]

# No typing imports needed for built-in generics

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
    attributes: list[str] = field(default_factory=list)
    operations: list[str] = field(default_factory=list)
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
    source_handle: Optional[Point] = None
    target_handle: Optional[Point] = None
    source_side: Optional[int] = None  # 0:Top, 1:Right, 2:Bottom, 3:Left
    target_side: Optional[int] = None


@dataclass
class UMLDiagram:
    classes: list[UMLClass] = field(default_factory=list)
    relationships: list[UMLRelationship] = field(default_factory=list)

    def add_class(self, uml_class: UMLClass) -> None:
        if uml_class not in self.classes:
            self.classes.append(uml_class)

    def remove_class(self, uml_class: UMLClass) -> None:
        if uml_class in self.classes:
            self.classes.remove(uml_class)
            # Also remove associated relationships
            self.relationships[:] = [
                r for r in self.relationships 
                if uml_class not in (r.source, r.target)
            ]

    def add_relationship(self, relationship: UMLRelationship) -> bool:
        """
        Adds a relationship to the diagram with constraints.
        Returns True if added, False if rejected (e.g. duplicate generalization).
        """
        # Constraint: Only one GENERALIZATION or REALIZATION between the same two classes
        if relationship.type in (RelationshipType.GENERALIZATION, RelationshipType.REALIZATION):
            for existing in self.relationships:
                if (existing.type == relationship.type and 
                    existing.source == relationship.source and 
                    existing.target == relationship.target):
                    return False

        # Use identity check for the final check to allow multiple identical-value relationships
        # if they are different objects (except for the constrained types above)
        if not any(r is relationship for r in self.relationships):
            self.relationships.append(relationship)
            return True
        return False

    def remove_relationship(self, relationship: UMLRelationship) -> None:
        if relationship in self.relationships:
            self.relationships.remove(relationship)
