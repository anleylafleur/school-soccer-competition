from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_connection
from werkzeug.utils import secure_filename

import os
import pandas as pd

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from functools import wraps

from flask import session


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "school-soccer-secret")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



ENTITIES = {
    "worlds": {"title": "Worlds", "table": "Worlds", "pk": "WorldID", "order_by": "WorldID DESC"},
    "confederations": {"title": "Confederations", "table": "Confederations", "pk": "ConfederationID", "order_by": "ConfederationID DESC"},
    "countries": {"title": "Countries", "table": "Countries", "pk": "CountryID", "order_by": "CountryID DESC"},
    "regions": {"title": "Regions", "table": "Regions", "pk": "RegionID", "order_by": "RegionID DESC"},
    "associations": {"title": "Associations", "table": "Associations", "pk": "AssociationID", "order_by": "AssociationID DESC"},
    "clubs": {"title": "Clubs", "table": "Clubs", "pk": "ClubID", "order_by": "ClubID DESC"},
    "teams": {"title": "Teams", "table": "Teams", "pk": "TeamID", "order_by": "TeamID DESC"},
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "Admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("admin_dashboard"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("login"))

@app.route("/db-test")
def db_test():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DB_NAME(), CURRENT_USER, SYSTEM_USER")
        row = cursor.fetchone()
        conn.close()
        return f"DB OK: {row[0]} | User: {row[1]} | Login: {row[2]}"
    except Exception as e:
        return f"DB ERROR: {str(e)}", 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return redirect(url_for("login"))

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT UserID, Username, Email, PasswordHash, Role, IsActive
                FROM Users
                WHERE LOWER(Email) = ?
            """, email)

            user = cursor.fetchone()
            conn.close()

            if not user:
                flash("No account found with that email address.", "danger")
                return redirect(url_for("login"))

            if hasattr(user, "IsActive") and user.IsActive == 0:
                flash("This account is inactive. Please contact the administrator.", "danger")
                return redirect(url_for("login"))

            if check_password_hash(user.PasswordHash, password):
                session.clear()
                session["user_id"] = user.UserID
                session["username"] = user.Username if hasattr(user, "Username") else ""
                session["email"] = user.Email
                session["role"] = user.Role if hasattr(user, "Role") else "User"
                flash("Login successful.", "success")
                return redirect(url_for("admin_dashboard"))

            flash("Invalid password.", "danger")
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Login failed: {str(e)}", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("signup"))

        password_hash = generate_password_hash(password)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Users
            (Username, Email, PasswordHash, Role)
            VALUES (?, ?, ?, ?)
        """,
        username,
        email,
        password_hash,
        "User")

        conn.commit()
        conn.close()

        flash("Account created successfully.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    
    conn = get_connection()
    cursor = conn.cursor()

    fifa_cards = []

    for entity, config in ENTITIES.items():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {config['table']}")
            count = cursor.fetchone()[0]
        except Exception:
            count = "N/A"

        fifa_cards.append({
            "title": config["title"],
            "url": url_for("list_records", entity=entity),
            "count": count
        })

    cursor.execute("SELECT COUNT(*) FROM Schools")
    school_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Competitions")
    competition_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Fixtures")
    fixture_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Results")
    result_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        fifa_cards=fifa_cards,
        school_count=school_count,
        competition_count=competition_count,
        fixture_count=fixture_count,
        result_count=result_count
    )


