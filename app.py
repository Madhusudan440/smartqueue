from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import os
import psycopg2
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secure_key_2026"

# ==========================================
# DATABASE CONNECTION (Render PostgreSQL)
# ==========================================

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set in environment variables")

    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

# ==========================================
# AUTO CREATE TABLE
# ==========================================

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                age TEXT NOT NULL,
                gender TEXT NOT NULL,
                address TEXT NOT NULL,
                mobile TEXT NOT NULL,
                status TEXT DEFAULT 'Waiting',
                checkin_time TEXT
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully")

    except Exception as e:
        print("Database initialization error:", e)

init_db()

# ==========================================
# DISABLE BACK BUTTON CACHE
# ==========================================

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")

# ==========================================
# PATIENT CHECKIN
# ==========================================

@app.route("/checkin", methods=["POST"])
def checkin():
    try:
        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        address = request.form.get("address")
        mobile = request.form.get("mobile")

        checkin_time = datetime.now().strftime("%d-%m-%Y %I:%M %p")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO patients (name, age, gender, address, mobile, checkin_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (name, age, gender, address, mobile, checkin_time))

        token_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "token": token_id
        })

    except Exception as e:
        print("Checkin error:", e)
        return jsonify({"success": False})

# ==========================================
# ADMIN LOGIN
# ==========================================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "admin@gmail.com" and password == "admin123":
            session.clear()
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Email or Password")

    return render_template("admin_login.html")

# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "admin_logged_in" not in session:
        return redirect(url_for("admin"))

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name, age, gender, address, mobile, status, checkin_time
            FROM patients
            ORDER BY id ASC
        """)

        rows = cur.fetchall()

        patients = []
        for row in rows:
            patients.append({
                "id": row[0],
                "name": row[1],
                "age": row[2],
                "gender": row[3],
                "address": row[4],
                "mobile": row[5],
                "status": row[6],
                "checkin_time": row[7]
            })

        cur.close()
        conn.close()

        waiting = sum(1 for p in patients if p["status"] == "Waiting")
        called = sum(1 for p in patients if p["status"] == "Called")
        completed = sum(1 for p in patients if p["status"] == "Completed")

        return render_template(
            "dashboard.html",
            patients=patients,
            waiting=waiting,
            called=called,
            completed=completed
        )

    except Exception as e:
        print("Dashboard error:", e)
        return "Internal Server Error", 500

# ==========================================
# CALL PATIENT
# ==========================================

@app.route("/call/<int:id>", methods=["POST"])
def call_patient(id):

    if "admin_logged_in" not in session:
        return jsonify({"success": False})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("UPDATE patients SET status='Called' WHERE id=%s", (id,))
        conn.commit()

        cur.execute("SELECT mobile FROM patients WHERE id=%s", (id,))
        result = cur.fetchone()

        cur.close()
        conn.close()

        if not result:
            return jsonify({"success": False})

        return jsonify({
            "success": True,
            "mobile": result[0]
        })

    except Exception as e:
        print("Call error:", e)
        return jsonify({"success": False})

# ==========================================
# COMPLETE PATIENT
# ==========================================

@app.route("/complete/<int:id>", methods=["POST"])
def complete_patient(id):

    if "admin_logged_in" not in session:
        return jsonify({"success": False})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("UPDATE patients SET status='Completed' WHERE id=%s", (id,))
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        print("Complete error:", e)
        return jsonify({"success": False})

# ==========================================
# PRINT RECEIPT
# ==========================================

@app.route("/print/<int:id>")
def print_receipt(id):

    if "admin_logged_in" not in session:
        return redirect(url_for("admin"))

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM patients WHERE id=%s", (id,))
        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row:
            return "Patient Not Found", 404

        patient = {
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "gender": row[3],
            "address": row[4],
            "mobile": row[5],
            "status": row[6],
            "checkin_time": row[7]
        }

        return render_template("print_receipt.html", patient=patient)

    except Exception as e:
        print("Print error:", e)
        return "Internal Server Error", 500

# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))

# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
