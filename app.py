from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secure_key_2026"

# ==============================
# DATABASE CONFIG (Railway)
# ==============================

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn


# ==============================
# CREATE TABLE IF NOT EXISTS
# ==============================

def init_db():
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

init_db()


# ==============================
# DISABLE BACK CACHE
# ==============================

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store"
    return response


# ==============================
# HOME
# ==============================

@app.route("/")
def home():
    return render_template("index.html")


# ==============================
# CHECKIN (PATIENT)
# ==============================

@app.route("/checkin", methods=["POST"])
def checkin():

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


# ==============================
# ADMIN LOGIN
# ==============================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "admin@gmail.com" and password == "admin123":
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Email or Password")

    return render_template("admin_login.html")


# ==============================
# DASHBOARD
# ==============================

@app.route("/dashboard")
def dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM patients ORDER BY id ASC")
    patients = cur.fetchall()

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


# ==============================
# CALL PATIENT
# ==============================

@app.route("/call/<int:id>", methods=["POST"])
def call_patient(id):

    if not session.get("admin_logged_in"):
        return jsonify({"success": False})

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


# ==============================
# COMPLETE PATIENT
# ==============================

@app.route("/complete/<int:id>", methods=["POST"])
def complete_patient(id):

    if not session.get("admin_logged_in"):
        return jsonify({"success": False})

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("UPDATE patients SET status='Completed' WHERE id=%s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"success": True})


# ==============================
# PRINT RECEIPT
# ==============================

@app.route("/print/<int:id>")
def print_receipt(id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM patients WHERE id=%s", (id,))
    patient = cur.fetchone()

    cur.close()
    conn.close()

    if not patient:
        return "Patient Not Found", 404

    return render_template("print_receipt.html", patient=patient)


# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


# ==============================
# RUN (LOCAL ONLY)
# ==============================

if __name__ == "__main__":
    app.run(debug=True)
 
