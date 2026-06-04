from flask import Flask, render_template, request, redirect, url_for, flash, abort
from db import get_connection
from werkzeug.utils import secure_filename

import os
import pandas as pd


# =========================================================
# FLASK APP CONFIGURATION
# =========================================================

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "school-soccer-secret")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================================================
# FIFA / REGISTRY HIERARCHY CONFIGURATION
# World -> Confederations -> Countries -> States/Provinces
# -> Regions -> Associations -> Clubs -> Teams -> Players
# =========================================================

ENTITIES = {
    "worlds": {
        "label": "Worlds",
        "table": "Worlds",
        "pk": "WorldID",
        "fields": ["WorldName", "Description"],
        "order_by": "WorldID DESC",
    },
    "confederations": {
        "label": "Confederations",
        "table": "Confederations",
        "pk": "ConfederationID",
        "fields": ["WorldID", "ConfederationCode", "ConfederationName", "Headquarters"],
        "order_by": "ConfederationID DESC",
    },
    "countries": {
        "label": "Countries",
        "table": "Countries",
        "pk": "CountryID",
        "fields": ["ConfederationID", "CountryName", "FIFACountryCode", "ISO2Code", "ISO3Code"],
        "order_by": "CountryID DESC",
    },
    "states": {
        "label": "States / Provinces",
        "table": "StatesProvinces",
        "pk": "StateProvinceID",
        "fields": ["CountryID", "StateProvinceName", "StateProvinceCode"],
        "order_by": "StateProvinceID DESC",
    },
    "regions": {
        "label": "Regions",
        "table": "Regions",
        "pk": "RegionID",
        "fields": ["StateProvinceID", "RegionName"],
        "order_by": "RegionID DESC",
    },
    "associations": {
        "label": "Associations",
        "table": "Associations",
        "pk": "AssociationID",
        "fields": ["RegionID", "AssociationName", "AssociationCode", "AssociationType"],
        "order_by": "AssociationID DESC",
    },
    "clubs": {
        "label": "Clubs",
        "table": "Clubs",
        "pk": "ClubID",
        "fields": ["AssociationID", "ClubName", "ClubCode", "FoundedYear", "HomeGround"],
        "order_by": "ClubID DESC",
    },
    "teams": {
        "label": "Teams",
        "table": "Teams",
        "pk": "TeamID",
        "fields": ["ClubID", "TeamName", "AgeGroup", "Gender", "Division", "SeasonYear"],
        "order_by": "TeamID DESC",
    },
    "players": {
        "label": "Players",
        "table": "Players",
        "pk": "PlayerID",
        "fields": [
            "TeamID",
            "FIFAConnectID",
            "FirstName",
            "LastName",
            "DateOfBirth",
            "Gender",
            "Nationality",
            "PreferredPosition",
            "ShirtNumber",
            "RegistrationStatus",
        ],
        "order_by": "PlayerID DESC",
    },
}


