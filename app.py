from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "super_secure_key_2026"

# ==============================
# DATABASE CONNECTION (SQLite)
# ==============================

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ==============================
# CREATE TABLE IF NOT EXISTS
# ==============================

def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age TEXT NOT NULL,
            gender TEXT NOT NULL,
            address TEXT NOT NULL,
            mobile TEXT NOT NULL,
            status TEXT DEFAULT 'Waiting',
            checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ==============================
# DISABLE BACK BUTTON CACHE
# ==============================

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ==============================
# HOME PAGE
# ==============================

@app.route("/")
def home():
    return render_template("index.html")


# ==============================
# PATIENT CHECK-IN (AJAX)
# ==============================

@app.route("/checkin", methods=["POST"])
def checkin():

    name = request.form.get("name")
    age = request.form.get("age")
    gender = request.form.get("gender")
    address = request.form.get("address")
    mobile = request.form.get("mobile")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO patients 
        (name, age, gender, address, mobile)
        VALUES (?, ?, ?, ?, ?)
    """, (name, age, gender, address, mobile))

    conn.commit()
    token_id = cursor.lastrowid
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
            session.clear()
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Email or Password")

    return render_template("admin_login.html")


# ==============================
# DASHBOARD (PROTECTED)
# ==============================

@app.route("/dashboard")
def dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    conn = get_db_connection()
    patients = conn.execute("SELECT * FROM patients ORDER BY id ASC").fetchall()
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
# CALL PATIENT (AJAX)
# ==============================

@app.route("/call/<int:id>", methods=["POST"])
def call_patient(id):

    if not session.get("admin_logged_in"):
        return jsonify({"success": False})

    conn = get_db_connection()

    # Update status
    conn.execute("UPDATE patients SET status='Called' WHERE id=?", (id,))
    conn.commit()

    # Get mobile number
    patient = conn.execute("SELECT mobile FROM patients WHERE id=?", (id,)).fetchone()
    conn.close()

    return jsonify({
        "success": True,
        "mobile": patient["mobile"]
    })


# ==============================
# COMPLETE PATIENT (AJAX)
# ==============================

@app.route("/complete/<int:id>", methods=["POST"])
def complete_patient(id):

    if not session.get("admin_logged_in"):
        return jsonify({"success": False})

    conn = get_db_connection()
    conn.execute("UPDATE patients SET status='Completed' WHERE id=?", (id,))
    conn.commit()
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
    patient = conn.execute("SELECT * FROM patients WHERE id=?", (id,)).fetchone()
    conn.close()

    if not patient:
        return "Patient Not Found"

    return render_template("print_receipt.html", patient=patient)


# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


# ==============================
# RUN APP
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
