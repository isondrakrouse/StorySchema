-- StorySchema v1.0.1 Database Schema
-- Copyright © 2026 Isondra Krouse. All rights reserved.

-- << DATABASE CONFIGURATION >>
-- SQLite

-- 1. Enable Referential Integrity (FK Enforcement)
PRAGMA foreign_keys = ON;

-- 2. USERS
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. WORLDS
-- Root container for all worldbuilding
CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_name TEXT NOT NULL,
    world_desc TEXT,

    -- A/N: I removed DEFAULT 1
    owner_id INTEGER,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,

    FOREIGN KEY (owner_id)
        REFERENCES users(id)
        ON DELETE SET NULL,

    UNIQUE(owner_id, world_name)
    -- Allows different users to have worlds with the same name
    -- while still preventing duplicate world names per user
);

CREATE INDEX IF NOT EXISTS idx_worlds_owner_id
ON worlds(owner_id);

-- 4.a CALENDAR SYSTEM
CREATE TABLE IF NOT EXISTS calendars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,
    
    calendar_name TEXT NOT NULL DEFAULT 'Standard',

    -- Validation checks to prevent invalid values
    hours_per_day INTEGER NOT NULL DEFAULT 24
        CHECK (hours_per_day > 0),
    
    leap_year_interval INTEGER NOT NULL DEFAULT 4
        CHECK (leap_year_interval >= 0),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_calendars_world_id
ON calendars(world_id);

-- 4.b CALENDAR MONTHS
CREATE TABLE IF NOT EXISTS calendar_months (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    calendar_id INTEGER NOT NULL,

    month_name TEXT NOT NULL,

    -- Ensures proper chronological ordering
    month_order INTEGER NOT NULL
        CHECK (month_order > 0),

    -- Prevents impossible month lengths    
    day_count INTEGER NOT NULL
        CHECK (day_count > 0),

    leap_day_count INTEGER NOT NULL DEFAULT 0
        CHECK (leap_day_count >= 0),

    FOREIGN KEY (calendar_id)
        REFERENCES calendars(id)
        ON DELETE CASCADE,
    
    UNIQUE(calendar_id, month_order),
    UNIQUE(calendar_id, month_name)
);

CREATE INDEX IF NOT EXISTS idx_calendar_months_calendar_id
ON calendar_months(calendar_id);

-- 5. LOCATIONS
-- Supports recursive hierarchy structure
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    parent_location_id INTEGER,

    location_name TEXT NOT NULL,
    location_desc TEXT,

    location_status TEXT NOT NULL DEFAULT 'Canon'
        CHECK (location_status IN ('Canon', 'Ghost', 'Draft')),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE,

    FOREIGN KEY (parent_location_id)
        REFERENCES locations(id)
        ON DELETE SET NULL,    

    -- Prevents duplicate location names inside of the same world
    UNIQUE(world_id, location_name),

    -- Prevents self-parenting recursion edge case
    CHECK (
        parent_location_id IS NULL
        OR parent_location_id != id
    )
);

CREATE INDEX IF NOT EXISTS idx_locations_world_id
ON locations(world_id);

CREATE INDEX IF NOT EXISTS idx_locations_parent_location_id
ON locations(parent_location_id);

-- 6. CHARACTERS
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    char_name TEXT NOT NULL,
    biography TEXT,

    char_status TEXT NOT NULL DEFAULT 'Canon'
        CHECK (char_status IN ('Canon', 'Ghost', 'Draft')),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE,

    -- Prevents duplicate characters within the same world
    -- Important for Ghost-Entity creation workflow
    UNIQUE(world_id, char_name)
);

CREATE INDEX IF NOT EXISTS idx_characters_world_id
ON characters(world_id);

-- 7. CODEX ENTRIES
-- Flexible storage
CREATE TABLE IF NOT EXISTS codex_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    -- A/N: May replace this with lookup tables during PostgreSQL migration
    entity_type TEXT NOT NULL
        CHECK (
            entity_type IN (
                'Event',
                'Item',
                'System',
                'Lore'
            )
        ),
    
    entry_name TEXT NOT NULL,
    entry_content TEXT,

    -- Flexible non-Gregorian calendar date support
    event_date_str TEXT,

    -- Sortable chronology support
    chronological_index INTEGER,

    entry_status TEXT NOT NULL DEFAULT 'Canon'
        CHECK (
            entry_status IN (
                'Canon',
                'Ghost',
                'Draft'
            )
        ),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE,
    
    -- Prevent duplicate codex names within a world
    UNIQUE(world_id, entry_name)
);

CREATE INDEX IF NOT EXISTS idx_codex_entries_world_id
ON codex_entries(world_id);

CREATE INDEX IF NOT EXISTS idx_codex_entries_entity_type
ON codex_entries(entity_type);

