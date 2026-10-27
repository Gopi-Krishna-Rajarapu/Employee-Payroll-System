"""Simple CSV-based employee storage for the learning project."""
import csv
from pathlib import Path

EMPLOYEE_FILE = Path(__file__).with_name("employees.txt")
FIELDS = ["employee_id", "name", "department", "role", "salary", "active", "joined_on"]


def get_employees():
    """Read employee records from employees.txt."""
    if not EMPLOYEE_FILE.exists():
        return []

    records = []
    with EMPLOYEE_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, fieldnames=FIELDS)
        for row in reader:
            try:
                records.append({
                    "employee_id": int(row["employee_id"]),
                    "name": row["name"],
                    "department": row["department"],
                    "role": row["role"],
                    "salary": row["salary"],
                    # Older five-column records default to Active and today's date.
                    "active": (row.get("active") or "true").strip().lower() == "true",
                    "joined_on": row.get("joined_on") or "",
                })
            except (KeyError, TypeError, ValueError, AttributeError):
                # Ignore malformed lines instead of stopping the whole app.
                continue
    return records


def save_employees(employees):
    """Rewrite the file with the current employee list and statuses."""
    with EMPLOYEE_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        for employee in employees:
            writer.writerow({
                "employee_id": employee["employee_id"],
                "name": employee["name"],
                "department": employee["department"],
                "role": employee["role"],
                "salary": employee["salary"],
                "active": employee["active"],
                "joined_on": employee["joined_on"],
            })


def add_employee(employee_id, name, department, role, salary, active=True, joined_on=None):
    """Append one employee record to the file."""
    existing = get_employees()
    existing.append({
        "employee_id": employee_id,
        "name": name,
        "department": department,
        "role": role,
        "salary": str(salary),
        "active": active,
        "joined_on": joined_on or "",
    })
    save_employees(existing)
