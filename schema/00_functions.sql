-- Functions (must exist before triggers)

-- Optimistic lock: reject updates where incoming timestamp is not strictly newer
CREATE OR REPLACE FUNCTION reject_unless_newer() RETURNS trigger AS $$
BEGIN
  IF NEW.updated <= OLD.updated THEN
    RETURN NULL;  -- silently skip the update
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;
