import tkinter as tk
from tkinter import filedialog, messagebox
import os

from model import UMLDiagram, UMLClass, RelationshipType
from editor_canvas import UMLCanvas, InteractionMode
import persistence

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
        new_class = UMLClass(name="NewClass", x=100, y=100)
        self.diagram.add_class(new_class)
        self.canvas.redraw()
        # Trigger inline editing for the name
        self.canvas.start_editing(new_class, "name", new_class.x, new_class.y, new_class.width, 25)

    def save_diagram(self):
        if not self.current_file:
            file_path = filedialog.asksaveasfilename(defaultextension=".mermaid",
                                                     filetypes=[("Mermaid files", "*.mermaid"), ("All files", "*.*")])
            if not file_path:
                return
            self.current_file = file_path

        mermaid_content = persistence.to_mermaid(self.diagram)
        layout_content = persistence.to_layout_json(self.diagram)

        try:
            with open(self.current_file, "w") as f:
                f.write(mermaid_content)
            
            layout_file = os.path.splitext(self.current_file)[0] + ".json"
            with open(layout_file, "w") as f:
                f.write(layout_content)
            
            self.root.title(f"UML Class Diagram Tool - {os.path.basename(self.current_file)}")
            messagebox.showinfo("Save", "Diagram saved successfully.")
        except (OSError, IOError) as e:
            messagebox.showerror("Save Error", f"Failed to save diagram: {e}")

    def load_diagram(self):
        file_path = filedialog.askopenfilename(filetypes=[("Mermaid files", "*.mermaid"), ("All files", "*.*")])
        if not file_path:
            return

        try:
            with open(file_path, "r") as f:
                mermaid_content = f.read()
            
            layout_file = os.path.splitext(file_path)[0] + ".json"
            layout_content = None
            if os.path.exists(layout_file):
                with open(layout_file, "r") as f:
                    layout_content = f.read()
            
            new_diagram = persistence.load_diagram(mermaid_content, layout_content)
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
        if self.canvas.selected_classes:
            if messagebox.askyesno("Delete", f"Delete {len(self.canvas.selected_classes)} selected class(es)?"):
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
