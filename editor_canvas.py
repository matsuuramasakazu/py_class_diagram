import tkinter as tk
from tkinter import messagebox
from enum import Enum, auto
import re
import math
from typing import Any, Optional
import tkinter.font as tkfont
from model import UMLClass, UMLRelationship, UMLDiagram, RelationshipType, Point
import rendering
from rendering import (
    draw_class_box, draw_relationship_line,
    HEADER_HEIGHT, ATTR_LINE_HEIGHT, ATTR_PADDING, MIN_COMPARTMENT_HEIGHT, MIN_WIDTH,
    HEADER_FONT, CONTENT_FONT
)
import geometry
import relationship_logic

MERMAID_NAME_REGEX = r"^[a-zA-Z_][a-zA-Z0-9_]*$"

class InteractionMode(Enum):
    SELECT = auto()
    CREATE_RELATIONSHIP = auto()

class HandleType(Enum):
    SOURCE_CONNECT = auto() # P0
    SOURCE_CONTROL = auto() # P1
    TARGET_CONTROL = auto() # P2
    TARGET_CONNECT = auto() # P3

class UMLCanvas(tk.Canvas):
    def __init__(self, master, diagram: UMLDiagram, **kwargs):
        super().__init__(master, **kwargs)
        self.diagram = diagram
        self.mode = InteractionMode.SELECT
        self.current_rel_type = RelationshipType.ASSOCIATION
        
        self.selected_classes: list[UMLClass] = []
        self.selected_relationship: Optional[UMLRelationship] = None
        
        # Interaction state
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.dragging_class: UMLClass | None = None
        self.rubber_band_id: int | None = None
        
        self.temp_line_id: int | None = None
        self.rel_source_class: UMLClass | None = None
        
        # Handle dragging
        self.dragging_handle: Optional[HandleType] = None
        self.active_handle_rel: Optional[UMLRelationship] = None
        
        self._is_committing = False
        
        # Inline editing state
        self.editor_widget: tk.Widget | None = None
        self.editor_window_id: int | None = None
        self.editing_class: UMLClass | None = None
        self.editing_part: str | None = None
        self.original_value: Any = None
        
        # Binds
        self.bind("<Button-1>", self.on_button_press)
        self.bind("<B1-Motion>", self.on_mouse_drag)
        self.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<Double-Button-1>", self.on_double_click)
        
        self.redraw()

    def set_mode(self, mode: InteractionMode, rel_type: RelationshipType | None = None):
        self.mode = mode
        if rel_type:
            self.current_rel_type = rel_type
        self.selected_classes = []
        self.selected_relationship = None
        self.redraw()

    def redraw(self):
        self.delete("all")
        # Draw relationships first
        for rel in self.diagram.relationships:
            rendering.draw_relationship_line(self, rel)

        # Draw classes
        for uml_class in self.diagram.classes:
            rendering.draw_class_box(self, uml_class)
            # Highlight selected classes
            if uml_class in self.selected_classes:
                self.create_rectangle(
                    uml_class.x - 2, uml_class.y - 2,
                    uml_class.x + uml_class.width + 2,
                    uml_class.y + uml_class.height + 2,
                    outline="blue", width=2, dash=(4, 4)
                )
        
        # Draw relationship handles ON TOP of class boxes
        if self.selected_relationship:
            self._draw_relationship_handles(self.selected_relationship)

    def _calculate_bezier_points(self, rel: UMLRelationship) -> tuple[Point, Point, Point, Point]:
        """Calculates P0, P1, P2, P3 for a relationship."""
        # Note: We don't force re-initialization here to respect manual moves
        # But if missing, we initialize.
        if not rel.source_handle or not rel.target_handle:
            relationship_logic.initialize_relationship_handles(rel)
            
        s_rect = relationship_logic.get_class_rect(rel.source)
        t_rect = relationship_logic.get_class_rect(rel.target)
        
        if rel.source == rel.target:
            p0 = (s_rect[0] + s_rect[2] / 2, s_rect[1] + s_rect[3])
            p3 = (s_rect[0] + s_rect[2], s_rect[1] + s_rect[3] / 2)
        else:
            p0, p3 = geometry.get_nearest_connection_points(s_rect, t_rect)
            
        p1 = rel.source_handle
        if not p1:
            p1 = p0
            
        p2 = rel.target_handle
        if not p2:
            p2 = p3
            
        return p0, p1, p2, p3

    def _draw_relationship_handles(self, rel: UMLRelationship):
        p0, p1, p2, p3 = self._calculate_bezier_points(rel)
        
        # Draw handles
        # P0, P3 (Connect): Yellow circles
        r = 4
        self.create_oval(p0[0]-r, p0[1]-r, p0[0]+r, p0[1]+r, fill="yellow", outline="black", tags="handle_p0")
        self.create_oval(p3[0]-r, p3[1]-r, p3[0]+r, p3[1]+r, fill="yellow", outline="black", tags="handle_p3")
        
        # P1, P2 (Control): Blue squares
        r = 3
        self.create_rectangle(p1[0]-r, p1[1]-r, p1[0]+r, p1[1]+r, fill="cyan", outline="black", tags="handle_p1")
        self.create_rectangle(p2[0]-r, p2[1]-r, p2[0]+r, p2[1]+r, fill="cyan", outline="black", tags="handle_p2")
        
        # Connect controls to endpoints for visibility
        self.create_line(p0[0], p0[1], p1[0], p1[1], fill="gray", dash=(2, 2))
        self.create_line(p3[0], p3[1], p2[0], p2[1], fill="gray", dash=(2, 2))

    def find_class_at(self, x, y) -> UMLClass | None:
        for uml_class in reversed(self.diagram.classes):
            if (uml_class.x <= x <= uml_class.x + uml_class.width and
                uml_class.y <= y <= uml_class.y + uml_class.height):
                return uml_class
        return None

    def find_relationship_handle_at(self, x, y) -> tuple[UMLRelationship, HandleType] | None:
        if not self.selected_relationship:
            return None
            
        rel = self.selected_relationship
        p0, p1, p2, p3 = self._calculate_bezier_points(rel)
        
        threshold = 6
        if geometry.distance((x, y), p0) <= threshold:
            return (rel, HandleType.SOURCE_CONNECT)
        if geometry.distance((x, y), p1) <= threshold:
            return (rel, HandleType.SOURCE_CONTROL)
        if geometry.distance((x, y), p2) <= threshold:
            return (rel, HandleType.TARGET_CONTROL)
        if geometry.distance((x, y), p3) <= threshold:
            return (rel, HandleType.TARGET_CONNECT)
        
        return None

    def find_relationship_at(self, x, y) -> UMLRelationship | None:
        # Check distance to bezier curves
        threshold = 5
        hits: list[tuple[float, UMLRelationship]] = []
        
        for rel in self.diagram.relationships:
            p0, p1, p2, p3 = self._calculate_bezier_points(rel)
            
            # Intersection with a small box around cursor
            rect_hit = geometry.find_bezier_rect_intersection(
                p0, p1, p2, p3, x - threshold, y - threshold, threshold * 2, threshold * 2
            )
            if rect_hit:
                # Calculate distance from cursor center to intersection point
                dist = geometry.distance((x, y), rect_hit)
                hits.append((dist, rel))
        
        if hits:
            # Return the closest one
            hits.sort(key=lambda item: item[0])
            return hits[0][1]
            
        return None

    def on_button_press(self, event):
        if self.editor_widget:
            if not self.commit_edit():
                return
            
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        # 1. Check handles (priority)
        if self._handle_handle_press(event):
            return

        clicked_class = self.find_class_at(event.x, event.y)
        
        if self.mode == InteractionMode.SELECT:
            self._handle_select_press(event, clicked_class)
        elif self.mode == InteractionMode.CREATE_RELATIONSHIP:
            self._handle_create_relationship_press(event, clicked_class)

    def _handle_handle_press(self, event) -> bool:
        handle_hit = self.find_relationship_handle_at(event.x, event.y)
        if handle_hit:
            self.active_handle_rel, self.dragging_handle = handle_hit
            self.mode = InteractionMode.SELECT  # Ensure we are in select mode logic for dragging handles
            return True
        return False

    def _handle_select_press(self, event, clicked_class):
        if clicked_class:
            if clicked_class not in self.selected_classes:
                if not (event.state & 0x0001):
                    self.selected_classes = [clicked_class]
                else:
                    self.selected_classes.append(clicked_class)
            self.dragging_class = clicked_class
            self.selected_relationship = None
            self.redraw()
        else:
            # Check relationship click
            rel_hit = self.find_relationship_at(event.x, event.y)
            if rel_hit:
                self.selected_relationship = rel_hit
                self.selected_classes = []
                self.redraw()
            else:
                if not (event.state & 0x0001):
                    self.selected_classes = []
                    self.selected_relationship = None
                self.redraw()
                self.rubber_band_id = self.create_rectangle(
                    event.x, event.y, event.x, event.y,
                    outline="gray", dash=(2, 2)
                )

    def _handle_create_relationship_press(self, event, clicked_class):
        if clicked_class:
            self.rel_source_class = clicked_class
            # Start temp line from center of clicked class
            cx = clicked_class.x + clicked_class.width / 2
            cy = clicked_class.y + clicked_class.height / 2
            self.temp_line_id = self.create_line(
                cx, cy, event.x, event.y,
                dash=(5, 5), fill="red"
            )

    def on_mouse_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        # Handle Dragging
        if self.dragging_handle and self.active_handle_rel:
            rel = self.active_handle_rel
            if self.dragging_handle == HandleType.SOURCE_CONTROL:
                rel.source_handle = (event.x, event.y)
            elif self.dragging_handle == HandleType.TARGET_CONTROL:
                rel.target_handle = (event.x, event.y)
            
            self.redraw()
            
            # Draw extra feedback for Connect handles
            if self.dragging_handle in (HandleType.SOURCE_CONNECT, HandleType.TARGET_CONNECT):
                p0, p1, p2, p3 = self._calculate_bezier_points(rel)
                
                # Feedback from original point to current mouse
                if self.dragging_handle == HandleType.SOURCE_CONNECT:
                    # Dash red from current mouse to P1 (first control point)
                    self.create_line(event.x, event.y, p1[0], p1[1], fill="red", dash=(2, 2), tags="rewire_line")
                    # Dash gray from original P0 to P1 for context
                    self.create_line(p0[0], p0[1], p1[0], p1[1], fill="gray", dash=(2, 2), tags="rewire_line")
                else:
                    # Dash red from current mouse to P2 (second control point)
                    self.create_line(event.x, event.y, p2[0], p2[1], fill="red", dash=(2, 2), tags="rewire_line")
                    # Dash gray from original P3 to P2
                    self.create_line(p3[0], p3[1], p2[0], p2[1], fill="gray", dash=(2, 2), tags="rewire_line")
            return

        if self.mode == InteractionMode.SELECT:
            if self.dragging_class:
                for uml_class in self.selected_classes:
                    uml_class.x += dx
                    uml_class.y += dy
                    self.recompute_relation_handles(uml_class, dx, dy)
                    
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.redraw()
            elif self.rubber_band_id:
                self.coords(self.rubber_band_id, self.drag_start_x, self.drag_start_y, event.x, event.y)
                
        elif self.mode == InteractionMode.CREATE_RELATIONSHIP:
            if self.temp_line_id:
                if not self.rel_source_class:
                    return
                # Update start point to be nearest edge? 
                # For simplicity, keep start at center, update end to cursor
                cx = self.rel_source_class.x + self.rel_source_class.width / 2
                cy = self.rel_source_class.y + self.rel_source_class.height / 2
                self.coords(self.temp_line_id, cx, cy, event.x, event.y)


    def recompute_relation_handles(self, uml_class: UMLClass, dx: float, dy: float):
        """Update absolute handles of any relationship connected to this class."""
        for rel in self.diagram.relationships:
            if rel.source == uml_class and rel.source_handle:
                rel.source_handle = (rel.source_handle[0] + dx, rel.source_handle[1] + dy)
            if rel.target == uml_class and rel.target_handle:
                rel.target_handle = (rel.target_handle[0] + dx, rel.target_handle[1] + dy)

    def on_button_release(self, event):
        # Handle Drop
        if self.dragging_handle and self.active_handle_rel:
            target_class = self.find_class_at(event.x, event.y)
            rel = self.active_handle_rel
            
            if target_class:
                new_source = None
                new_target = None
                
                if self.dragging_handle == HandleType.SOURCE_CONNECT:
                    new_source = target_class
                elif self.dragging_handle == HandleType.TARGET_CONNECT:
                    new_target = target_class
                
                if (new_source and new_source != rel.source) or (new_target and new_target != rel.target):
                    success = relationship_logic.rewire_relationship(
                        self.diagram, rel, new_source, new_target
                    )
                    if not success:
                        messagebox.showwarning("Invalid Operation", "Self-reference not allowed for this relationship type.")
            
            self.dragging_handle = None
            self.active_handle_rel = None
            self.delete("rewire_line")
            self.redraw()
            return

        if self.mode == InteractionMode.SELECT:
            if self.rubber_band_id:
                coords = self.coords(self.rubber_band_id)
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    left, right = min(x1, x2), max(x1, x2)
                    top, bottom = min(y1, y2), max(y1, y2)
                    for uml_class in self.diagram.classes:
                        cx = uml_class.x + uml_class.width / 2
                        cy = uml_class.y + uml_class.height / 2
                        if left <= cx <= right and top <= cy <= bottom:
                            if uml_class not in self.selected_classes:
                                self.selected_classes.append(uml_class)
                self.delete(self.rubber_band_id)
                self.rubber_band_id = None
                self.redraw()
            self.dragging_class = None
            
        elif self.mode == InteractionMode.CREATE_RELATIONSHIP:
            if self.rel_source_class:
                target_class = self.find_class_at(event.x, event.y)
                
                # Logic for creation
                created = False
                if target_class:
                    # Check validity for self-ref
                    # "Association, Aggregation, Composition can be self-ref"
                    # "Gen, Dep, Real cannot"
                    is_self = (target_class == self.rel_source_class)
                    allowed_self = self.current_rel_type in (
                        RelationshipType.ASSOCIATION, 
                        RelationshipType.AGGREGATION, 
                        RelationshipType.COMPOSITION
                    )
                    
                    if not is_self or allowed_self:
                        new_rel = UMLRelationship(self.current_rel_type, self.rel_source_class, target_class)
                        self.diagram.add_relationship(new_rel)
                        relationship_logic.initialize_relationship_handles(new_rel)
                        relationship_logic.update_multiple_relationship_offsets(self.diagram)
                        created = True
                    else:
                        messagebox.showwarning("Invalid Operation", "Self-reference not allowed for this relationship type.")
                
                self.delete(self.temp_line_id)
                self.temp_line_id = None
                self.rel_source_class = None
                self.redraw()

    def on_double_click(self, event):
        clicked_class = self.find_class_at(event.x, event.y)
        if not clicked_class:
            return
            
        rel_y = event.y - clicked_class.y
        header_h = rendering.HEADER_HEIGHT
        attr_h = rendering.get_attr_height(clicked_class)
        minimal_ops_space = rendering.MIN_COMPARTMENT_HEIGHT
        h = clicked_class.height
        attr_h = max(0, min(attr_h, h - header_h - minimal_ops_space))
        
        if rel_y < HEADER_HEIGHT:
            self.start_editing(clicked_class, "name", clicked_class.x, clicked_class.y, clicked_class.width, HEADER_HEIGHT)
        elif rel_y < HEADER_HEIGHT + attr_h:
            self.start_editing(clicked_class, "attributes", clicked_class.x, clicked_class.y + HEADER_HEIGHT, clicked_class.width, attr_h)
        else:
            self.start_editing(clicked_class, "operations", clicked_class.x, clicked_class.y + HEADER_HEIGHT + attr_h, clicked_class.width, clicked_class.height - (HEADER_HEIGHT + attr_h))

    def start_editing(self, uml_class, part, x, y, w, h):
        if self.editor_widget:
            if not self.commit_edit():
                return
            
        self.editing_class = uml_class
        self.editing_part = part

        
        if part == "name":
            self.original_value = uml_class.name
            self.editor_widget = tk.Entry(self, font=("Arial", 10, "bold"), justify="center")
            self.editor_widget.insert(0, uml_class.name)
            self.editor_widget.bind("<Return>", lambda _: self.commit_edit())
        else:
            self.original_value = list(getattr(uml_class, part))
            self.editor_widget = tk.Text(self, font=("Arial", 9), padx=5, pady=5)
            content = "\n".join(getattr(uml_class, part))
            self.editor_widget.insert("1.0", content)
            new_h = self._get_editor_height()
            self.editor_widget.bind("<KeyRelease>", self.update_editor_height)
            h = max(h, new_h)
            
        self.editor_widget.bind("<FocusOut>", lambda _: self.commit_edit())
        self.editor_widget.bind("<Escape>", lambda _: self.cancel_edit())
        
        self.editor_window_id = self.create_window(x, y, window=self.editor_widget, anchor="nw", width=w, height=h)
        self.editor_widget.focus_set()
        if part == "name":
            self.editor_widget.selection_range(0, tk.END)

    def update_class_size(self, uml_class: UMLClass):
        header_f = tkfont.Font(family=HEADER_FONT[0], size=HEADER_FONT[1], weight=HEADER_FONT[2])
        content_f = tkfont.Font(family=CONTENT_FONT[0], size=CONTENT_FONT[1])

        name_width = header_f.measure(uml_class.name)
        content_lines = uml_class.attributes + uml_class.operations
        max_content_width = max((content_f.measure(line) for line in content_lines), default=0)
        
        max_w = max(name_width, max_content_width) + 20
        uml_class.width = max(MIN_WIDTH, max_w)
        
        attr_h = rendering.get_attr_height(uml_class)
        ops_h = rendering.get_ops_height(uml_class)
        uml_class.height = HEADER_HEIGHT + attr_h + ops_h
        
        # Reinitialize handles for relationships connected to this class
        for rel in self.diagram.relationships:
            if rel.source == uml_class or rel.target == uml_class:
                # Reset and recalculate handles for proper anchor alignment
                rel.source_handle = None
                rel.target_handle = None
                relationship_logic.initialize_relationship_handles(rel)
        relationship_logic.update_multiple_relationship_offsets(self.diagram)

    def _get_editor_height(self) -> int:
        if not self.editor_widget or self.editing_part == "name":
            return 0
        line_count = int(float(self.editor_widget.index(tk.END)) - 1.0)
        return (line_count + 1) * ATTR_LINE_HEIGHT + 10

    def update_editor_height(self, event=None):
        new_h = self._get_editor_height()
        if new_h > 0 and self.editor_window_id:
            self.itemconfigure(self.editor_window_id, height=new_h)

    def commit_edit(self, event=None) -> bool:
        if not self.editor_widget or not self.editing_class:
            return True
            
        if self.editing_part == "name":
            if self._is_committing:
                return False
            self._is_committing = True
            try:
                new_value = self.editor_widget.get().strip()
                error_message = None
                if not new_value:
                    error_message = "Class name cannot be empty."
                elif not re.match(MERMAID_NAME_REGEX, new_value):
                    error_message = "Class name must start with a letter or underscore and contain only alphanumeric characters."
                elif any(c.name == new_value for c in self.diagram.classes if c != self.editing_class):
                    error_message = f"A class with name '{new_value}' already exists."

                if error_message:
                    self.editor_widget.unbind("<FocusOut>")
                    messagebox.showerror("Validation Error", error_message)
                    if self.editor_widget:
                        self.editor_widget.bind("<FocusOut>", lambda _: self.commit_edit())
                    return False

                self.editing_class.name = new_value
            finally:
                self._is_committing = False
        else:
            new_value = self.editor_widget.get("1.0", tk.END).strip()
            lines = [line.strip() for line in new_value.split("\n") if line.strip()]
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            setattr(self.editing_class, self.editing_part, unique_lines)
            
        self.update_class_size(self.editing_class)
        self.cleanup_editor()
        self.redraw()
        return True

    def cancel_edit(self, event=None):
        if self.editing_class and self.editing_part:
            setattr(self.editing_class, self.editing_part, self.original_value)
        self.cleanup_editor()
        self.redraw()

    def cleanup_editor(self):
        if self.editor_widget:
            widget = self.editor_widget
            self.editor_widget = None
            widget.destroy()
        self.editing_class = None
        self.editing_part = None

if __name__ == "__main__":
    root = tk.Tk()
    root.title("UML Canvas Test")
    diag = UMLDiagram()
    c1 = UMLClass("ClassA", ["attr1: int"], ["op1()"], x=50, y=50)
    c2 = UMLClass("ClassB", ["attr2: str"], ["op2()"], x=300, y=100)
    diag.add_class(c1)
    diag.add_class(c2)
    diag.add_relationship(UMLRelationship(RelationshipType.GENERALIZATION, c1, c2))
    
    canvas = UMLCanvas(root, diag, width=800, height=600, bg="white")
    canvas.pack(fill=tk.BOTH, expand=True)
    
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill=tk.X)
    
    tk.Button(btn_frame, text="Select Mode", command=lambda: canvas.set_mode(InteractionMode.SELECT)).pack(side=tk.LEFT)
    tk.Button(btn_frame, text="Rel Mode", command=lambda: canvas.set_mode(InteractionMode.CREATE_RELATIONSHIP)).pack(side=tk.LEFT)
    
    root.mainloop()
