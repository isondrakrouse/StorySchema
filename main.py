# StorySchema v1.0.2 UI
# Copyright © 2026 Isondra Krouse. All rights reserved.

import tkinter as tk
from tkinter import messagebox, ttk
from database_manager import DatabaseManager

class StorySchemaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StorySchema v1.1")

        # A\N instead of assigned default window size, opt for zoom state on launch
        self.root.state('zoomed')

        # Initialize Backend
        self.db = DatabaseManager()

        # State Tracking
        self.current_world_id = None

        # Main Container
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        self.show_world_selector()

    def clear_screen(self):
        """Clears the main container for frame switching."""
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def show_world_selector(self):
        """The landing screen to pick or create a world."""
        self.clear_screen()

        tk.Label(self.main_container, text="Select a World", font=("Arial", 16, "bold")).pack(pady=10)

        # Listbox for existing worlds
        self.world_list = tk.Listbox(self.main_container, height=10)
        self.world_list.pack(fill="x", pady=5)

        # Populate worlds from DB
        worlds = self.db.get_all_worlds()
        for w in worlds:
            self.world_list.insert(tk.END, w['world_name'])
        
        btn_frame = tk.Frame(self.main_container)
        btn_frame.pack(fill="x", pady=10)

        tk.Button(btn_frame, text="Open World", command=self.load_world).pack(side="left", expand=True, fill="x")
        tk.Button(btn_frame, text="New World", command=self.show_world_creator).pack(side="right", expand=True, fill="x")

    def show_world_creator(self):
        """Screen to input a new world name and description."""
        self.clear_screen()

        tk.Label(self.main_container, text="Create New World", font=("Arial", 14)).pack(pady=10)

        tk.Label(self.main_container, text="World Name:").pack(anchor="w")
        name_entry = tk.Entry(self.main_container)
        name_entry.pack(fill="x", pady=5)

        tk.Label(self.main_container, text="Description:").pack(anchor="w")
        desc_entry = tk.Text(self.main_container, height=5)
        desc_entry.pack(fill="x", pady=5)

        def save_new_world():
            name = name_entry.get().strip()
            desc = desc_entry.get("1.0", tk.END).strip()
            
            # Validate name is not empty
            if not name:
                messagebox.showwarning("Validation Error", "World name cannot be left blank.", parent=self.root)
                return
                
            new_id = self.db.create_world(name, desc)
            if new_id:
                messagebox.showinfo("Success", f"World '{name}' created!")
                self.show_world_selector()

        tk.Button(self.main_container, text="Save & Return", command=save_new_world).pack(pady=10)
        tk.Button(self.main_container, text="Cancel", command=self.show_world_selector).pack()

    def load_world(self):
        """Loads the selected world and moves to the Dashboard."""
        selection = self.world_list.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a world first.")
            return
        
        world_name = self.world_list.get(selection[0])
        
        # Pull matching row dictionary to extract the proper world identification key
        worlds = self.db.get_all_worlds()
        
        try:
            # Match the selected world name against our database records to find its true ID
            selected_world = next(w for w in worlds if w['world_name'] == world_name)
            self.current_world_id = selected_world['id']
        except StopIteration:
            messagebox.showerror("Error", "Could not resolve the selected world ID.")
            return
        
        self.show_dashboard()

    def show_dashboard(self):
        """The main workspace with a sidebar and content area."""
        self.clear_screen()
        
        # 1. Create a PanedWindow (Split screen)
        self.paned = tk.PanedWindow(self.main_container, orient="horizontal", sashrelief="raised")
        self.paned.pack(fill="both", expand=True)

        # 2. Left Sidebar (Navigation)
        self.sidebar = tk.Frame(self.paned, width=150, bg="#f0f0f0")
        self.paned.add(self.sidebar)

        tk.Label(self.sidebar, text="Project Explorer", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(pady=10)

        # Treeview is a Tkinter 'spreadsheet' or 'tree' widget
        self.entity_tree = ttk.Treeview(self.sidebar)
        self.entity_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Define tree structure
        self.entity_tree.heading("#0", text="Entities", anchor="w")

        self.entity_tree.bind("<<TreeviewSelect>>", self.on_entity_click)

        # 3. Right Content Area (Editor)
        self.right_container = tk.Frame(self.paned)
        self.paned.add(self.right_container)

        self.editor_canvas = tk.Canvas(self.right_container, bg="white", highlightthickness=0)
        self.editor_scrollbar = ttk.Scrollbar(self.right_container, orient="vertical", command=self.editor_canvas.yview)
        
        # This is the actual frame where our editor elements will be drawn
        self.content_area = tk.Frame(self.editor_canvas, bg="white")

        # Configure the canvas to scroll our content area frame dynamically
        self.content_area.bind(
            "<Configure>",
            lambda e: self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox("all"))
        )
        
        self.canvas_window = self.editor_canvas.create_window((0, 0), window=self.content_area, anchor="nw")
        self.editor_canvas.configure(yscrollcommand=self.editor_scrollbar.set)

        # Force the content frame width to stretch match the canvas size dynamically when resized
        self.editor_canvas.bind('<Configure>', lambda e: self.editor_canvas.itemconfig(self.canvas_window, width=e.width))

        # Pack the scroll components into position
        self.editor_scrollbar.pack(side="right", fill="y")
        self.editor_canvas.pack(side="left", fill="both", expand=True)

        self.refresh_sidebar()

        # 4. Bottom Controls
        tk.Button(self.sidebar, text="View World Timeline", command=self.display_timeline, bg="#FF9800", fg="white").pack(fill="x", side="bottom", pady=2)
        tk.Button(self.sidebar, text="Add New Entity", command=self.add_entity_popup).pack(fill="x", side="bottom")
        tk.Button(self.sidebar, text="Exit World", command=self.show_world_selector).pack(fill="x", side="bottom")

    def display_timeline(self):
        """Clears the workspace and draws a vertical chronological history timeline."""
        for widget in self.content_area.winfo_children():
            widget.destroy()

        # Canvas & Scrollbar assembly for long historical lists
        canvas = tk.Canvas(self.content_area, bg="#f9f9f9", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f9f9f9")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Header Title
        tk.Label(scrollable_frame, text="Historical Timeline Chronicles", font=("Arial", 16, "bold"), bg="#f9f9f9").pack(anchor="w", padx=20, pady=15)

        timeline_data = self.db.get_chronological_timeline(self.current_world_id)

        if not timeline_data:
            # Friendly blank-slate state if no data exists yet
            no_data_frame = tk.Frame(scrollable_frame, bg="white", relief="solid", bd=1, padx=20, pady=20)
            no_data_frame.pack(fill="x", padx=20, pady=10)
            tk.Label(no_data_frame, text="No historical events have been dated yet.", font=("Arial", 11, "italic"), bg="white", fg="gray").pack()
            tk.Label(no_data_frame, text="To add an event to the timeline, open an Event Codex entry\nand assign it a Year, Month, and Day index numerical key.", font=("Arial", 9), bg="white", fg="gray", pady=5).pack()
            return
        
        # Render sequential timeline event cards
        for index, event in enumerate(timeline_data):
            # cursor="hand2" gives immediate visual feedback that the card is a link
            card = tk.Frame(scrollable_frame, bg="white", relief="solid", bd=1, padx=15, pady=15, cursor="hand2")
            card.pack(fill="x", padx=20, pady=10)

            # Left/Top Meta Flag Row
            meta_row = tk.Frame(card, bg="white", cursor="hand2")
            meta_row.pack(fill="x")

            # Date Stamp Badge
            date_badge = tk.Label(meta_row, text=event['event_date_str'], font=("Courier", 10, "bold"), fg="#E91E63", bg="#FCE4EC", padx=6, pady=2)
            date_badge.pack(side="left")
            
            # Sub-type Badge (e.g. Event, Lore)
            type_badge = tk.Label(meta_row, text=event['entity_type'].upper(), font=("Arial", 7, "bold"), fg="gray", bg="#eee", padx=5)
            type_badge.pack(side="left", padx=10)

            # Event Title
            title_lbl = tk.Label(card, text=event['entry_name'], font=("Arial", 13, "bold"), bg="white", anchor="w", cursor="hand2")
            title_lbl.pack(fill="x", pady=(8, 4))

            # Description snippet summary
            snippet = event['entry_content'] if event['entry_content'] else "No description provided yet."
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
                
            desc_lbl = tk.Label(card, text=snippet, font=("Arial", 9), fg="#555", bg="white", wrap=500, justify="left", anchor="w", cursor="hand2")
            desc_lbl.pack(fill="x")

            # >> The Context Navigation Routing Engine <<
            # Captures the exact parameters of the specific event entry row
            e_name = event['entry_name']
            e_type = event['entity_type']

            # This inline function intercepts the click event and safely requests details 
            # from the database before triggering the editor display re-render.
            def make_navigation_callback(target_name, target_type):
                return lambda click_event: self.route_timeline_click_to_editor(target_name, target_type)

            callback = make_navigation_callback(e_name, e_type)

            # Binds the click callback function to the frame and all internal text elements.
            card.bind("<Button-1>", callback)
            meta_row.bind("<Button-1>", callback)
            title_lbl.bind("<Button-1>", callback)
            desc_lbl.bind("<Button-1>", callback)

    def route_timeline_click_to_editor(self, entity_name, entity_type):
        """Fetches full data details and instantly redirects the workspace view to the Editor."""
        entity_data = self.db.get_entity_details(self.current_world_id, entity_name, entity_type)
        if entity_data:
            self.display_entity_editor(entity_data, entity_type)

    def refresh_sidebar(self):
        """Fetches data from the DB and fills the sidebar."""
        # Clear existing items
        for item in self.entity_tree.get_children():
            self.entity_tree.delete(item)

        # Fetch using your backend method
        data = self.db.get_world_entities(self.current_world_id)

        # Create Folders
        for category, items in data.items():
            parent = self.entity_tree.insert("", "end", text=category, open=True)
            for entity in items:
                # Use the name of the entity for display
                display_name = entity[1] 
                self.entity_tree.insert(parent, "end", text=display_name)

    def add_entity_popup(self):
        """Opens a small modal popup window to add a new entity."""
        # 1. Create a top-level window overlay
        popup = tk.Toplevel(self.root)
        popup.title("Add New Entity")
        popup.geometry("300x250")

        # Make the popup 'modal' (blocks interaction with the main window until closed)
        popup.transient(self.root)
        popup.grab_set()

        # 2. Add input fields
        tk.Label(popup, text="Entity Name:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        name_entry = tk.Entry(popup)
        name_entry.pack(fill="x", padx=10, pady=5)

        tk.Label(popup, text="Entity Type:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)

        # Combobox is ttk's version of a dropdown menu
        type_dropdown = ttk.Combobox(popup, values=[
            "Character", "Location", "Event", "Item", "System", "Lore"
        ], state="readonly") # state="readonly" prevents typing custom text into the dropdown
        type_dropdown.set("Character") # Default selection
        type_dropdown.pack(fill="x", padx=10, pady=5)

        # 3. Action function when 'Save' is clicked
        def save_entity():
            name = name_entry.get().strip()
            entity_type = type_dropdown.get()

            # Prevent empty entity creation
            if not name:
                messagebox.showwarning("Validation Error", "Entity name cannot be left blank.", parent=popup)
                return
            
            # Fire backend engine
            new_id = self.db.get_or_create_ghost(self.current_world_id, entity_type, name)

            if new_id:
                messagebox.showinfo("Success", f"Created {entity_type}: '{name}'", parent=popup)
                self.refresh_sidebar() # Update Treeview sidebar immediately
                popup.destroy() # Close the popup window
            else:
                messagebox.showerror("Error", "Could not create entity.", parent=popup)
            
        # 4. Save Button
        tk.Button(popup, text="Save Entity", command=save_entity, bg="#4CAF50", fg="white").pack(padx=10, pady=15, fill="x")

    def on_entity_click(self, event):
        """Triggers automatically when a user selects a sidebar item."""
        selected_item = self.entity_tree.selection()
        if not selected_item:
            return
            
        # Get visual text of the clicked item
        item_text = self.entity_tree.item(selected_item[0], "text")

        # Determine parent category folder ('Characters', 'Locations', or 'Codex')
        parent_id = self.entity_tree.parent(selected_item[0])

        # If folder root itself is clicked, nothing happens
        if not parent_id:
            return
            
        category = self.entity_tree.item(parent_id, "text")

        # Map visual folders back to single entity types for our database backend
        type_mapping = {
            'Characters': 'Character',
            'Locations': 'Location',
            'Codex': 'CodexEntry' # Backend code will infer exact sub-type
        }

        # If it's a Codex sub-item, we can dynamically look up its true type
        entity_type = type_mapping[category]
        if entity_type == 'CodexEntry':
            # Temporary fallback to inspect table schemas dynamically
            results = self.db.global_search(self.current_world_id, item_text)
            if results:
                entity_type = results[0]['type']

        # Fetch details using our new backend method
        entity_data = self.db.get_entity_details(self.current_world_id, item_text, entity_type)
        if entity_data:
            self.display_entity_editor(entity_data, entity_type)

    def display_entity_editor(self, data, entity_type):
        """Renders the comprehensive workspace profile editor for a chosen entity."""
        # 1. Canvas Reset Clear
        for widget in self.content_area.winfo_children():
            widget.destroy()

        # 2. Variable Schema Extraction Mappings
        if entity_type in ['Character', 'Location']:
            entity_name = data['char_name'] if entity_type == 'Character' else data['location_name']
            desc_field = 'biography' if entity_type == 'Character' else 'location_desc'
            status_field = 'char_status' if entity_type == 'Character' else 'location_status'
        else:
            entity_name = data['entry_name']
            desc_field = 'entry_content'
            status_field = 'entry_status'
            
        # 3. Header Display Assembly
        header_frame = tk.Frame(self.content_area, bg="white")
        header_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(header_frame, text=entity_name, font=("Arial", 16, "bold"), bg="white").pack(side="left")
        
        status_colors = {'Ghost': ('#FF9800', '#FFF3E0'), 'Canon': ('#4CAF50', '#E8F5E9')}
        s_color, b_color = status_colors.get(data[status_field], ('#757575', '#F5F5F5'))
        
        tk.Label(header_frame, text=f" {data[status_field].upper()} ", font=("Arial", 9, "bold"), fg=s_color, bg=b_color, padx=6).pack(side="left", padx=10)
        tk.Label(header_frame, text=entity_type.upper(), font=("Arial", 9, "bold"), fg="gray", bg="#eee", padx=5).pack(side="right")

        # 4. Core Text Description Area
        tk.Label(self.content_area, text="Description / Details:", font=("Arial", 10, "bold"), bg="white").pack(anchor="w", padx=15, pady=(10, 2))
        text_editor = tk.Text(self.content_area, height=10, wrap="word", relief="solid", bd=1)
        text_editor.pack(fill="x", padx=15, pady=5)
        if data[desc_field]:
            text_editor.insert("1.0", data[desc_field])

        # 5. Temporal / Date Inputs (ONLY rendered for Codex/Timeline entries)
        if entity_type not in ['Character', 'Location']:
            date_frame = tk.LabelFrame(self.content_area, text=" Timeline Integration (Chronology) ", bg="white", padx=10, pady=10)
            date_frame.pack(fill="x", padx=15, pady=10)

            tk.Label(date_frame, text="Year:", bg="white").grid(row=0, column=0, sticky="w", padx=5)
            year_entry = tk.Entry(date_frame, width=8)
            year_entry.grid(row=1, column=0, padx=5, pady=5)
            # FIXED: Read index values safely using standard row key checks
            if 'event_year' in data.keys() and data['event_year'] is not None:
                year_entry.insert(0, str(data['event_year']))

            tk.Label(date_frame, text="Month Name:", bg="white").grid(row=0, column=1, sticky="w", padx=5)
            db_months = self.db.get_world_months(self.current_world_id)
            
            month_options = []
            month_num_to_name = {}
            month_name_to_num = {}
            for m_row in db_months:
                display_str = f"{m_row['sequence_order']} - {m_row['month_name']}"
                month_options.append(display_str)
                month_num_to_name[m_row['sequence_order']] = display_str
                month_name_to_num[display_str] = m_row['sequence_order']

            month_dropdown = ttk.Combobox(date_frame, values=month_options, state="readonly", width=18)
            month_dropdown.grid(row=1, column=1, padx=5, pady=5)
            
            # FIXED: Safe check for existing event month number
            if 'event_month' in data.keys() and data['event_month'] in month_num_to_name:
                month_dropdown.set(month_num_to_name[data['event_month']])
            elif month_options:
                month_dropdown.set(month_options[0])

            tk.Label(date_frame, text="Day:", bg="white").grid(row=0, column=2, sticky="w", padx=5)
            day_entry = tk.Entry(date_frame, width=8)
            day_entry.grid(row=1, column=2, padx=5, pady=5)
            # FIXED: Safe check for existing event day
            if 'event_day' in data.keys() and data['event_day'] is not None:
                day_entry.insert(0, str(data['event_day']))

            tk.Label(date_frame, text="Current Timestamp:", bg="white").grid(row=0, column=3, sticky="w", padx=15)
            # FIXED: Safe check for the human-readable date string stamp
            date_label_str = data['event_date_str'] if ('event_date_str' in data.keys() and data['event_date_str']) else "[No Date Assigned]"
            tk.Label(date_frame, text=date_label_str, font=("Courier", 10, "bold"), fg="#E91E63", bg="#FCE4EC", padx=5).grid(row=1, column=3, sticky="w", padx=15)
        
        # 6. Graph Relationship Linker Module (Rendered for ALL entity types)
        link_frame = tk.LabelFrame(self.content_area, text=" Relationship Graph Linker ", bg="white", padx=10, pady=10)
        link_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(link_frame, text="Connection Type:", bg="white").grid(row=0, column=0, sticky="w", padx=5)
        conn_entry = tk.Entry(link_frame, width=20)
        conn_entry.grid(row=1, column=0, padx=5, pady=5)
        
        tk.Label(link_frame, text="Target Entity:", bg="white").grid(row=0, column=1, sticky="w", padx=5)
        
        # Pull clean string array lists safely
        all_targets = self.db.get_all_entities_for_linking(self.current_world_id, entity_name)
        
        target_dropdown = ttk.Combobox(link_frame, values=all_targets, state="readonly", width=30)
        target_dropdown.grid(row=1, column=1, padx=5, pady=5)
        if all_targets:
            target_dropdown.set(all_targets[0])

        def execute_link():
            conn_type = conn_entry.get().strip()
            target_str = target_dropdown.get()
            if not conn_type or not target_str:
                messagebox.showwarning("Validation Error", "Connection type and target are required.", parent=self.root)
                return
            
            try:
                # Safely parse back out the entity parameters
                t_name = target_str.split(" (")[0]
                t_type = target_str.split(" (")[1].replace(")", "")
                
                source_type_string = 'Character' if entity_type == 'Character' else ('Location' if entity_type == 'Location' else 'CodexEntry')
                target_type_string = 'Character' if t_type == 'Character' else ('Location' if t_type == 'Location' else 'CodexEntry')
                
                success_link = self.db.create_relationship(self.current_world_id, entity_name, source_type_string, t_name, target_type_string, conn_type)
                if success_link:
                    messagebox.showinfo("Success", f"Linked '{entity_name}' to '{t_name}' as {conn_type}!", parent=self.root)
                    conn_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Linking Error", f"Could not process relationship link mapping: {str(e)}", parent=self.root)

        tk.Button(link_frame, text="Link Entities", command=execute_link, bg="#9C27B0", fg="white", font=("Arial", 9, "bold")).grid(row=1, column=2, padx=10, pady=5)

        # Real-time Verification Box: Displays active database graph links
        tk.Label(link_frame, text="Active Connections:", font=("Arial", 9, "bold"), bg="white").grid(row=2, column=0, sticky="w", padx=5, pady=(10,0))
        
        # Translate entity types to match database relationship schema
        source_type_db = 'Character' if entity_type == 'Character' else ('Location' if entity_type == 'Location' else 'CodexEntry')
        active_links = self.db.get_entity_relationships(self.current_world_id, entity_name, source_type_db)
        
        links_display_frame = tk.Frame(link_frame, bg="#F5F5F5", relief="sunken", bd=1)
        links_display_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        if not active_links:
            tk.Label(links_display_frame, text="No active relationships established yet.", fg="gray", bg="#F5F5F5", font=("Arial", 9, "italic")).pack(anchor="w", padx=5, pady=2)
        else:
            for link in active_links:
                # Format: " -> Involved Character: Kaelen" or " <- Origin Event: The Shattering"
                direction = "->" if link['source_name'] == entity_name else "<-"
                display_text = f" {direction} {link['connection_type']}: {link['target_name'] if link['source_name'] == entity_name else link['source_name']}"
                tk.Label(links_display_frame, text=display_text, bg="#F5F5F5", font=("Courier", 9)).pack(anchor="w", padx=5)

        # 7. Core Application Save Logic Engine
        def save_changes():
            updated_text = text_editor.get("1.0", tk.END).strip()
            current_status = data[status_field]
            new_status = 'Canon' if current_status == 'Ghost' and updated_text else current_status

            success = self.db.update_entity_details(
                self.current_world_id, entity_name, entity_type, updated_text, new_status
            )
            
            if success and entity_type not in ['Character', 'Location']:
                try:
                    y_str = year_entry.get().strip()
                    d_str = day_entry.get().strip()
                    chosen_month_str = month_dropdown.get()

                    if not y_str and not d_str and not chosen_month_str:
                        y, m, d, date_str, chron_idx = None, None, None, None, None
                    else:
                        if not y_str or not d_str:
                            raise ValueError("Both Year and Day are required to calculate a timeline date.")
                        y = int(y_str)
                        d = int(d_str)
                        if y < 0 or d <= 0:
                            raise ValueError("Dates must be positive metrics.")
                            
                        m = month_name_to_num[chosen_month_str]
                        clean_month_name = chosen_month_str.split(" - ")[1]
                        date_str = f"Year {y}, {clean_month_name}, Day {d}"
                        chron_idx = self.db.calculate_chronological_index(self.current_world_id, y, m, d)

                    query = """
                    UPDATE codex_entries 
                    SET event_year = ?, event_month = ?, event_day = ?, event_date_str = ?, chronological_index = ?
                    WHERE world_id = ? AND entry_name = ?
                    """
                    with self.db.get_connection() as conn:
                        conn.execute(query, (y, m, d, date_str, chron_idx, self.current_world_id, entity_name))
                except ValueError:
                    messagebox.showerror("Validation Error", "Please ensure Year and Day are valid positive whole numbers.")
                    return

            if success:
                messagebox.showinfo("Saved", f"Changes to '{entity_name}' saved successfully!")
                if new_status != current_status:
                    self.refresh_sidebar()
                fresh_data = self.db.get_entity_details(self.current_world_id, entity_name, entity_type)
                if fresh_data:
                    self.display_entity_editor(fresh_data, entity_type)

        def trigger_destructive_purge():
            if messagebox.askyesno("Confirm Deletion", f"Permanently delete '{entity_name}'?"):
                if self.db.delete_entity(self.current_world_id, entity_name, entity_type):
                    messagebox.showinfo("Deleted", "Entity removed.")
                    self.refresh_sidebar()
                    for widget in self.content_area.winfo_children():
                        widget.destroy()

        # 8. Bottom Universal Action Buttons Panel (Sits completely outside of ALL conditionals)
        control_frame = tk.Frame(self.content_area, bg="white")
        control_frame.pack(fill="x", padx=15, pady=15)
        
        tk.Button(control_frame, text="Delete Entity", command=trigger_destructive_purge, bg="#F44336", fg="white", font=("Arial", 10, "bold")).pack(side="left")
        tk.Button(control_frame, text="Save Changes", command=save_changes, bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side="right")
        
if __name__ == "__main__":
    root = tk.Tk()
    app = StorySchemaApp(root)
    root.mainloop()

