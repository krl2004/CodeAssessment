Database schema:

    CREATE TABLE tenants (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    );

    CREATE TABLE login (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        ip_source TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status in ('success', 'failure')),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    One table needed to keep track of the individual tenants, one table to keep track of each login and its relevant data


API construction:

    Initialize the database by creating the tables shown above and inserting data (ex: INSERT INTO tenants (id, name) VALUES ('1', 'First Last'))

    POST -- insert new login event
        Validate input data -- check to make sure all fields are filled in and in correct format
        Check indempotency of event -- if it doesn't exist, then insert the event into login table

        Example query:
            POST /api/1/events
                Content-Type: application/json
                {
                    "event_id": "string-for-id",
                    "user_id": "2",
                    "ip-source": "123.456.7.8",
                    "status": "failure",
                    "timestamp": "2025-05-02T12:34:56Z"
                }
    
    GET -- return suspicious login fails
