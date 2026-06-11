from flask import Flask, render_template, jsonify
import mysql.connector
from dotenv import load_dotenv
import os
import subprocess
import sys

load_dotenv()

app = Flask(__name__)

# =====================================================
# DATABASE CONFIG
# =====================================================

MAIN_DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("MAIN_DB_NAME")
}

AUDIT_DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("AUDIT_DB_NAME")
}


# =====================================================
# CONNECTIONS
# =====================================================

def get_main_connection():
    return mysql.connector.connect(
        **MAIN_DB_CONFIG
    )


def get_audit_connection():
    return mysql.connector.connect(
        **AUDIT_DB_CONFIG
    )


# =====================================================
# HOME
# =====================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =====================================================
# CURRENT DATA
# =====================================================


@app.route("/api/current")
def current_data():

    try:

        conn = get_main_connection()

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT

            p.project_id,
            p.project_name,

            n.agency_name AS nodal_agency,

            p.executive_agency,
            p.contractor_name,

            p.sanction_date,
            p.start_date,
            p.completion_date,

            p.sanction_cost_cr,
            p.agreement_cost_cr,

            p.physical_progress,
            p.financial_progress,

            p.update_date,
            p.remarks,

            pc.work_component,
            pc.technology,
            pc.capacity_length_no,
            pc.physical_progress AS component_progress,
            pc.photos

        FROM cetp_projects p

        INNER JOIN nodal_agencies n
            ON p.nodal_agency_id = n.nodal_agency_id

        LEFT JOIN project_components pc
            ON p.project_id = pc.project_id

        ORDER BY
            p.project_id,
            pc.component_id
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        projects = {}

        for row in rows:

            pid = row["project_id"]

            if pid not in projects:

                projects[pid] = {

                    "project_id":
                        pid,

                    "project_name":
                        row["project_name"],

                    "nodal_agency":
                        row["nodal_agency"],

                    "executive_agency":
                        row["executive_agency"],

                    "contractor":
                        row["contractor_name"],

                    "date_of_sanction":
                        str(row["sanction_date"] or ""),

                    "date_of_start":
                        str(row["start_date"] or ""),

                    "date_of_completion":
                        str(row["completion_date"] or ""),

                    "sanction_cost_cr":
                        row["sanction_cost_cr"],

                    "agreement_cost_cr":
                        row["agreement_cost_cr"],

                    "physical_progress_percent":
                        row["physical_progress"],

                    "financial_progress_cr":
                        row["financial_progress"],

                    "date_of_updation":
                        str(row["update_date"] or ""),

                    "remarks":
                        row["remarks"],

                    "components": []
                }

            if row["work_component"]:

                projects[pid]["components"].append({

                    "work_component":
                        row["work_component"],

                    "technology":
                        row["technology"],

                    "capacity_length_no":
                        row["capacity_length_no"],

                    "physical_progress_percent":
                        row["component_progress"],

                    "photos":
                        row["photos"]
                })

        return jsonify(
            list(projects.values())
        )

    except Exception as e:

        print(e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# =====================================================
# AUDIT DATA
# =====================================================

@app.route("/api/audit")
def audit_data():

    try:

        conn = get_audit_connection()

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT

            p.audit_project_id,

            p.project_name,

            n.agency_name AS nodal_agency,

            p.executive_agency,
            p.contractor_name,

            p.sanction_date,
            p.start_date,
            p.completion_date,

            p.sanction_cost_cr,
            p.agreement_cost_cr,

            p.physical_progress,
            p.financial_progress,

            p.update_date,
            p.remarks,

            pc.work_component,
            pc.technology,
            pc.capacity_length_no,

            pc.physical_progress AS component_progress,

            pc.photos,

            p.scrape_time

        FROM audit_cetp_projects p

        INNER JOIN audit_nodal_agencies n
            ON p.audit_nodal_agency_id =
               n.audit_nodal_agency_id

        LEFT JOIN audit_project_components pc
            ON p.audit_project_id =
               pc.audit_project_id

        ORDER BY p.project_name
        """)

        data = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(data)

    except Exception as e:

        print("AUDIT ERROR:", e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/fetch-now", methods=["POST"])
def fetch_now():

    try:

        result = subprocess.run(
            [
                sys.executable,
                "manual_refresh.py"
            ],
            capture_output=True,
            text=True
        )

        print(result.stdout)
        print(result.stderr)

        if result.returncode != 0:

            return jsonify({
                "success": False,
                "message": result.stderr
            }), 500

        return jsonify({
            "success": True,
            "message": "Data Updated Successfully"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

# =====================================================
# STATS
# =====================================================

@app.route("/api/stats")
def stats():

    try:

        conn = get_main_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM cetp_projects
        """)
        projects = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM nodal_agencies
        """)
        agencies = cursor.fetchone()[0]

        cursor.execute("""
            SELECT MAX(update_date)
            FROM cetp_projects
        """)
        last_update = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return jsonify({
            "projects": projects,
            "agencies": agencies,
            "last_update": str(last_update)
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# =====================================================
# FAVICON
# =====================================================

@app.route("/favicon.ico")
def favicon():

    return "", 204

@app.route("/test-db")
def test_db():

    try:

        conn = get_main_connection()

        cursor = conn.cursor()

        cursor.execute("SHOW TABLES")

        data = cursor.fetchall()

        return jsonify(data)

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

# =====================================================
# ERROR HANDLER
# =====================================================

@app.errorhandler(Exception)
def handle_error(error):

    return jsonify({
        "status": "error",
        "message": str(error)
    }), 500


# =====================================================
# START APP
# =====================================================

if __name__ == "__main__":

    print("Starting Flask Server...")
    print("MAIN DB :", MAIN_DB_CONFIG["database"])
    print("AUDIT DB :", AUDIT_DB_CONFIG["database"])

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )