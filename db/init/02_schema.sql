-- users
CREATE TABLE IF NOT EXISTS users(
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  password_hash TEXT,
  full_name TEXT,
  role TEXT NOT NULL DEFAULT 'customer',
  rating_avg NUMERIC(3,2) NOT NULL DEFAULT 0.00,
  rating_cnt INT NOT NULL DEFAULT 0,
  can_post_jobs BOOLEAN NOT NULL DEFAULT TRUE,
  can_take_jobs BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- pets
CREATE TABLE IF NOT EXISTS pets(
  id BIGSERIAL PRIMARY KEY,
  owner_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('dog','cat','other')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- jobs
CREATE TABLE IF NOT EXISTS jobs(
  id BIGSERIAL PRIMARY KEY,
  customer_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
  pet_id BIGINT REFERENCES pets(id) ON DELETE SET NULL,
  category TEXT NOT NULL CHECK (category IN ('walk','boarding','grooming','other')),
  title TEXT NOT NULL,
  description TEXT,
  price_rub INT NOT NULL,
  scheduled_at TIMESTAMPTZ,
  location GEOGRAPHY(POINT,4326),
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open','assigned','in_progress','done','cancelled')),
  provider_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_loc_gix ON jobs USING GIST(location);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs(status);

-- walk sessions
CREATE TABLE IF NOT EXISTS walk_sessions(
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  duration_sec INT,
  distance_m INT
);

-- walk points
CREATE TABLE IF NOT EXISTS walk_points(
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES walk_sessions(id) ON DELETE CASCADE,
  seq INT,
  loc GEOGRAPHY(POINT,4326) NOT NULL,
  ts TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS walk_points_loc_gix ON walk_points USING GIST(loc);

-- media (photos)
CREATE TABLE IF NOT EXISTS media(
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
  session_id BIGINT REFERENCES walk_sessions(id) ON DELETE CASCADE,
  uploader_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  url TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'photo' CHECK (kind IN ('photo','video')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- reviews
CREATE TABLE IF NOT EXISTS reviews(
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
  from_user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
  to_user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
  rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (job_id, from_user_id, to_user_id)
);
