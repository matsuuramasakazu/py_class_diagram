import tkinter as tk
from tkinter import messagebox
from enum import Enum, auto
import re
import rendering
from typing import Any
import tkinter.font as tkfont
from model import UMLClass, UMLRelationship, UMLDiagram, RelationshipType
from rendering import (
    draw_class_box, draw_relationship_line,
    HEADER_HEIGHT, ATTR_LINE_HEIGHT, ATTR_PADDING, MIN_COMPARTMENT_HEIGHT, MIN_WIDTH,
    HEADER_FONT, CONTENT_FONT, get_attr_height, get_ops_height
)

MERMAID_NAME_REGEX = r"^[a-zA-Z_][a-zA-Z0-9_]*$"

class InteractionMode(Enum):
    SELECT = auto()
    CREATE_RELATIONSHIP = auto()

class UMLCanvas(tk.Canvas):
    def __init__(self, master, diagram: UMLDiagram, **kwargs):
        super().__init__(master, **kwargs)
        self.diagram = diagram
        self.mode = InteractionMode.SELECT
        self.current_rel_type = RelationshipType.ASSOCIATION
        self.selected_classes: list[UMLClass] = []
        
        # Interaction state
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.dragging_class: UMLClass | None = None
        self.rubber_band_id: int | None = None
        self.temp_line_id: int | None = None
        self.rel_source_class: UMLClass | None = None
        
        self._is_committing = False # To prevent re-entrant calls
        
        # Inline editing state
        self.editor_widget: tk.Widget | None = None
        self.editor_window_id: int | None = None
        self.editing_class: UMLClass | None = None
        self.editing_part: str | None = None
        self.original_value: Any = None # Store value before editing
        
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
        self.redraw()

    def redraw(self):
        self.delete("all")
        # Draw relationships first so they are behind classes
        for rel in self.diagram.relationships:
            rendering.draw_relationship_line(self, rel)
            
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

    def find_class_at(self, x, y) -> UMLClass | None:
        for uml_class in reversed(self.diagram.classes):
            if (uml_class.x <= x <= uml_class.x + uml_class.width and
                uml_class.y <= y <= uml_class.y + uml_class.height):
                return uml_class
        return None

    def on_button_press(self, event):
        if self.editor_widget:
            if not self.commit_edit():
                return # Still editing due to validation error, don't select or drag
            
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        clicked_class = self.find_class_at(event.x, event.y)
        
        if self.mode == InteractionMode.SELECT:
            if clicked_class:
                if clicked_class not in self.selected_classes:
                    if not (event.state & 0x0001): # Shift not pressed
                        self.selected_classes = [clicked_class]
                    else:
                        self.selected_classes.append(clicked_class)
                self.dragging_class = clicked_class
                self.redraw()
            else:
                if not (event.state & 0x0001):
                    self.selected_classes = []
                self.redraw()
                # Start rubber-band selection
                self.rubber_band_id = self.create_rectangle(
                    event.x, event.y, event.x, event.y,
                    outline="gray", dash=(2, 2)
                )
            
        elif self.mode == InteractionMode.CREATE_RELATIONSHIP:
            if clicked_class:
                self.rel_source_class = clicked_class
                self.temp_line_id = self.create_line(
                    event.x, event.y, event.x, event.y,
                    dash=(5, 5), fill="red"
                )

    def on_mouse_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        if self.mode == InteractionMode.SELECT:
            if self.dragging_class:
                # Move all selected classes
                for uml_class in self.selected_classes:
                    uml_class.x += dx
                    uml_class.y += dy
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.redraw()
            elif self.rubber_band_id:
                self.coords(self.rubber_band_id, self.drag_start_x, self.drag_start_y, event.x, event.y)
                
        elif self.mode == InteractionMode.CREATE_RELATIONSHIP:
            if self.temp_line_id:
                self.coords(self.temp_line_id, self.drag_start_x, self.drag_start_y, event.x, event.y)

    def on_button_release(self, event):
        if self.mode == InteractionMode.SELECT:
            if self.rubber_band_id:
                # Finalize selection
                coords = self.coords(self.rubber_band_id)
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    # Normalize coordinates
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
                if target_class and target_class != self.rel_source_class:
                    new_rel = UMLRelationship(self.current_rel_type, self.rel_source_class, target_class)
                    self.diagram.add_relationship(new_rel)
                
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
        # Apply the same constraints as rendering
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
        if self.editor_widget and not self.commit_edit():
            return
            
        self.editing_class = uml_class
        self.editing_part = part
        
        # Store original value for cancellation
        if part == "name":
            self.original_value = uml_class.name
        else:
            self.original_value = list(getattr(uml_class, part))
        
        if part == "name":
            self.editor_widget = tk.Entry(self, font=("Arial", 10, "bold"), justify="center")
            self.editor_widget.insert(0, uml_class.name)
            self.editor_widget.bind("<Return>", lambda _: self.commit_edit())
        else:
            self.editor_widget = tk.Text(self, font=("Arial", 9), padx=5, pady=5)
            content = "\n".join(getattr(uml_class, part))
            self.editor_widget.insert("1.0", content)
            
            # Adjust initial height
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
        """Calculate and update the optimal size for a class box based on its content."""
        header_f = tkfont.Font(family=HEADER_FONT[0], size=HEADER_FONT[1], weight=HEADER_FONT[2])
        content_f = tkfont.Font(family=CONTENT_FONT[0], size=CONTENT_FONT[1])

        name_width = header_f.measure(uml_class.name)
        content_lines = uml_class.attributes + uml_class.operations
        max_content_width = max((content_f.measure(line) for line in content_lines), default=0)
        
        # Max of all widths + padding
        max_w = max(name_width, max_content_width) + 20
        uml_class.width = max(MIN_WIDTH, max_w)
        
        # Height: Header + Attr area + Ops area
        attr_h = rendering.get_attr_height(uml_class)
        ops_h = rendering.get_ops_height(uml_class)
        uml_class.height = HEADER_HEIGHT + attr_h + ops_h

    def _get_editor_height(self) -> int:
        """Calculate required height for text editor based on line count."""
        if not self.editor_widget or self.editing_part == "name":
            return 0
        # For tk.Text widget used in attributes/operations
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
                # Mermaid compatible: Alphanumeric and underscores, not starting with a digit
                new_value = self.editor_widget.get().strip()
                
                # Combined validation
                error_message = None
                if not new_value:
                    error_message = "Class name cannot be empty."
                elif not re.match(MERMAID_NAME_REGEX, new_value):
                    error_message = "Class name must start with a letter or underscore and contain only alphanumeric characters."
                elif any(c.name == new_value for c in self.diagram.classes if c != self.editing_class):
                    error_message = f"A class with name '{new_value}' already exists."

                if error_message:
                    # Unbind FocusOut to avoid recursive calls while showing dialog
                    self.editor_widget.unbind("<FocusOut>")
                    messagebox.showerror("Validation Error", error_message)
                    if self.editor_widget:
                        self.editor_widget.bind("<FocusOut>", lambda _: self.commit_edit())
                    return False # Stay in edit mode

                self.editing_class.name = new_value
            finally:
                self._is_committing = False
        else:
            # For Text widget, we need to handle multi-line input
            new_value = self.editor_widget.get("1.0", tk.END).strip()
            lines = [line.strip() for line in new_value.split("\n") if line.strip()]
            # Remove duplicates while preserving order
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
            # We must be careful not to trigger FocusOut again during destruction
            widget = self.editor_widget
            self.editor_widget = None # Set to None before destroying
            widget.destroy()
        self.editing_class = None
        self.editing_part = None

if __name__ == "__main__":
    # Simple test
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
