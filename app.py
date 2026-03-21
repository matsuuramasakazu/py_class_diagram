import tkinter as tk
from tkinter import filedialog, messagebox
import os

from model import UMLDiagram, UMLClass, RelationshipType
from editor_canvas import UMLCanvas, InteractionMode
import persistence
import rendering

class UMLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UML Class Diagram Tool")
        self.root.geometry("1000x700")

        self.diagram = UMLDiagram()
        self.current_file = None

        # Create UI components
        self.create_toolbar()
        
        self.canvas = UMLCanvas(self.root, self.diagram, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Setup keyboard shortcuts
        self.root.bind("<Delete>", self.on_delete_key)
        self.root.bind("<Control-s>", self.on_ctrl_s)

    def create_toolbar(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # File operations
        save_btn = tk.Button(toolbar, text="Save", command=self.save_diagram)
        save_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        load_btn = tk.Button(toolbar, text="Load", command=self.load_diagram)
        load_btn.pack(side=tk.LEFT, padx=2, pady=2)

        tk.Frame(toolbar, width=2, bd=1, relief=tk.SUNKEN).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Edit operations
        add_class_btn = tk.Button(toolbar, text="Add Class", command=self.add_class)
        add_class_btn.pack(side=tk.LEFT, padx=2, pady=2)

        tk.Frame(toolbar, width=2, bd=1, relief=tk.SUNKEN).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Modes
        self.mode_var = tk.StringVar(value="SELECT")
        
        select_rb = tk.Radiobutton(toolbar, text="Select", variable=self.mode_var, value="SELECT", 
                                  indicatoron=0, command=self.update_mode)
        select_rb.pack(side=tk.LEFT, padx=2, pady=2)

        rel_types = [
            ("Association", RelationshipType.ASSOCIATION),
            ("Generalization", RelationshipType.GENERALIZATION),
            ("Aggregation", RelationshipType.AGGREGATION),
            ("Composition", RelationshipType.COMPOSITION),
            ("Dependency", RelationshipType.DEPENDENCY),
            ("Realization", RelationshipType.REALIZATION),
        ]

        for text, rel_type in rel_types:
            rb = tk.Radiobutton(toolbar, text=text, variable=self.mode_var, value=rel_type.name, 
                               indicatoron=0, command=self.update_mode)
            rb.pack(side=tk.LEFT, padx=2, pady=2)

    def update_mode(self):
        mode_name = self.mode_var.get()
        if mode_name == "SELECT":
            self.canvas.set_mode(InteractionMode.SELECT)
        else:
            rel_type = RelationshipType[mode_name]
            self.canvas.set_mode(InteractionMode.CREATE_RELATIONSHIP, rel_type)

    def add_class(self):
        if not self.canvas.commit_edit():
            return
            
        offset = len(self.diagram.classes) * 20
        new_x, new_y = 100 + offset, 100 + offset
        
        # Make name unique
        base_name = "NewClass"
        name = base_name
        counter = 1
        while any(c.name == name for c in self.diagram.classes):
            name = f"{base_name}_{counter}"
            counter += 1
            
        new_class = UMLClass(name=name, x=new_x, y=new_y)
        self.canvas.update_class_size(new_class)
        self.diagram.add_class(new_class)
        self.canvas.redraw()
        # Trigger inline editing for the name
        self.canvas.start_editing(new_class, "name", new_class.x, new_class.y, new_class.width, rendering.HEADER_HEIGHT)

    def save_diagram(self):
        if not self.current_file:
            file_path = filedialog.asksaveasfilename(defaultextension=".md",
                                                     filetypes=[("Markdown files", "*.md"), ("All files", "*.*")])
            if not file_path:
                return
            self.current_file = file_path

        title = os.path.splitext(os.path.basename(self.current_file))[0]
        try:
            persistence.save_to_file(self.diagram, self.current_file, title=title)
            self.root.title(f"UML Class Diagram Tool - {os.path.basename(self.current_file)}")
            messagebox.showinfo("Save", "Diagram saved successfully.")
        except OSError as e:
            messagebox.showerror("Save Error", f"Failed to save diagram: {e}")

    def load_diagram(self):
        file_path = filedialog.askopenfilename(filetypes=[("Markdown files", "*.md"), ("All files", "*.*")])
        if not file_path:
            return

        try:
            new_diagram = persistence.load_from_file(file_path)
            self.diagram.classes[:] = new_diagram.classes
            self.diagram.relationships[:] = new_diagram.relationships
            self.canvas.selected_classes = []
            
            self.current_file = file_path
            self.root.title(f"UML Class Diagram Tool - {os.path.basename(self.current_file)}")
            self.canvas.redraw()
            messagebox.showinfo("Load", "Diagram loaded successfully.")
        except (OSError, ValueError) as e:
            messagebox.showerror("Load Error", f"Failed to load diagram: {e}")

    def on_delete_key(self, event):
        if self.canvas.editor_widget:
            return # Don't delete classes while editing
            
        if self.canvas.selected_classes and messagebox.askyesno(
            "Delete", f"Delete {len(self.canvas.selected_classes)} selected class(es)?"
        ):
            for uml_class in list(self.canvas.selected_classes):
                self.diagram.remove_class(uml_class)
            self.canvas.selected_classes = []
            self.canvas.redraw()

    def on_ctrl_s(self, event):
        self.save_diagram()

if __name__ == "__main__":
    root = tk.Tk()
    app = UMLApp(root)
    root.mainloop()
