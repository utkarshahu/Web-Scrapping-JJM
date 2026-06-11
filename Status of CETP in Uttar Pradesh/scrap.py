import requests
import json
from bs4 import BeautifulSoup
import mysql.connector
from datetime import datetime
import time


url = "https://jjm.up.gov.in/NamamiGange/UnderConstruction_CETP"
USE_LOCAL_HTML = True

HTML_FILE = "under_construction_cetp.html"

def scrape_and_create_json():

    if USE_LOCAL_HTML:

        print("Reading Local HTML...")

        with open(
            HTML_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            html = f.read()

    else:

        print("Downloading Website...")

        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=60
        )

        response.raise_for_status()

        html = response.text

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    table = soup.find(
        "table",
        id="tableReportTable"
    )

    rows = table.find_all("tr")

    projects = []

    i = 2  # header rows skip

    while i < len(rows):

        cols = rows[i].find_all("td")

        if len(cols) < 19:
            i += 1
            continue

        rowspan = int(
            cols[0].get("rowspan", 1)
        )

        project = {
            "sr_no": cols[0].get_text(" ", strip=True),
            "project_name": cols[1].get_text(" ", strip=True),
            "nodal_agency": cols[2].get_text(" ", strip=True),
            "executive_agency": cols[3].get_text(" ", strip=True),
            "contractor": cols[4].get_text(" ", strip=True),
            "date_of_sanction": cols[5].get_text(" ", strip=True),
            "date_of_start": cols[6].get_text(" ", strip=True),
            "date_of_completion": cols[7].get_text(" ", strip=True),
            "sanction_cost_cr": cols[8].get_text(" ", strip=True),
            "agreement_cost_cr": cols[9].get_text(" ", strip=True),
            "physical_progress_percent": cols[10].get_text(" ", strip=True),
            "financial_progress_cr": cols[11].get_text(" ", strip=True),
            "date_of_updation": cols[17].get_text(" ", strip=True),
            "remarks": cols[18].get_text(" ", strip=True),
            "components": []
        }

        project["components"].append({
            "work_component": cols[12].get_text(" ", strip=True),
            "technology": cols[13].get_text(" ", strip=True),
            "capacity_length_no": cols[14].get_text(" ", strip=True),
            "physical_progress_percent": cols[15].get_text(" ", strip=True),
            "photos": cols[16].get_text(" ", strip=True)
        })

        for j in range(1, rowspan):

            if i + j >= len(rows):
                break

            sub_cols = rows[i + j].find_all("td")

            if len(sub_cols) < 5:
                continue

            project["components"].append({
                "work_component":
                    sub_cols[0].get_text(" ", strip=True),

                "technology":
                    sub_cols[1].get_text(" ", strip=True),

                "capacity_length_no":
                    sub_cols[2].get_text(" ", strip=True),

                "physical_progress_percent":
                    sub_cols[3].get_text(" ", strip=True),

                "photos":
                    sub_cols[4].get_text(" ", strip=True)
            })

        projects.append(project)

        i += rowspan

    with open(
            "under_construction_cetp.json",
            "w",
            encoding="utf-8"
    ) as f:

        json.dump(
            projects,
            f,
            indent=4,
            ensure_ascii=False
        )




conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Utkarshahu@18",
    database="status_of_cetp_up"
)

cur = conn.cursor()

def safe_float(value):

    if not value:
        return None

    value = str(value).replace("+", "").strip()

    try:
        return float(value)
    except:
        return None

def parse_date(value):

    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%d-%b-%Y"
        ).date()
    except:
        return None


with open(
    "under_construction_cetp.json",
    "r",
    encoding="utf-8"
) as f:

    projects = json.load(f)

agency_cache = {}