CREATE INDEX IF NOT EXISTS idx_codex_entries_chronological_index
ON codex_entries(chronological_index);

-- 8. ENTITY LINKS
-- Flexible polymorphic relationship graph
-- A\N: Enforcement of polymorphic FKs will be handled and validated in the Python service layer

CREATE TABLE IF NOT EXISTS entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    source_id INTEGER NOT NULL,

    source_type TEXT NOT NULL
        CHECK (
            source_type IN (
                'Character',
                'Location',
                'CodexEntry'
            )
        ),

    target_id INTEGER NOT NULL,

    target_type TEXT NOT NULL
        CHECK (
            target_type IN (
                'Character',
                'Location',
                'CodexEntry'
            )
        ),
    
    connection_type TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE,

    -- Prevent duplicate relationships
    UNIQUE (
        world_id,
        source_id,
        source_type,
        target_id,
        target_type,
        connection_type
    ),

    -- Prevent self-linking edge case
    CHECK (
        NOT (
            source_id = target_id
            AND source_type = target_type
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_entity_links_world_id
ON entity_links(world_id);

CREATE INDEX IF NOT EXISTS idx_entity_links_source
ON entity_links(source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_entity_links_target
ON entity_links(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_entity_links_connection_type
ON entity_links(connection_type);

-- 9. ATTRIBUTES
-- Flexible metadata storage
-- A\N: Core fields remain in structured tables intentionally

CREATE TABLE IF NOT EXISTS attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    entity_id INTEGER NOT NULL,

    entity_type TEXT NOT NULL
        CHECK (
            entity_type IN (
                'Character',
                'Location',
                'CodexEntry'
            )
        ),

    attr_key TEXT NOT NULL,
    attr_value TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE,

    -- Prevent duplicate attribute keys on the same entity
    UNIQUE(entity_type, entity_id, attr_key)
);

CREATE INDEX IF NOT EXISTS idx_attributes_world_id
ON attributes(world_id);

CREATE INDEX IF NOT EXISTS idx_attributes_entity
ON attributes(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_attributes_attr_key
ON attributes(attr_key);

-- 10. TAGS
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    tag_name TEXT NOT NULL,
    color_code TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE,

    UNIQUE(world_id, tag_name)
);

CREATE INDEX IF NOT EXISTS idx_tags_world_id
ON tags(world_id);

-- 11. ENTITY TAGS
-- A\N: Added junction table so tags can actually attach to entities
CREATE TABLE IF NOT EXISTS entity_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    entity_id INTEGER NOT NULL,

    entity_type TEXT NOT NULL
        CHECK (
            entity_type IN (
                'Character',
                'Location',
                'CodexEntry'
            )
        ),
    
    tag_id INTEGER NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE,

    FOREIGN KEY (tag_id)
        REFERENCES tags(id)
        ON DELETE CASCADE,

    -- Prevent duplicate tag assignments
    UNIQUE(entity_type, entity_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_tags_world_id
ON entity_tags(world_id);

CREATE INDEX IF NOT EXISTS idx_entity_tags_entity
ON entity_tags(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_tags_tag_id
ON entity_tags(tag_id);

-- 12. MEDIA ATTACHMENTS
CREATE TABLE IF NOT EXISTS media_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    world_id INTEGER NOT NULL,

    entity_id INTEGER NOT NULL,

    entity_type TEXT NOT NULL
        CHECK (
            entity_type IN (
                'Character',
                'Location',
                'CodexEntry'
            )
        ),

    file_path TEXT NOT NULL,

    caption TEXT,

    -- A\N: Future-proofing with added metadata support
    mime_type TEXT,
    file_size INTEGER,
    file_checksum TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (world_id)
        REFERENCES worlds(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_attachments_world_id
ON media_attachments(world_id);

CREATE INDEX IF NOT EXISTS idx_media_attachments_entity
ON media_attachments(entity_type, entity_id);

-- 13. AUTOMATION TRIGGERS
-- These triggers ensure updated_at is refreshed on modification
-- The WHEN clause prevents recursive trigger loops

CREATE TRIGGER IF NOT EXISTS trg_worlds_updated_at
AFTER UPDATE ON worlds
FOR EACH ROW
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE worlds
    SET updated_at = CURRENT_TIMESTAMP
    where id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_calendars_updated_at
AFTER UPDATE ON calendars
FOR EACH ROW
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE calendars
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_locations_updated_at
AFTER UPDATE ON locations
FOR EACH ROW
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE locations
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_characters_updated_at
AFTER UPDATE ON characters
FOR EACH ROW
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE characters
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_codex_entries_updated_at
AFTER UPDATE ON codex_entries
FOR EACH ROW
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE codex_entries
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;