from flask import Flask, jsonify, request
from functools import wraps
import sqlite3
import datetime

app = Flask(__name__)
DATABASE = 'tenants.db'

#Helper functions
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def validate_tenant(tenant_id):
    conn = get_db()
    tenant = conn.execute('SELECT id FROM tenants WHERE id = ?', (tenant_id,)).fetchone()
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
    required_fields = ['id', 'username', 'ip_source', 'status', 'timestamp']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if data['status'] not in ('success', 'failure'):
        return jsonify({'error': 'Invalid status value'}), 400
   
    #Check if indempotent
    conn = get_db()
    existing = conn.execute('SELECT id FROM logins WHERE id = ? AND tenant_id = ?', (data['id'], tenant_id)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Event already exists'}), 409
    
    #Insert new event into database
    try:
        conn.execute('INSERT INTO logins (id, tenant_id, username, ip_source, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)', (data['id'], tenant_id, data['username'], data['ip_source'], data['status'], data['timestamp']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Event created'}), 201
    except sqlite3.Error as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

#GET -- suspicious events
@app.route('/api/<tenant_id>/event/suspicious', methods=['POST'])
@tenant_required
def get_suspicious_events(tenant_id):
    #Validate parameters
    try:
        minutes = int(request.args.get('minutes'))
        threshold = int(request.args.get('threshold'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid minutes or threshold'}), 400
    
    if minutes <= 0 or threshold <= 0:
        return jsonify({'error': 'Minutes and threshold must be positive integers'}), 400
    
    #Parameters for sorting
    sort_field = request.args.get('sort', 'failure_count')
    sort_order = request.args.get('order', 'desc')
    valid_sort_fields = ['failure_count', 'ip_source', 'last_attempt']
    if sort_field not in valid_sort_fields:
        return jsonify({'error': 'Invalid sort field'}), 400
    
    #Parameters for pagination
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    if page < 1 or per_page < 1:
        return jsonify({'error': 'Invalid pagination parameters'}), 400
    
    #Calculate time window
    time_window = datetime.utcnow() - datetime.timedelta(minutes=minutes)
    
    conn = get_db()
    #Get suspicious IPs with failure counts
    query = '''SELECT ip_source, COUNT(*) as failure_count, MAX(timestamp) as last_attempt, MIN(timestamp) as first_attempt
        FROM logins
        WHERE tenant_id = ? AND status = 'failure' AND timestamp >= ?
        GROUP BY ip_source
        HAVING COUNT(*) >= ?
        ORDER BY {} {}
        LIMIT ? OFFSET ?'''.format(sort_field, sort_order)
    suspicious_ips = conn.execute(query, (tenant_id, time_window.isoformat(), threshold, per_page, (page-1)*per_page)).fetchall()
    
    #Total failure count
    total = conn.execute('''SELECT COUNT(DISTINCT ip_source) as total
        FROM (SELECT ip_source
                FROM logins
                WHERE tenant_id = ? AND status = 'failure' AND timestamp >= ?
                GROUP BY ip_source
                HAVING COUNT(*) >= ?)''', (tenant_id, time_window.isoformat(), threshold)).fetchone()
    conn.close()

    result = {
        'data': [dict(ip) for ip in suspicious_ips],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total['total'] if total else 0
        }
    }
    return jsonify(result)
