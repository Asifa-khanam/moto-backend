import psycopg2
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
# Enable CORS so your Streamlit frontend can securely talk to this API
CORS(app)

def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        # Fallback for local testing (update with your local postgres credentials if needed)
        return psycopg2.connect(dbname="postgres", user="postgres", password="password", host="localhost", port="5432")

# --- INVENTORY ROUTES ---

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, part_name, part_code, category, cost_price, available_units, alert_limit FROM inventory ORDER BY id DESC;")
    rows = cursor.fetchall()
    items = [{"id": r[0], "part_name": r[1], "part_code": r[2], "category": r[3], "cost_price": float(r[4]), "available_units": r[5], "alert_limit": r[6]} for r in rows]
    cursor.close()
    conn.close()
    return jsonify(items), 200

@app.route('/api/inventory', methods=['POST'])
def add_inventory_item():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO inventory (part_name, part_code, category, cost_price, available_units, alert_limit) VALUES (%s, %s, %s, %s, %s, %s);", 
                   (data['part_name'], data['part_code'], data['category'], data['cost_price'], data['available_units'], data['alert_limit']))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Part added"}), 201

@app.route('/api/inventory/update', methods=['POST'])
def update_inventory_item():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory SET part_name=%s, category=%s, cost_price=%s, available_units=%s, alert_limit=%s WHERE part_code=%s;",
                   (data['part_name'], data['category'], data['cost_price'], data['available_units'], data['alert_limit'], data['part_code']))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Updated"}), 200

@app.route('/api/inventory/update-qty', methods=['POST'])
def update_quantity():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory SET available_units = GREATEST(0, available_units + %s) WHERE part_code = %s;", (data['change'], data['part_code']))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Quantity adjusted"}), 200

@app.route('/api/inventory/delete', methods=['POST'])
def delete_inventory_item():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE part_code = %s;", (data['part_code'],))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Purged"}), 200

# --- ANALYTICS ROUTE ---

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(cost_price * available_units) FROM inventory;")
    val = cursor.fetchone()[0] or 0
    cursor.close()
    conn.close()
    return jsonify({"network_financial_value": float(val)}), 200

# --- BOOKINGS ROUTE ---

@app.route('/api/bookings', methods=['GET', 'POST'])
def manage_bookings():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.get_json()
        cursor.execute("INSERT INTO bookings (name, plate, type, date, time) VALUES (%s, %s, %s, %s, %s);", 
                       (data['name'], data['plate'], data['type'], data['date'], data['time']))
        conn.commit()
    
    cursor.execute("SELECT id, name, plate, type, date, time FROM bookings ORDER BY id DESC;")
    rows = cursor.fetchall()
    bookings = [{"id": r[0], "name": r[1], "plate": r[2], "type": r[3], "date": str(r[4]), "time": str(r[5])} for r in rows]
    cursor.close()
    conn.close()
    return jsonify(bookings), 200

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = %s;", (booking_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Deleted"}), 200

# --- EMERGENCY ROUTE ---

@app.route('/api/emergency/sos', methods=['POST'])
def trigger_emergency_dispatch():
    return jsonify({
        "status": "Dispatched",
        "technician": "Vikram Rathore",
        "unit": "Interceptor 4",
        "contact": "+91 98765 43210",
        "distance_km": "5.2 km",
        "eta_minutes": "20 mins"
    }), 200
# --- TEMPORARY DATABASE SETUP ROUTE ---

@app.route('/api/setup-database', methods=['GET'])
def setup_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Run the exact SQL commands we need
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                part_name VARCHAR(255) NOT NULL,
                part_code VARCHAR(100) UNIQUE NOT NULL,
                category VARCHAR(100),
                cost_price NUMERIC(10, 2),
                available_units INTEGER DEFAULT 0,
                alert_limit INTEGER DEFAULT 3
            );
            
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                plate VARCHAR(100) NOT NULL,
                type VARCHAR(150),
                date DATE,
                time TIME
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return "✅ Database tables created successfully! You can close this tab.", 200
    except Exception as e:
        return f"❌ Error: {str(e)}", 500
        
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
