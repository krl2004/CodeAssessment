Database schema:

    CREATE TABLE tenants (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    );

    CREATE TABLE logins (
        id TEXT PRIMARY KEY,
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
        Create and execute post query

        Example query:
            POST /api/1/events
                Content-Type: application/json
                {
                    "id": "string-for-id",
                    "username": "string-for-username",
                    "ip_source": "123.456.7.8",
                    "status": "failure",
                    "timestamp": "2025-05-02T12:34:56Z"
                }
    
    GET -- return suspicious login fails
        Validate input parameters for minutes spent attempting and threshold of unsuccessful attempts
        Validate parameters for sorting by failure_count, ip_source, and last_attempt
        Validate parameters for pagination
        Create and execute get query
        Format query results and return them

        Example query:
            GET /api/1/events/suspicious?minutes=25&threshold=10&page=1&sort=failure_count&order=desc
        Example result:
            {
                "data": [
                    {
                        "source_ip": "123.456.7.8",
                        "failure_count": 12,
                        "last_attempt": "2025-05-02T12:34:56Z",
                        "first_attempt": "2025-05-02T12:09:00Z"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "per_page": 10,
                    "total_items": 12
                }
            }