@app.route("/schools")
def schools():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SchoolID, SchoolName, SchoolType, StateCode, Region, ContactName, Email, Phone
        FROM Schools
        ORDER BY StateCode, Region, SchoolName
    """)

    schools = cursor.fetchall()
    conn.close()

    return render_template("schools.html", schools=schools)


@app.route("/schools/add", methods=["GET", "POST"])
def add_school():
    if request.method == "POST":
        school_name = request.form["school_name"]
        school_type = request.form["school_type"]
        state_code = request.form["state_code"]
        region = request.form["region"]
        contact_name = request.form["contact_name"]
        email = request.form["email"]
        phone = request.form["phone"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Schools
            (SchoolName, SchoolType, StateCode, Region, ContactName, Email, Phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, school_name, school_type, state_code, region, contact_name, email, phone)

        conn.commit()
        conn.close()

        flash("School added successfully.", "success")
        return redirect(url_for("schools"))

    return render_template("school_form.html", school=None)


@app.route("/schools/edit/<int:school_id>", methods=["GET", "POST"])
def edit_school(school_id):
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
            UPDATE Schools
            SET SchoolName = ?,
                SchoolType = ?,
                StateCode = ?,
                Region = ?,
                ContactName = ?,
                Email = ?,
                Phone = ?
            WHERE SchoolID = ?
        """, school_name, school_type, state_code, region, contact_name, email, phone, school_id)

        conn.commit()
        conn.close()

        flash("School updated successfully.", "success")
        return redirect(url_for("schools"))

    cursor.execute("""
        SELECT SchoolID, SchoolName, SchoolType, StateCode, Region, ContactName, Email, Phone
        FROM Schools
        WHERE SchoolID = ?
    """, school_id)

    school = cursor.fetchone()
    conn.close()

    return render_template("school_form.html", school=school)


@app.route("/schools/delete/<int:school_id>", methods=["POST"])
def delete_school(school_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Schools WHERE SchoolID = ?", school_id)

    conn.commit()
    conn.close()

    flash("School deleted successfully.", "success")
    return redirect(url_for("schools"))


@app.route("/register-school", methods=["GET", "POST"])
def register_school():
    if request.method == "POST":
        school_name = request.form["school_name"]
        school_type = request.form["school_type"]
        state_code = request.form["state_code"]
        region = request.form["region"]
        contact_name = request.form["contact_name"]
        email = request.form["email"]
        phone = request.form["phone"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Schools
            (SchoolName, SchoolType, StateCode, Region, ContactName, Email, Phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, school_name, school_type, state_code, region, contact_name, email, phone)

        conn.commit()
        conn.close()

        flash("School registration submitted successfully.", "success")
        return redirect(url_for("index"))

    return render_template("register_school.html")


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
                SELECT COUNT(*)
                FROM Schools
                WHERE SchoolName = ?
                  AND StateCode = ?
            """, school_name, state_code)

            exists = cursor.fetchone()[0]

            if exists == 0:
                cursor.execute("""
                    INSERT INTO Schools
                    (SchoolName, SchoolType, StateCode, Region, ContactName, Email, Phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    school_name,
                    school_type,
                    state_code,
                    region,
                    contact_name,
                    email,
                    phone
                )

                inserted += 1

                if inserted % 50 == 0:
                    conn.commit()
            else:
                skipped += 1

        conn.commit()
        cursor.close()
        conn.close()

        flash(
            f"Upload completed. Processed: {len(df)}, inserted: {inserted}, skipped/already existed: {skipped}",
            "success"
        )

        return redirect(url_for("upload_schools"))

    return render_template("upload_schools.html")


@app.route("/competitions")
def competitions():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Competitions
        ORDER BY CompetitionID DESC
    """)

    competitions = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    conn.close()

    return render_template("competitions.html", competitions=competitions, columns=columns)


@app.route("/fixtures")
def fixtures():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Fixtures
        ORDER BY FixtureID DESC
    """)

    fixtures = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    conn.close()

    return render_template("fixtures.html", fixtures=fixtures, columns=columns)


@app.route("/players")
def players():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Players
        ORDER BY PlayerID DESC
    """)

    players = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    conn.close()

    return render_template("players.html", players=players, columns=columns)


@app.route("/results")
def results():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Results
        ORDER BY ResultID DESC
    """)

    results = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    conn.close()

    return render_template("results.html", results=results, columns=columns)


@app.route("/downloads")
def downloads():
    return render_template("downloads.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/<entity>")
def list_records(entity):
    if entity not in ENTITIES:
        return "Page not found", 404

    config = ENTITIES[entity]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT *
        FROM {config['table']}
        ORDER BY {config['order_by']}
    """)

    records = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    conn.close()

    return render_template(
        "list.html",
        entity=entity,
        config=config,
        records=records,
        columns=columns
    )

if __name__ == "__main__":
    app.run(debug=True)
