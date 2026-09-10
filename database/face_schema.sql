-- Face detection tables
CREATE TABLE IF NOT EXISTS face_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    encoding BLOB NOT NULL,
    image_path TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS face_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    face_id INTEGER,
    image_path TEXT,
    location_top INTEGER,
    location_right INTEGER,
    location_bottom INTEGER,
    location_left INTEGER,
    confidence REAL,
    created_at TEXT,
    FOREIGN KEY (face_id) REFERENCES face_data(id)
);

-- Add face columns to photos table if not exists
ALTER TABLE photos ADD COLUMN face_count INTEGER DEFAULT 0;
ALTER TABLE photos ADD COLUMN face_data TEXT;
