from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_connection

import pandas as pd
import os

from werkzeug.utils import secure_filename

# ==========================================
# CREATE FLASK APP
# ==========================================

app = Flask(__name__)

app.secret_key = "school-soccer-secret"

# ==========================================
# UPLOAD CONFIGURATION
# ==========================================

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/competitions")
def competitions():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT CompetitionID, CompetitionName, GenderCategory, AgeLimit, Year, Status
        FROM Competitions
        ORDER BY Year DESC, CompetitionName
    """)

    competitions = cursor.fetchall()
    conn.close()

    return render_template("competitions.html", competitions=competitions)


@app.route("/fixtures")
def fixtures():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            f.RoundName,
            hs.SchoolName AS HomeSchool,
            aw.SchoolName AS AwaySchool,
            f.MatchDate,
            f.Venue,
            f.HomeScore,
            f.AwayScore,
            f.Status
        FROM Fixtures f
        LEFT JOIN Schools hs ON f.HomeSchoolID = hs.SchoolID
        LEFT JOIN Schools aw ON f.AwaySchoolID = aw.SchoolID
        ORDER BY f.MatchDate
    """)

    fixtures = cursor.fetchall()
    conn.close()

    return render_template("fixtures.html", fixtures=fixtures)


@app.route("/register-school", methods=["GET", "POST"])
def register_school():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        school_name = request.form["school_name"]
        school_type = request.form["school_type"]
        state_code = request.form["state_code"]
        region = request.form["region"]
        contact_name = request.form["contact_name"]
        email = request.form["email"]
        phone = request.form["phone"]

        cursor.execute("""
            INSERT INTO Schools
            (
                SchoolName,
                SchoolType,
                StateCode,
                Region,
                ContactName,
                Email,
                Phone
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, school_name, school_type, state_code, region, contact_name, email, phone)

        conn.commit()
        conn.close()

        flash("School registration submitted successfully.", "success")
        return redirect(url_for("index"))

    conn.close()
    return render_template("register_school.html")


@app.route("/downloads")
def downloads():
    return render_template("downloads.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/admin")
def admin_dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Schools")
    school_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Competitions")
    competition_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Fixtures")
    fixture_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        school_count=school_count,
        competition_count=competition_count,
        fixture_count=fixture_count
    )


@app.route("/upload-schools", methods=["GET", "POST"])
def upload_schools():
    if request.method == "POST":

        if "excel_file" not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)

        file = request.files["excel_file"]

        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        df = pd.read_excel(filepath)
        df.columns = df.columns.str.strip()
        df = df.fillna("")

        required_columns = [
            "SchoolName",
            "SchoolType",
            "StateCode",
            "Region",
            "ContactName",
            "Email",
            "Phone"
        ]

        for col in required_columns:
            if col not in df.columns:
                flash(f"Missing required Excel column: {col}", "danger")
                return redirect(request.url)

        conn = get_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():

            school_name = str(row["SchoolName"]).strip()
            school_type = str(row["SchoolType"]).strip()
            state_code = str(row["StateCode"]).strip()
            region = str(row["Region"]).strip()
            contact_name = str(row["ContactName"]).strip()
            email = str(row["Email"]).strip()
            phone = str(row["Phone"]).strip()

            if school_name == "":
                skipped += 1
                continue

            cursor.execute("""
                IF NOT EXISTS (
                    SELECT 1
                    FROM Schools
                    WHERE SchoolName = ?
                      AND StateCode = ?
                )
                BEGIN
                    INSERT INTO Schools
                    (
                        SchoolName,
                        SchoolType,
                        StateCode,
                        Region,
                        ContactName,
                        Email,
                        Phone
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                END
            """,
                school_name,
                state_code,
                school_name,
                school_type,
                state_code,
                region,
                contact_name,
                email,
                phone
            )

            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Upload completed. Processed: {len(df)}, inserted/already existed: {inserted}, skipped: {skipped}", "success")
        return redirect(url_for("upload_schools"))

    return render_template("upload_schools.html")

@app.route("/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return "Database Connection OK"
    except Exception as e:
        return f"Database Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)