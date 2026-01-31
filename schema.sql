-- PostgreSQL schema for external DB (managed via pgAdmin4)
-- This script creates only the application tables; it does not create the database.
-- Ensure you connect to your target database (e.g., doanpythonc) before running.

-- Users table for authentication
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(128) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    email VARCHAR(128) NOT NULL UNIQUE,
    fullname VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.user_settings (
  user_id INTEGER PRIMARY KEY,
  theme VARCHAR(20) DEFAULT 'light',
  language VARCHAR(10) DEFAULT 'vi',
  notifications BOOLEAN DEFAULT TRUE,
  email_notifications BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.prediction_history (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  image_path VARCHAR(500) NOT NULL,
  breed VARCHAR(200),
  confidence FLOAT,
  species VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- Quota tracking: free 10 predictions, then up to 3 ad views to unlock extra uses
CREATE TABLE IF NOT EXISTS public.user_quota (
  user_id INTEGER PRIMARY KEY,
  plan VARCHAR(20) NOT NULL DEFAULT 'free',
  ad_views_used INTEGER NOT NULL DEFAULT 0,
  ad_unlocks_remaining INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  plan_expire TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- Payment orders (demo) for admin tracking
CREATE TABLE IF NOT EXISTS public.payment_orders (
  id SERIAL PRIMARY KEY,
  order_id VARCHAR(32) NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  plan VARCHAR(20) NOT NULL,
  payment_method VARCHAR(20) NOT NULL,
  amount_vnd INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_at TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- Nếu thiếu cột trong users:
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
-- Optional: seed an example admin user (replace the hash with a real one).
-- The hash below is just a placeholder; generate with Python werkzeug.security.generate_password_hash.
-- INSERT INTO public.users (username, password_hash) VALUES ('admin', 'pbkdf2:sha256:...');

-- If your users table already exists, run this migration to add columns:
-- ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
-- ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
-- To promote a user to admin:
-- UPDATE public.users SET role = 'admin' WHERE username = '<your_admin_username>';
-- To deactivate a user:
-- UPDATE public.users SET is_active = FALSE WHERE username = '<username>'; 

-- Verify
-- SELECT id, username, created_at FROM public.users ORDER BY id;