SCHOOL_MODULES = {
    "schools": {
        "label": "Schools",
        "table": "Schools",
        "url": "schools",
    },
    "competitions": {
        "label": "Competitions",
        "table": "Competitions",
        "url": "competitions",
    },
    "fixtures": {
        "label": "Fixtures",
        "table": "Fixtures",
        "url": "fixtures",
    },
    "results": {
        "label": "Results",
        "table": "Results",
        "url": "results",
    },
}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def fetch_count(table_name):
    """Return count from a table. If the table does not exist yet, return 0."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def fetch_all_from_table(table_name, order_by=None):
    conn = get_connection()
    cursor = conn.cursor()

    sql = f"SELECT * FROM {table_name}"
    if order_by:
        sql += f" ORDER BY {order_by}"

    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    conn.close()
    return rows, columns


# =========================================================
# HOME / DASHBOARD
# =========================================================

@app.route("/")
def index():
    return redirect(url_for("admin_dashboard"))


@app.route("/admin")
def admin_dashboard():
    fifa_cards = []

    for key, config in ENTITIES.items():
        fifa_cards.append({
            "key": key,
            "label": config["label"],
            "table": config["table"],
            "count": fetch_count(config["table"]),
            "url": url_for("list_records", entity=key),
        })

    school_cards = []

    for key, config in SCHOOL_MODULES.items():
        school_cards.append({
            "key": key,
            "label": config["label"],
            "table": config["table"],
            "count": fetch_count(config["table"]),
            "url": url_for(config["url"]),
        })

    return render_template(
        "admin_dashboard.html",
        fifa_cards=fifa_cards,
        school_cards=school_cards,
        entities=ENTITIES,
    )


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


# =========================================================
# FIFA / REGISTRY GENERIC CRUD ROUTES
# =========================================================

@app.route("/<entity>")
def list_records(entity):
    if entity not in ENTITIES:
        abort(404)

    config = ENTITIES[entity]
    records, columns = fetch_all_from_table(config["table"], config.get("order_by"))

    return render_template(
        "list.html",
        entity=entity,
        config=config,
        columns=columns,
        records=records,
        entities=ENTITIES,
    )


@app.route("/<entity>/create", methods=["GET", "POST"])
def create_record(entity):
    if entity not in ENTITIES:
        abort(404)

    config = ENTITIES[entity]

    if request.method == "POST":
        fields = config["fields"]
        values = [request.form.get(field) or None for field in fields]

        placeholders = ", ".join(["?"] * len(fields))
        field_list = ", ".join(fields)

        sql = f"""
            INSERT INTO {config['table']} ({field_list})
            VALUES ({placeholders})
        """

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        conn.close()

        flash(f"{config['label']} record created successfully.", "success")
        return redirect(url_for("list_records", entity=entity))

    return render_template(
        "form.html",
        entity=entity,
        config=config,
        record=None,
        action="Create",
        entities=ENTITIES,
    )


@app.route("/<entity>/edit/<int:record_id>", methods=["GET", "POST"])
def edit_record(entity, record_id):
    if entity not in ENTITIES:
        abort(404)

    config = ENTITIES[entity]
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        fields = config["fields"]
        values = [request.form.get(field) or None for field in fields]

        set_clause = ", ".join([f"{field}=?" for field in fields])
        values.append(record_id)

        sql = f"""
            UPDATE {config['table']}
            SET {set_clause}
            WHERE {config['pk']}=?
        """

        cursor.execute(sql, values)
        conn.commit()
        conn.close()

        flash(f"{config['label']} record updated successfully.", "success")
        return redirect(url_for("list_records", entity=entity))

    sql = f"SELECT * FROM {config['table']} WHERE {config['pk']}=?"
    cursor.execute(sql, record_id)

    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()

    record = dict(zip(columns, row)) if row else None
    conn.close()

    return render_template(
        "form.html",
        entity=entity,
        config=config,
        record=record,
        action="Edit",
        entities=ENTITIES,
    )


@app.route("/<entity>/delete/<int:record_id>", methods=["POST", "GET"])
def delete_record(entity, record_id):
    if entity not in ENTITIES:
        abort(404)

    config = ENTITIES[entity]

    conn = get_connection()
    cursor = conn.cursor()

    sql = f"DELETE FROM {config['table']} WHERE {config['pk']}=?"
    cursor.execute(sql, record_id)

    conn.commit()
    conn.close()

    flash(f"{config['label']} record deleted successfully.", "danger")
    return redirect(url_for("list_records", entity=entity))


@app.route("/hierarchy")
def hierarchy():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vw_FIFA_PlayerHierarchy")
    records = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    conn.close()

    return render_template(
        "list.html",
        entity="hierarchy",
        config={
            "label": "Full FIFA Player Hierarchy",
            "pk": "PlayerID",
            "fields": [],
        },
        columns=columns,
        records=records,
        entities=ENTITIES,
    )


# =========================================================
# SCHOOL COMPETITION ROUTES
# =========================================================

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

    return render_template("schools.html", schools=schools, entities=ENTITIES)


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

    return render_template("school_form.html", school=None, entities=ENTITIES)


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

    return render_template("school_form.html", school=school, entities=ENTITIES)


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
        return redirect(url_for("admin_dashboard"))

    return render_template("register_school.html", entities=ENTITIES)


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
            "Phone",
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
                """,
                    school_name,
                    school_type,
                    state_code,
                    region,
                    contact_name,
                    email,
                    phone,
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
            "success",
        )

        return redirect(url_for("upload_schools"))

    return render_template("upload_schools.html", entities=ENTITIES)


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

    return render_template(
        "competitions.html",
        competitions=competitions,
        columns=columns,
        entities=ENTITIES,
    )


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

    return render_template(
        "fixtures.html",
        fixtures=fixtures,
        columns=columns,
        entities=ENTITIES,
    )


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

    return render_template(
        "results.html",
        results=results,
        columns=columns,
        entities=ENTITIES,
    )


# =========================================================
# STATIC CONTENT ROUTES
# =========================================================

@app.route("/downloads")
def downloads():
    return render_template("downloads.html", entities=ENTITIES)


@app.route("/contact")
def contact():
    return render_template("contact.html", entities=ENTITIES)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)
