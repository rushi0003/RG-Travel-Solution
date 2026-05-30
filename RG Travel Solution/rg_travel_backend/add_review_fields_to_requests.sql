-- Add review_note and reviewed_at columns to driver_requests table
-- This enables capturing rejection reasons and timestamps

ALTER TABLE driver_requests ADD COLUMN review_note TEXT;
ALTER TABLE driver_requests ADD COLUMN reviewed_at TEXT;