for project in projects:

    agency = project["nodal_agency"]

    # Insert Agency
    if agency not in agency_cache:

        cur.execute(
            """
            INSERT IGNORE INTO nodal_agencies
            (agency_name)
            VALUES (%s)
            """,
            (agency,)
        )

        conn.commit()

        cur.execute(
            """
            SELECT nodal_agency_id
            FROM nodal_agencies
            WHERE agency_name=%s
            """,
            (agency,)
        )

        agency_cache[agency] = cur.fetchone()[0]

    agency_id = agency_cache[agency]

    # Insert Project
    cur.execute(
        """
        INSERT INTO cetp_projects
        (
            project_name,
            nodal_agency_id,
            executive_agency,
            contractor_name,
            sanction_date,
            start_date,
            completion_date,
            sanction_cost_cr,
            agreement_cost_cr,
            physical_progress,
            financial_progress,
            update_date,
            remarks
        )
        VALUES
        (
            %s,%s,%s,%s,
            %s,%s,%s,
            %s,%s,%s,%s,
            %s,%s
        )
        """,
        (
            project["project_name"],
            agency_id,
            project["executive_agency"],
            project["contractor"],
            parse_date(project["date_of_sanction"]),
            parse_date(project["date_of_start"]),
            parse_date(project["date_of_completion"]),
            safe_float(project["sanction_cost_cr"]),
            safe_float(project["agreement_cost_cr"]),
            safe_float(project["physical_progress_percent"]),
            safe_float(project["financial_progress_cr"]),
            parse_date(project["date_of_updation"]),
            project["remarks"]
        )
    )

    project_id = cur.lastrowid

    # Insert Components
    for comp in project["components"]:

        if not any(comp.values()):
            continue

        cur.execute(
            """
            INSERT INTO project_components
            (
                project_id,
                work_component,
                technology,
                capacity_length_no,
                physical_progress,
                photos
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s
            )
            """,
            (
                project_id,
                comp["work_component"],
                comp["technology"],
                comp["capacity_length_no"],
                safe_float(
                    comp["physical_progress_percent"]
                ),
                comp["photos"]
            )
        )
conn.commit()
print("Data inserted successfully")
cur.close()
conn.close()


def backup_current_to_audit():

    main_conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Utkarshahu@18",
        database="status_of_cetp_up"
    )

    audit_conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Utkarshahu@18",
        database="audit_status_of_cetp_up"
    )

    main_cur = main_conn.cursor(dictionary=True)
    audit_cur = audit_conn.cursor()

    # Delete old audit snapshot
    audit_cur.execute(
        "SET FOREIGN_KEY_CHECKS=0"
    )

    audit_cur.execute(
        "TRUNCATE TABLE audit_project_components"
    )

    audit_cur.execute(
        "TRUNCATE TABLE audit_cetp_projects"
    )

    audit_cur.execute(
        "TRUNCATE TABLE audit_nodal_agencies"
    )

    audit_cur.execute(
        "SET FOREIGN_KEY_CHECKS=1"
    )

    agency_map = {}

    # Agencies
    main_cur.execute(
        "SELECT * FROM nodal_agencies"
    )

    for agency in main_cur.fetchall():

        audit_cur.execute(
            """
            INSERT INTO audit_nodal_agencies
            (agency_name)
            VALUES (%s)
            """,
            (
                agency["agency_name"],
            )
        )

        agency_map[
            agency["nodal_agency_id"]
        ] = audit_cur.lastrowid

    project_map = {}

    # Projects
    main_cur.execute(
        "SELECT * FROM cetp_projects"
    )

    for project in main_cur.fetchall():

        audit_cur.execute(
            """
            INSERT INTO audit_cetp_projects
            (
                audit_nodal_agency_id,
                project_name,
                executive_agency,
                contractor_name,
                sanction_date,
                start_date,
                completion_date,
                sanction_cost_cr,
                agreement_cost_cr,
                physical_progress,
                financial_progress,
                update_date,
                remarks,
                report_date,
                scrape_time
            )
            VALUES
            (
                %s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,
                %s,%s,
                %s,%s,
                CURDATE(),NOW()
            )
            """,
            (
                agency_map[
                    project["nodal_agency_id"]
                ],
                project["project_name"],
                project["executive_agency"],
                project["contractor_name"],
                project["sanction_date"],
                project["start_date"],
                project["completion_date"],
                project["sanction_cost_cr"],
                project["agreement_cost_cr"],
                project["physical_progress"],
                project["financial_progress"],
                project["update_date"],
                project["remarks"]
            )
        )

        project_map[
            project["project_id"]
        ] = audit_cur.lastrowid

    # Components
    main_cur.execute(
        "SELECT * FROM project_components"
    )

    for comp in main_cur.fetchall():

        audit_cur.execute(
            """
            INSERT INTO audit_project_components
            (
                audit_project_id,
                work_component,
                technology,
                capacity_length_no,
                physical_progress,
                photos
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s
            )
            """,
            (
                project_map[
                    comp["project_id"]
                ],
                comp["work_component"],
                comp["technology"],
                comp["capacity_length_no"],
                comp["physical_progress"],
                comp["photos"]
            )
        )

    audit_conn.commit()

    main_cur.close()
    audit_cur.close()

    main_conn.close()
    audit_conn.close()

    print(
        "Current -> Audit Completed"
    )


