-- backend/db/migrations/004_route_optimization.sql
-- Add route optimization fields for Google Maps Directions API integration
-- STEP 7: Multi-stop route planning with waypoint optimization

-- Trips table: Add optimized waypoint order and duration
ALTER TABLE trips ADD COLUMN optimized_waypoint_order TEXT;  -- JSON array of optimized indices
ALTER TABLE trips ADD COLUMN total_duration_minutes INTEGER;  -- Total trip duration from Google Maps

-- Trip employees: Add stop sequence and ETA
ALTER TABLE trip_employees ADD COLUMN stop_sequence INTEGER;  -- Order in optimized route (1, 2, 3...)
ALTER TABLE trip_employees ADD COLUMN estimated_arrival_time TEXT;  -- ISO timestamp for arrival at this stop

-- Note: total_km and polyline fields already exist in trips table
-- total_km renamed to total_distance_km in application layer for clarity
