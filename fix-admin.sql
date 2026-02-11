-- Fix admin user with correct bcrypt hash
DELETE FROM users WHERE username = 'admin';

INSERT INTO users (user_id, username, email, password_hash, full_name, role_id, is_active, created_at)
VALUES (
    gen_random_uuid(),
    'admin',
    'admin@addrai.com',
    '$2b$12$ndTaxsu9T4Q5hkPRwn9ds.DQKiKn//qhVwNP5lnpOfgR4rwoCm64u',
    'System Administrator',
    1,
    true,
    NOW()
);

-- Verify
SELECT username, email, LENGTH(password_hash) as hash_len, LEFT(password_hash, 7) as prefix 
FROM users WHERE username = 'admin';