def clear_audit():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Utkarshahu@18",
        database="audit_status_of_cetp_up"
    )

    cur = conn.cursor()

    cur.execute(
        "SET FOREIGN_KEY_CHECKS=0"
    )

    cur.execute(
        "TRUNCATE TABLE audit_project_components"
    )

    cur.execute(
        "TRUNCATE TABLE audit_cetp_projects"
    )

    cur.execute(
        "TRUNCATE TABLE audit_nodal_agencies"
    )

    cur.execute(
        "SET FOREIGN_KEY_CHECKS=1"
    )

    conn.commit()

    cur.close()
    conn.close()

def clear_current():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Utkarshahu@18",
        database="status_of_cetp_up"
    )

    cur = conn.cursor()

    cur.execute(
        "SET FOREIGN_KEY_CHECKS=0"
    )

    cur.execute(
        "TRUNCATE TABLE project_components"
    )

    cur.execute(
        "TRUNCATE TABLE cetp_projects"
    )

    cur.execute(
        "TRUNCATE TABLE nodal_agencies"
    )

    cur.execute(
        "SET FOREIGN_KEY_CHECKS=1"
    )

    conn.commit()

    cur.close()
    conn.close()

from datetime import datetime

def parse_date(value):

    if not value:
        return None

    try:
        return datetime.strptime(
            value.strip(),
            "%d-%b-%Y"
        ).date()
    except:
        return None


def to_decimal(value):

    if not value:
        return 0

    value = str(value)

    value = value.replace("+0", "")
    value = value.replace(",", "")
    value = value.strip()

    try:
        return float(value)
    except:
        return 0


def save_to_mysql():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Utkarshahu@18",
        database="status_of_cetp_up"
    )

    cur = conn.cursor()

    with open(
        "under_construction_cetp.json",
        "r",
        encoding="utf-8"
    ) as f:

        projects = json.load(f)

    agency_cache = {}

    for project in projects:

        agency = project["nodal_agency"]

        # Agency Insert
        if agency not in agency_cache:

            cur.execute(
                """
                INSERT
                IGNORE INTO nodal_agencies
                (agency_name)
                VALUES (
                %s
                )
                """,
                (agency,)
            )

            cur.execute(
                """
                SELECT nodal_agency_id
                FROM nodal_agencies
                WHERE agency_name = %s
                """,
                (agency,)
            )

            result = cur.fetchone()

            if result is None:
                continue

            agency_cache[agency] = result[0]

        agency_id = agency_cache[agency]

        # Project Insert
        cur.execute(
            """
            INSERT INTO cetp_projects
            (project_name,
             nodal_agency_id,
             executive_agency,
             contractor_name,
             sanction_date,
             start_date,
             completion_date,
             sanction_cost_cr,
             agreement_cost_cr,
             physical_progress,
             financial_progress,
             update_date,
             remarks)
            VALUES (%s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s)
            """,
            (
                project["project_name"],
                agency_id,
                project["executive_agency"],
                project["contractor"],
                parse_date(project["date_of_sanction"]),
                parse_date(project["date_of_start"]),
                parse_date(project["date_of_completion"]),
                safe_float(project["sanction_cost_cr"]),
                safe_float(project["agreement_cost_cr"]),
                # FIX
                to_decimal(project["physical_progress_percent"]),
                to_decimal(project["financial_progress_cr"]),
                parse_date(project["date_of_updation"]),
                project["remarks"]
            )
        )

        project_id = cur.lastrowid

        # Components Insert
        for comp in project["components"]:

            if not any(comp.values()):
                continue

            cur.execute(
                """
                INSERT INTO project_components
                (project_id,
                 work_component,
                 technology,
                 capacity_length_no,
                 physical_progress,
                 photos)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    comp["work_component"],
                    comp["technology"],
                    comp["capacity_length_no"],
                    safe_float(
                        comp["physical_progress_percent"]
                    ),
                    comp["photos"]
                )
            )
    conn.commit()

    print("Current DB Updated")
    print("Data inserted successfully")

    cur.close()
    conn.close()
def run_scheduler():

    first_run = True

    while True:

        print("\nRunning Cycle...")

        scrape_and_create_json()

        if first_run:

            clear_current()
            save_to_mysql()

            first_run = False

        else:

            clear_audit()
            backup_current_to_audit()

            clear_current()
            save_to_mysql()

        print("Waiting 10 Seconds...")

        time.sleep(10)

if __name__ == "__main__":
    run_scheduler()