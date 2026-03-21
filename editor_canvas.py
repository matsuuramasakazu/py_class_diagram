import tkinter as tk
from enum import Enum, auto
from typing import Optional
from model import UMLClass, UMLRelationship, UMLDiagram, RelationshipType
import rendering

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
        self.dragging_class: Optional[UMLClass] = None
        self.rubber_band_id: Optional[int] = None
        self.temp_line_id: Optional[int] = None
        self.rel_source_class: Optional[UMLClass] = None
        
        # Inline editing state
        self.editor_widget: Optional[tk.Widget] = None
        self.editing_class: Optional[UMLClass] = None
        self.editing_part: Optional[str] = None
        
        # Binds
        self.bind("<Button-1>", self.on_button_press)
        self.bind("<B1-Motion>", self.on_mouse_drag)
        self.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<Double-Button-1>", self.on_double_click)
        
        self.redraw()

    def set_mode(self, mode: InteractionMode, rel_type: Optional[RelationshipType] = None):
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

    def find_class_at(self, x, y) -> Optional[UMLClass]:
        for uml_class in reversed(self.diagram.classes):
            if (uml_class.x <= x <= uml_class.x + uml_class.width and
                uml_class.y <= y <= uml_class.y + uml_class.height):
                return uml_class
        return None

    def on_button_press(self, event):
        if self.editor_widget:
            self.commit_edit()
            
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
        minimal_ops_space = 20
        h = clicked_class.height
        attr_h = min(attr_h, h - header_h - minimal_ops_space)
        if attr_h < 0:
            attr_h = 0
        
        if rel_y < header_h:
            self.start_editing(clicked_class, "name", clicked_class.x, clicked_class.y, clicked_class.width, header_h)
        elif rel_y < header_h + attr_h:
            self.start_editing(clicked_class, "attributes", clicked_class.x, clicked_class.y + header_h, clicked_class.width, attr_h)
        else:
            self.start_editing(clicked_class, "operations", clicked_class.x, clicked_class.y + header_h + attr_h, clicked_class.width, clicked_class.height - (header_h + attr_h))

    def start_editing(self, uml_class, part, x, y, w, h):
        if self.editor_widget:
            self.commit_edit()
            
        self.editing_class = uml_class
        self.editing_part = part
        
        if part == "name":
            self.editor_widget = tk.Entry(self, font=("Arial", 10, "bold"), justify="center")
            self.editor_widget.insert(0, uml_class.name)
            self.editor_widget.bind("<Return>", lambda _: self.commit_edit())
        else:
            self.editor_widget = tk.Text(self, font=("Arial", 9), padx=5, pady=5)
            content = "\n".join(getattr(uml_class, part))
            self.editor_widget.insert("1.0", content)
            
        self.editor_widget.bind("<FocusOut>", lambda _: self.commit_edit())
        self.editor_widget.bind("<Escape>", lambda _: self.cancel_edit())
        
        self.create_window(x, y, window=self.editor_widget, anchor="nw", width=w, height=h)
        self.editor_widget.focus_set()
        if part == "name":
            self.editor_widget.selection_range(0, tk.END)

    def commit_edit(self, event=None):
        if not self.editor_widget or not self.editing_class:
            return
            
        if self.editing_part == "name":
            new_value = self.editor_widget.get().strip()
            if new_value:
                self.editing_class.name = new_value
        else:
            # For Text widget, we need to handle multi-line input
            new_value = self.editor_widget.get("1.0", tk.END).strip()
            lines = [line.strip() for line in new_value.split("\n") if line.strip()]
            setattr(self.editing_class, self.editing_part, lines)
            
        self.cleanup_editor()
        self.redraw()

    def cancel_edit(self, event=None):
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
