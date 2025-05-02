from flask import Flask, jsonify, request
from functools import wraps
import sqlite3

app = Flask(__name__)
DATABASE = 'tenants.db'

#Helper functions
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def validate_tenant(tenant_id):
    conn = get_db()
    tenant = conn.execute(
        'SELECT id FROM tenants WHERE id = ?', (tenant_id,)
    ).fetchone()
    conn.close()
    return tenant is not None

def tenant_required(f):
    @wraps(f)
    def decorated_function(tenant_id, *args, **kwargs):
        if not validate_tenant(tenant_id):
            return jsonify({'error': 'Tenant not found'}), 404
        return f(tenant_id, *args, **kwargs)
    return decorated_function

#API Endpoints
#POST -- new event
@app.route('/api/<tenant_id>/events', methods=['GET'])
@tenant_required
def create_event(tenant_id):

    data = request.get_json()

    #Validate input data
    required_fields = ['event_id', 'user_id', 'ip_source', 'status', 'timestamp']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if data['status'] not in ('success', 'failure'):
        return jsonify({'error': 'Invalid status value'}), 400
   
    #Check if indempotent
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM login_events WHERE id = ? AND tenant_id = ?', (data['event_id'], tenant_id)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Event already exists'}), 409
    
    #Insert new event into database
    try:
        conn.execute(
            'INSERT INTO login_events (id, tenant_id, user_id, ip_source, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)', (data['event_id'], tenant_id, data['user_id'], data['ip_source'], data['status'], data['timestamp'])
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Event created'}), 201
    except sqlite3.Error as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
