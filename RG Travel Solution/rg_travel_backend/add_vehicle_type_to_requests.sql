-- Add vehicle_type column to driver_requests table
-- This migration captures the vehicle type (4 or 6 seater) that drivers select during registration

ALTER TABLE driver_requests 
ADD COLUMN vehicle_type TEXT DEFAULT '4';

-- Update any existing NULL values to default '4'
UPDATE driver_requests 
SET vehicle_type = '4' 
WHERE vehicle_type IS NULL;
