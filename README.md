# StorySchema (v1.1)
### *A Relational Workspace Engine for Worldbuilders & Authors*

**Developed by Isondra Krouse** *Copyright © 2026. All rights reserved.*


StoryChema is an ongoing personal portfolio project I'm solo-developing to both mirror my ever-growing (largely self-taught) software engineering skills. It aims to solve many of the inconveniences and issues I, among many other worldbuilders and authors experience during creative processes. This iteration serves as a proof-of-concept. It's visually ugly and dated, stripped down, and purely exists a personal testament to my rudimentary knowledge of programming, technical architecture, design, and so on... In short, this version is a "yes you can!" to myself, regardless of how far from a final product it is in my mind.

## Core Systems Blueprint

### 1. The Polymorphic Relationship Linker
Instead of writing a different database table for every single combination of connections, StorySchema utilizes a single, unified `entity_links` junction framework. Users can dynamically establish bidirectional ties between any two assets on the canvas.
* **Smart Context Resolution:** The engine maps human-readable UI dropdown strings back to explicit system primary IDs in the background.
* **Bidirectional Traversal:** When you open an entity, the engine simultaneously queries both the `source` and `target` database columns so you instantly see every connection leading to or from that note.

### 2. Custom Fantasy Calendars & Timelines
Traditional software forces chronology into standard Gregorian date calendars. StorySchema overrides this entirely by decoupling time parameters:
* **Dynamic Months Structure:** Every world initializes a dedicated calendar backbone inside the database. Users can fully customize, rename, and add custom fantasy months.
* **Automatic Sequence Indexing:** The engine translates disparate Year, Month, and Day entries into a continuous chronological index value, allowing non-traditional time structures to sort sequentially.

### 3. "Ghost" vs. "Canon" Lifecycle Tracking
To support the natural, messy flow of creative writing, entities sport a dynamic state tag:
* **Ghost State:** When an asset is created as a placeholder but contains no descriptive text, it displays an amber `GHOST` badge.
* **Canon State:** The moment an author adds workspace documentation, the layout automatically converts the entity to a green `CANON` status badge, signaling it is an active piece of the lore.

## Technical Stack & Architecture
* **Frontend Design:** Python 3.14 via Tkinter GUI engine utilizing a dynamic hardware-zoomed launch window canvas.
* **Database Management:** SQLite3 featuring strict referential integrity configurations (`PRAGMA foreign_keys = ON;`).
* **Schema Blueprinting:** Normalized relational layout utilizing advanced database index optimization, foreign key constraints, and automatic `updated_at` modification triggers.

## Local Installation & Quick Start

1. **Clone or Download the Project Folder:** Ensure `main.py`, `database_manager.py`, and `schema.sql` are sitting in the same directory.
2. **Launch the Core Application Engine:**
   ```bash
   python main.py
