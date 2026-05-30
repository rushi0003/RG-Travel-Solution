-- Create Driver Change Requests Table
CREATE TABLE IF NOT EXISTS driver_change_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id TEXT NOT NULL,
    name TEXT,
    mobile TEXT,
    dl_no TEXT,
    vehicle_no TEXT,
    vehicle_type TEXT,
    home_town TEXT,
    status TEXT DEFAULT 'Pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(driver_id) REFERENCES drivers(id)
);

-- Create Employee Change Requests Table
CREATE TABLE IF NOT EXISTS employee_change_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    name TEXT,
    mobile TEXT,
    home_address TEXT,
    status TEXT DEFAULT 'Pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(employee_id) REFERENCES employees(id)
);
