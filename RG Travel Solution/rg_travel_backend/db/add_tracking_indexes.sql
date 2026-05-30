-- Add indexes for driver_live_locations table to improve query performance
-- Run this migration after the main schema.sql has been executed

CREATE INDEX IF NOT EXISTS idx_driver_live_locations_driver 
  ON driver_live_locations(driver_id);

CREATE INDEX IF NOT EXISTS idx_driver_live_locations_route 
  ON driver_live_locations(route_no);

-- Verify indexes
SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='driver_live_locations';
