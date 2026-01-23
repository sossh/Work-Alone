
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    delay_interval INT
);


CREATE TABLE IF NOT EXISTS escalation_contacts (
    id SERIAL PRIMARY KEY,
    contact_of INT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT NOT NULL,
    FOREIGN KEY (contact_of) REFERENCES users(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    last_check_in_at TIMESTAMP,
    status TEXT CHECK(status IN ('active','inactive','alert')) DEFAULT 'active',
    checked_in_by_contact_id INT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (checked_in_by_contact_id) REFERENCES escalation_contacts(id) ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS message_logs (
    id SERIAL PRIMARY KEY,
    user_id INT NULL,
    contact_id INT NULL,
    timestamp TIMESTAMP NOT NULL,
    message_text TEXT NOT NULL,
    direction TEXT CHECK(direction IN ('incoming','outgoing')) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES escalation_contacts(id) ON DELETE SET NULL
)



CREATE INDEX ON escalation_contacts(contact_of);
CREATE INDEX ON sessions(user_id);
CREATE INDEX ON sessions(checked_in_by_contact_id);
CREATE INDEX ON message_logs(user_id);
CREATE INDEX ON message_logs(contact_id);
