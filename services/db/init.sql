CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  name TEXT,
  age INT,
  sex TEXT,
  height_m FLOAT,
  weight_kg FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exercise_tracking (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  session_date DATE,
  workout_type TEXT,
  calories_burned FLOAT,
  session_duration_hours FLOAT,
  max_bpm INT,
  avg_bpm INT,
  resting_bpm INT
);

CREATE TABLE IF NOT EXISTS plans (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
