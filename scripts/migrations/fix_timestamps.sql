DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    LOOP
        BEGIN
            EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP', t);
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Could not add created_at to %: %', t, SQLERRM;
        END;
        BEGIN
            EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP', t);
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Could not add updated_at to %: %', t, SQLERRM;
        END;
    END LOOP;
END $$;
