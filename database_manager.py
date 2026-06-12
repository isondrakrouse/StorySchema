# StorySchema v1.0.4 Database Manager
# Copyright © 2026 Isondra Krouse. All rights reserved.

import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="story_schema.db"):
        self.db_path = db_path

        # A\N: Added dynamic schema path handling
        # Prevents failures when schema.sql is not in the working directory.
        self.schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

        # Initialize the database if it doesn't exist
        self.initialize_db()

    def get_connection(self):
        """Returns a connection with Foreign Key support enabled."""
        conn = sqlite3.connect(self.db_path)

        # Supports referential integrity as defined in schema.sql
        conn.execute("PRAGMA foreign_keys = ON;")

        # Allows accessing columns by name
        conn.row_factory = sqlite3.Row

        return conn

    def initialize_db(self):
        """Initialize schema if required tables do not exist."""

        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                AND name='worlds'
            """)

            result = cursor.fetchone()

            if result is None:

                # A\N: Now uses self.schema_path instead of hardcoded filename
                if os.path.exists(self.schema_path):

                    with open(self.schema_path, "r", encoding="utf-8") as f:
                        schema_script = f.read()

                    conn.executescript(schema_script)

                    print("Database initialized successfully.")

                else:
                    print("Error: schema.sql not found.")

    # >> World Management Tools <<

    def create_world(self, name, description):
        """Creates a brand new world record and immediately seeds its custom calendar framework."""
        query = "INSERT INTO worlds (world_name, world_desc) VALUES (?, ?)"
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (name, description))
                new_world_id = cursor.lastrowid
                
                # >> LINK THE SEEDER HERE TO BIND THE MONTHS <<
                self.seed_default_months(conn, new_world_id)
                
                conn.commit()
                return new_world_id
        except Exception as e:
            print(f"Database Error in create_world: {e}")
            return None
        
    # >> Ghost Note / Entity Workflow <<

    def get_or_create_ghost(self, world_id, entity_type, entity_name):
        """
        Universal Ghost Entity creator.
        Supports: 'Character', 'Location', 'Event', 'Item', 'System', 'Lore'
        """
        # Mapping for routing to correct table and columns (v1.1 schema)
        table_map = {
            'Character': ('characters', 'char_name', 'char_status'),
            'Location': ('locations', 'location_name', 'location_status'),
            'Event': ('codex_entries', 'entry_name', 'entry_status'),
            'Item': ('codex_entries', 'entry_name', 'entry_status'),
            'System': ('codex_entries', 'entry_name', 'entry_status'),
            'Lore': ('codex_entries', 'entry_name', 'entry_status')
        }

        # A/N: Added safer validation
        if entity_type not in table_map:
            raise ValueError(f"Unsupported entity type: {entity_type}")
        
        table, name_col, status_col = table_map[entity_type]

        # 1. Search for existing entity (to prevent duplicate ghost entities)
        search_query = f"SELECT id FROM {table} WHERE world_id = ? AND {name_col} = ?"

        with self.get_connection() as conn:
            cursor = conn.execute(search_query, (world_id, entity_name))
            result = cursor.fetchone()

            if result:
                return result['id']

            # 2. Insert as 'Ghost' if no match is found
            # Handle the specific 'entity_type' column requirement for codex_entries
            if table == 'codex_entries':
                insert_query = f"""
                INSERT INTO codex_entries (world_id, entity_type, entry_name, entry_status)
                VALUES (?, ?, ?, 'Ghost')
                """
                params = (world_id, entity_type, entity_name)
            else:
                insert_query = f"""
                INSERT INTO {table} (world_id, {name_col}, {status_col})
                VALUES (?, ?, 'Ghost')
                """
                params = (world_id, entity_name)

            try:
                new_cursor = conn.execute(insert_query, params)
                print(f"Ghost {entity_type} '{entity_name}' created.")
                return new_cursor.lastrowid
            except sqlite3.IntegrityError as e:
                print(f"Database Error during ghost creation: {e}")
                return None
            
    # >> Relationship Management <<

    def create_link(self, world_id, source_id, source_type, target_id, target_type, connection_type):
        """
        Creates a directed relationship between two entites.
        Validates that both entites exist before linking.
        """
        # 1. Validation Logic: Ensure both sides of the link exist
        if not self._entity_exists(world_id, source_id, source_type):
            print(f"Link Error: Source {source_type} (ID: {source_id}) not found.")
            return None

        if not self._entity_exists(world_id, target_id, target_type):
            print(f"Link Error: Target {target_type} (ID: {target_id}) not found.")
            return None
        
        # 2. Insert the Link
        query = """
        INSERT INTO entity_links (world_id, source_id, source_type, target_id, target_type, connection_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (world_id, source_id, source_type, target_id, target_type, connection_type))
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Handles UNIQUE constraint preventing duplicate identical links
            print("Link Error: This specific relationship already exists.")
            return None
        
    def _entity_exists(self, world_id, entity_id, entity_type):
        """Internal helper to verify an entity exists in its respective table."""
        table_map = {
            'Character': 'characters',
            'Location': 'locations',
            'CodexEntry': 'codex_entries'
        }
        table = table_map.get(entity_type)
        if not table:
            return False

        query = f"SELECT 1 FROM {table} WHERE id = ? AND world_id = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (entity_id, world_id))
            return cursor.fetchone() is not None

    # >> Calendar & Temporal Logic <<

    def get_calendar_definition(self, world_id):
        """Retrieves the full calendar rules and month lengths for a world."""
        query = """
        SELECT c.leap_year_interval, m.month_name, m.month_order, m.day_count, m.leap_day_count
        FROM calendars c
        JOIN calendar_months m ON c.id = m.calendar_id
        WHERE c.world_id = ?
        ORDER BY m.month_order ASC
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (world_id,))
            return cursor.fetchall()
        
    def calculate_chronological_index(self, world_id, year, month_order, day):
        """
        Converts a custom date into a single sortable integer.
        Formula: (Days in prior years) + (Days in prior months of current year) + (Current Day)
        """
        months = self.get_calendar_definition(world_id)
        if not months:
            return None # No calendar defined for this world
        
        leap_interval = months[0]['leap_year_interval']
        days_in_normal_year = sum(m['day_count'] for m in months)
        days_added_in_leap_year = sum(m['leap_day_count'] for m in months)

        # 1. Calculate days from completed years
        # We assume Year 0 as start
        total_days = year * days_in_normal_year

        # Add leap year extra days for all elapsed leap years
        if leap_interval > 0:
            num_leap_years = year // leap_interval
            total_days = (num_leap_years * days_added_in_leap_year) + total_days

        # 2. Add days from completed months in the current year
        is_leap_year = (leap_interval > 0 and year % leap_interval == 0)

        for m in months:
            if m['month_order'] < month_order:
                total_days = m['day_count'] + total_days
                if is_leap_year:
                    total_days = m['leap_day_count'] + total_days

        # 3. Add current days
        total_days = day + total_days
        return total_days
    
    def update_entry_chronology(self, entry_id, year, month_order, day):
        """Calculates and saves the chronological index for a Codex Entry."""
        # First, find the world_id for this entry
        with self.get_connection() as conn:
            world_row = conn.execute("SELECT world_id FROM codex_entries WHERE id = ?", (entry_id,)).fetchone()
            if not world_row:
                return False
            
            world_id = world_row['world_id']
            index = self.calculate_chronological_index(world_id, year, month_order, day)

            if index is not None:
                conn.execute("""
                    UPDATE codex_entries
                    SET chronological_index = ?, event_date_str = ?
                    WHERE id = ?
                """, (index, f"Year {year}, Month {month_order}, Day {day}", entry_id))
                return True
        return False
    
    # >> Data Retrieval & UI Support <<
    def get_all_worlds(self):
        """Fetches all worlds for the selection screen."""
        query = "SELECT id, world_name, world_desc FROM worlds ORDER BY world_name ASC"
        with self.get_connection() as conn:
            return conn.execute(query).fetchall()
        
    def get_world_entities(self, world_id):
        """
        Fetches all primary entities in a world.
        Useful for populating sidebars and selection lists.
        """
        entities = {
            'Characters': [],
            'Locations': [],
            'Codex': []
        }

        with self.get_connection() as conn:
            # Fetch Characters
            entities['Characters'] = conn.execute(
                "SELECT id, char_name, char_status FROM characters WHERE world_id = ?",
                (world_id,)
            ).fetchall()

            # Fetch Locations
            entities['Locations'] = conn.execute(
                "SELECT id, location_name, location_status FROM locations WHERE world_id = ?",
                (world_id,)
            ).fetchall()

            # Fetch Codex (Events, Items, etc.)
            entities['Codex'] = conn.execute(
                "SELECT id, entry_name, entity_type, entry_status FROM codex_entries WHERE world_id = ?",
                (world_id,)
            ).fetchall()

        return entities
    
    def global_search(self, world_id, search_term):
        """
        Cross-table search to find entities by name.
        Essential for the 'Disambiguation' workflow.
        """
        results = []
        term = f"%{search_term}%"

        with self.get_connection() as conn:
            # Search Characters
            chars = conn.execute(
                "SELECT id, char_name as name, 'Character' as type FROM characters WHERE world_id = ? AND char_name LIKE ?",
                (world_id, term)
            ).fetchall()
            results.extend(chars)

            # Search Locations
            locs = conn.execute(
                "SELECT id, location_name as name, 'Location' as type FROM locations WHERE world_id = ? AND location_name LIKE ?",
                (world_id, term)
            ).fetchall()
            results.extend(locs)

            # Search Codex
            codex = conn.execute(
                "SELECT id, entry_name as name, entity_type as type FROM codex_entries WHERE world_id = ? AND entry_name LIKE ?",
                (world_id, term)
            ).fetchall()
            results.extend(codex)

        return results
    
    def get_entity_details(self, world_id, entity_name, entity_type):
        """Fetches the complete database row for a specific named entity."""
        table_map = {
            'Character': ('characters', 'char_name'),
            'Location': ('locations', 'location_name'),
            'Event': ('codex_entries', 'entry_name'),
            'Item': ('codex_entries', 'entry_name'),
            'System': ('codex_entries', 'entry_name'),
            'Lore': ('codex_entries', 'entry_name')
        }
    
        table, name_col = table_map[entity_type]
        query = f"SELECT * FROM {table} WHERE world_id = ? AND {name_col} = ?"

        with self.get_connection() as conn:
            return conn.execute(query, (world_id, entity_name)).fetchone()
        
    def update_entity_details(self, world_id, entity_name, entity_type, new_content, new_status='Canon'):
        """Updates the content/biography and promotes the status of an entity."""
        table_map = {
            'Character': ('characters', 'biography', 'char_name', 'char_status'),
            'Location': ('locations', 'location_desc', 'location_name', 'location_status'),
            'Event': ('codex_entries', 'entry_content', 'entry_name', 'entry_status'),
            'Item': ('codex_entries', 'entry_content', 'entry_name', 'entry_status'),
            'System': ('codex_entries', 'entry_content', 'entry_name', 'entry_status'),
            'Lore': ('codex_entries', 'entry_content', 'entry_name', 'entry_status')
        }
    
        table, content_col, name_col, status_col = table_map[entity_type]

        query = f"""
        UPDATE {table}
        SET {content_col} = ?, {status_col} = ?
        WHERE world_id = ? AND {name_col} = ?
        """

        with self.get_connection() as conn:
            conn.execute(query, (new_content, new_status, world_id, entity_name))
            return True
        
    def get_chronological_timeline(self, world_id):
        """Fetches all dated codex entries ordered chronologically."""
        query = """
        SELECT id, entry_name, entity_type, event_date_str, entry_content, entry_status
        FROM codex_entries
        WHERE world_id = ? AND chronological_index IS NOT NULL
        ORDER BY chronological_index ASC
        """
        with self.get_connection() as conn:
            return conn.execute(query, (world_id,)).fetchall()
    
    def get_world_months(self, world_id):
        """Fetches months for the dropdown by joining the true calendar tables."""
        query = """
        SELECT cm.month_name, cm.month_order AS sequence_order
        FROM calendar_months cm
        JOIN calendars c ON cm.calendar_id = c.id
        WHERE c.world_id = ?
        ORDER BY cm.month_order ASC
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (world_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Database Error in get_world_months: {e}")
            return []
        
    def delete_entity(self, world_id, entity_name, entity_type):
        """Safely removes an entity and cascades to clean up all associated relationship links."""
        table_map = {
            'Character': ('characters', 'char_name', 'Character'),
            'Location': ('locations', 'location_name', 'Location'),
            'Event': ('codex_entries', 'entry_name', 'CodexEntry'),
            'Item': ('codex_entries', 'entry_name', 'CodexEntry'),
            'System': ('codex_entries', 'entry_name', 'CodexEntry'),
            'Lore': ('codex_entries', 'entry_name', 'CodexEntry')
        }
        
        table, name_col, link_type_string = table_map[entity_type]
        
        with self.get_connection() as conn:
            # 1. First, fetch the actual unique internal integer ID of the entity
            query_id = f"SELECT id FROM {table} WHERE world_id = ? AND {name_col} = ?"
            row = conn.execute(query_id, (world_id, entity_name)).fetchone()
            
            if not row:
                return False
                
            entity_id = row['id']
            
            # 2. CASCADE CLEANUP: Delete all graph connection wires where this asset is either the source OR the target
            conn.execute("""
                DELETE FROM entity_links 
                WHERE world_id = ? 
                AND ((source_id = ? AND source_type = ?) OR (target_id = ? AND target_type = ?))
            """, (world_id, entity_id, link_type_string, entity_id, link_type_string))
            
            # 3. CORE PURGE: Delete the primary record row asset itself
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (entity_id,))
            return True
        
    def update_entity_details(self, world_id, entity_name, entity_type, text_content, status):
        """Routes application text and status saves dynamically to the correct database schema."""
        try:
            with self.get_connection() as conn:
                if entity_type == 'Character':
                    query = "UPDATE characters SET biography = ?, char_status = ? WHERE world_id = ? AND char_name = ?"
                elif entity_type == 'Location':
                    query = "UPDATE locations SET location_desc = ?, location_status = ? WHERE world_id = ? AND location_name = ?"
                else:
                    query = "UPDATE codex_entries SET entry_content = ?, entry_status = ? WHERE world_id = ? AND entry_name = ?"
                
                conn.execute(query, (text_content, status, world_id, entity_name))
                conn.commit()
                return True
        except Exception as e:
            print(f"Database Error in update_entity_details: {e}")
            return False
        
    def get_entity_details(self, world_id, entity_name, entity_type):
        """Fetches a single cohesive database row regardless of entity type mapping."""
        try:
            with self.get_connection() as conn:
                if entity_type == 'Character':
                    query = "SELECT * FROM characters WHERE world_id = ? AND char_name = ?"
                elif entity_type == 'Location':
                    query = "SELECT * FROM locations WHERE world_id = ? AND location_name = ?"
                else:
                    query = "SELECT * FROM codex_entries WHERE world_id = ? AND entry_name = ?"
                
                cursor = conn.execute(query, (world_id, entity_name))
                return cursor.fetchone()
        except Exception as e:
            print(f"Database Error in get_entity_details: {e}")
            return None
        
    def get_all_entities_for_linking(self, world_id, exclude_name):
        """Fetches every entity name in the world except the current one, formatted for a dropdown menu."""
        query = """
        SELECT char_name AS name, 'Character' AS type FROM characters WHERE world_id = ? AND char_name != ?
        UNION ALL
        SELECT location_name AS name, 'Location' AS type FROM locations WHERE world_id = ? AND location_name != ?
        UNION ALL
        SELECT entry_name AS name, entity_type AS type FROM codex_entries WHERE world_id = ? AND entry_name != ?
        """
        target_list = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (world_id, exclude_name, world_id, exclude_name, world_id, exclude_name))
                for row in cursor.fetchall():
                    target_list.append(f"{row['name']} ({row['type']})")
        except Exception as e:
            print(f"Database Error in get_all_entities_for_linking: {e}")
        return target_list

    def create_relationship(self, world_id, source_name, source_type, target_name, target_type, connection_type):
        """Creates an entry in entity_links by translating names to entity IDs dynamically."""
        try:
            with self.get_connection() as conn:
                # 1. Resolve Source ID
                if source_type == 'Character':
                    s_res = conn.execute("SELECT id FROM characters WHERE world_id = ? AND char_name = ?", (world_id, source_name)).fetchone()
                elif source_type == 'Location':
                    s_res = conn.execute("SELECT id FROM locations WHERE world_id = ? AND location_name = ?", (world_id, source_name)).fetchone()
                else:
                    s_res = conn.execute("SELECT id FROM codex_entries WHERE world_id = ? AND entry_name = ?", (world_id, source_name)).fetchone()
                
                # 2. Resolve Target ID
                if target_type == 'Character':
                    t_res = conn.execute("SELECT id FROM characters WHERE world_id = ? AND char_name = ?", (world_id, target_name)).fetchone()
                elif target_type == 'Location':
                    t_res = conn.execute("SELECT id FROM locations WHERE world_id = ? AND location_name = ?", (world_id, target_name)).fetchone()
                else:
                    t_res = conn.execute("SELECT id FROM codex_entries WHERE world_id = ? AND entry_name = ?", (world_id, target_name)).fetchone()

                if not s_res or not t_res:
                    return False

                # 3. Insert into the correct entity_links table schema
                conn.execute("""
                    INSERT INTO entity_links (world_id, source_id, source_type, target_id, target_type, connection_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (world_id, s_res['id'], source_type, t_res['id'], target_type, connection_type))
                conn.commit()
                return True
        except Exception as e:
            print(f"Database Error in create_relationship: {e}")
            return False

    def get_entity_relationships(self, world_id, entity_name, entity_type):
        """Fetches active relationships and resolves foreign IDs back to names for UI display."""
        relationships = []
        try:
            with self.get_connection() as conn:
                # Find current entity ID
                if entity_type == 'Character':
                    curr = conn.execute("SELECT id FROM characters WHERE world_id = ? AND char_name = ?", (world_id, entity_name)).fetchone()
                elif entity_type == 'Location':
                    curr = conn.execute("SELECT id FROM locations WHERE world_id = ? AND location_name = ?", (world_id, entity_name)).fetchone()
                else:
                    curr = conn.execute("SELECT id FROM codex_entries WHERE world_id = ? AND entry_name = ?", (world_id, entity_name)).fetchone()

                if not curr:
                    return []
                curr_id = curr['id']

                # Select all links involving this entity ID and type
                links = conn.execute("""
                    SELECT * FROM entity_links 
                    WHERE world_id = ? AND ((source_id = ? AND source_type = ?) OR (target_id = ? AND target_type = ?))
                """, (world_id, curr_id, entity_type, curr_id, entity_type)).fetchall()

                for link in links:
                    # Resolve names based on whether the current item is the source or the target
                    is_source = (link['source_id'] == curr_id and link['source_type'] == entity_type)
                    t_id = link['target_id'] if is_source else link['source_id']
                    t_type = link['target_type'] if is_source else link['source_type']

                    if t_type == 'Character':
                        name_row = conn.execute("SELECT char_name AS name FROM characters WHERE id = ?", (t_id,)).fetchone()
                    elif t_type == 'Location':
                        name_row = conn.execute("SELECT location_name AS name FROM locations WHERE id = ?", (t_id,)).fetchone()
                    else:
                        name_row = conn.execute("SELECT entry_name AS name FROM codex_entries WHERE id = ?", (t_id,)).fetchone()

                    if name_row:
                        relationships.append({
                            'source_name': entity_name if is_source else name_row['name'],
                            'target_name': name_row['name'] if is_source else entity_name,
                            'connection_type': link['connection_type']
                        })
        except Exception as e:
            print(f"Database Error in get_entity_relationships: {e}")
        return relationships

    def seed_default_months(self, conn, world_id):
        """Seeds standard custom calendar months using your true calendar database schema structure."""
        cursor = conn.execute("INSERT INTO calendars (world_id, calendar_name) VALUES (?, 'Standard')", (world_id,))
        calendar_id = cursor.lastrowid
        default_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

        for index, name in enumerate(default_months):
            conn.execute("""
 month_name, month_order, day_count)                 INSERT INTO calendar_months (calendar_id,
                VALUES (?, ?, ?, 30)
            """, (calendar_id, name, index + 1))

    def get_world_months(self, world_id):
        """Fetches structured months for the dropdown by joining your calendar schemas."""
        query = """
        SELECT cm.month_name, cm.month_order AS sequence_order
        FROM calendar_months cm
        JOIN calendars c ON cm.calendar_id = c.id
        WHERE c.world_id = ?
        ORDER BY cm.month_order ASC
        """
        try:
            with self.get_connection() as conn:
                return conn.execute(query, (world_id,)).fetchall()
        except Exception as e:
            print(f"Database Error in get_world_months: {e}")
            return []

    def get_entity_details(self, world_id, entity_name, entity_type):
        """Fetches a single cohesive database row regardless of polymorphic entity type mapping."""
        try:
            with self.get_connection() as conn:
                if entity_type == 'Character':
                    return conn.execute("SELECT * FROM characters WHERE world_id = ? AND char_name = ?", (world_id, entity_name)).fetchone()
                elif entity_type == 'Location':
                    return conn.execute("SELECT * FROM locations WHERE world_id = ? AND location_name = ?", (world_id, entity_name)).fetchone()
                else:
                    return conn.execute("SELECT * FROM codex_entries WHERE world_id = ? AND entry_name = ?", (world_id, entity_name)).fetchone()
        except Exception as e:
            print(f"Database Error in get_entity_details: {e}")
            return None

    def update_entity_details(self, world_id, entity_name, entity_type, text_content, status):
        """Routes application text and status updates dynamically to the matching database schema layout."""
        try:
            with self.get_connection() as conn:
                if entity_type == 'Character':
                    conn.execute("UPDATE characters SET biography = ?, char_status = ? WHERE world_id = ? AND char_name = ?", (text_content, status, world_id, entity_name))
                elif entity_type == 'Location':
                    conn.execute("UPDATE locations SET location_desc = ?, location_status = ? WHERE world_id = ? AND location_name = ?", (text_content, status, world_id, entity_name))
                else:
                    conn.execute("UPDATE codex_entries SET entry_content = ?, entry_status = ? WHERE world_id = ? AND entry_name = ?", (text_content, status, world_id, entity_name))
                conn.commit()
                return True
        except Exception as e:
            print(f"Database Error in update_entity_details: {e}")
            return False

    def delete_entity(self, world_id, entity_name, entity_type):
        """Deletes an entity from its respective table."""
        try:
            with self.get_connection() as conn:
                if entity_type == 'Character':
                    conn.execute("DELETE FROM characters WHERE world_id = ? AND char_name = ?", (world_id, entity_name))
                elif entity_type == 'Location':
                    conn.execute("DELETE FROM locations WHERE world_id = ? AND location_name = ?", (world_id, entity_name))
                else:
                    conn.execute("DELETE FROM codex_entries WHERE world_id = ? AND entry_name = ?", (world_id, entity_name))
                conn.commit()
                return True
        except Exception as e:
            print(f"Database Error in delete_entity: {e}")
            return False
        