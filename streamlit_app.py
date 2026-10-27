"""Employee Payroll System - a small Python + FastAPI learning project."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
from typing import Optional

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from employee_storage import add_employee as save_employee, get_employees as load_employees, save_employees

import streamlit as st
st.set_page_config(
    page_title="Employee Payroll System",
    page_icon="💼",
    layout="wide",
)

app = FastAPI(
    title="Employee Payroll System",
    description="A simple payroll calculator built to practise Python concepts.",
    version="1.1.0",
)

# Employee details are persisted in employees.txt. These lists are used while the app runs.
employees = []
payroll_records = []  # Payroll history is still in memory for this learning version.
next_employee_id = 1
next_payroll_id = 1


def money(value) -> Decimal:
    """Convert a value to a 2-decimal-place Decimal safely."""
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a valid numeric amount.")
    if not amount.is_finite() or amount < 0:
        raise ValueError("Amounts must be valid, non-negative numbers.")
    return amount


class Employee:
    """Represent one employee."""
    def __init__(self, employee_id: int, name: str, department: str, role: str,
                 monthly_basic: Decimal, active: bool = True, joined_on: Optional[date] = None):
        self.employee_id = employee_id
        self.name = name.strip()
        self.department = department.strip()
        self.role = role.strip()
        self.monthly_basic = monthly_basic
        self.joined_on = joined_on or date.today()
        self.active = active


class PayrollCalculator:
    """Calculate sample monthly salary values."""
    def calculate(self, basic, allowances, bonus, deductions):
        basic, allowances, bonus, deductions = map(money, (basic, allowances, bonus, deductions))
        gross = basic + allowances + bonus
        if deductions > gross:
            raise ValueError("Deductions cannot be greater than gross salary.")
        return {
            "basic": basic,
            "allowances": allowances,
            "bonus": bonus,
            "gross": gross,
            "deductions": deductions,
            "net": gross - deductions,
        }


calculator = PayrollCalculator()


def employee_file_record(employee):
    return {
        "employee_id": employee.employee_id,
        "name": employee.name,
        "department": employee.department,
        "role": employee.role,
        "salary": str(employee.monthly_basic),
        "active": employee.active,
        "joined_on": employee.joined_on.isoformat(),
    }


def persist_employees():
    save_employees([employee_file_record(employee) for employee in employees])


def load_saved_employees():
    """Load employee details and their active status when the app starts."""
    global next_employee_id
    for record in load_employees():
        try:
            joined_on = date.fromisoformat(record["joined_on"]) if record.get("joined_on") else date.today()
            employee = Employee(
                record["employee_id"], record["name"], record["department"],
                record["role"], money(record["salary"]), record["active"], joined_on,
            )
            employees.append(employee)
        except (ValueError, TypeError, KeyError):
            continue
    if employees:
        next_employee_id = max(employee.employee_id for employee in employees) + 1


load_saved_employees()


def page(content: str, title: str = "Employee Payroll System") -> HTMLResponse:
    """Return a responsive HTML page."""
    return HTMLResponse(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#f3f6fb;color:#172033;font:15px Arial,sans-serif}}
header{{background:#173b67;color:white;padding:22px max(20px,calc((100% - 1080px)/2))}} header h1{{margin:0 0 8px;font-size:25px}}
nav{{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px}} nav a{{color:#dceaff;text-decoration:none}}
main{{max-width:1080px;margin:26px auto;padding:0 18px}} .card{{background:white;border:1px solid #e1e7f0;border-radius:12px;padding:20px;margin-bottom:18px;box-shadow:0 3px 12px #17203308}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}} label{{display:block;font-weight:600;margin:10px 0 5px}}
input,select{{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:7px;font:inherit}}
button,.button{{display:inline-block;border:0;border-radius:7px;padding:9px 12px;background:#1765b3;color:white;font-weight:600;text-decoration:none;cursor:pointer;margin:3px}}
button.secondary{{background:#64748b}} .muted{{color:#64748b}} .stats{{font-size:25px;font-weight:700;margin-top:8px}} .message{{padding:12px;background:#fff7df;border-radius:8px}}
table{{border-collapse:collapse;width:100%;margin-top:12px}} th,td{{padding:10px;text-align:left;border-bottom:1px solid #e2e8f0}} th{{background:#f8fafc}}
.table-wrap{{overflow-x:auto}} .status-active{{color:#166534;font-weight:700}} .status-inactive{{color:#9f1239;font-weight:700}}
footer{{text-align:center;color:#64748b;padding:20px}} @media(max-width:600px){{header h1{{font-size:21px}}th,td{{padding:8px;font-size:13px}}}}
</style></head><body><header><h1>Employee Payroll System</h1>
<div>Employee management · FastAPI · Payroll calculator</div><nav>
<a href="/">Dashboard</a><a href="/employees">Employees</a><a href="/employees/new">Add Employee</a>
<a href="/payroll/new">Calculate Payroll</a><a href="/payroll/history">Payroll History</a><a href="/docs">API Docs</a>
</nav></header><main>{content}</main>
<footer>Employee details and status are saved in employees.txt. Payroll history resets when the server restarts.</footer></body></html>''')


def employee_by_id(employee_id: int) -> Optional[Employee]:
    for employee in employees:
        if employee.employee_id == employee_id:
            return employee
    return None


@app.get("/", response_class=HTMLResponse)
def dashboard():
    active_count = sum(1 for employee in employees if employee.active)
    inactive_count = len(employees) - active_count
    total_net = sum((record["net"] for record in payroll_records), Decimal("0.00"))
    recent = sorted(payroll_records, key=lambda item: item["created_at"], reverse=True)[:5]
    recent_rows = "".join(
        f"<tr><td>{r['payroll_id']}</td><td>{escape(r['employee_name'])}</td><td>{escape(r['month'])}</td><td>₹{r['net']:.2f}</td></tr>"
        for r in recent
    )
    if not recent_rows:
        recent_rows = '<tr><td colspan="4" class="muted">No payroll records yet. Calculate a payroll to see it here.</td></tr>'
    return page(f'''<section class="grid">
<div class="card"><div class="muted">Active employees</div><div class="stats">{active_count}</div></div>
<div class="card"><div class="muted">Inactive employees</div><div class="stats">{inactive_count}</div></div>
<div class="card"><div class="muted">Payroll calculations this session</div><div class="stats">{len(payroll_records)}</div></div>
<div class="card"><div class="muted">Total net pay calculated</div><div class="stats">₹{total_net:.2f}</div></div></section>
<section class="card"><h2>Welcome</h2><p>A Python and FastAPI learning application for employee records and monthly salary calculations.</p>
<p class="message">Employee information is saved in employees.txt. Payroll history remains in memory for the future work. </p>
<a class="button" href="/employees/new">+ Add Employee</a><a class="button" href="/employees">Manage Employees</a><a class="button" href="/payroll/new">Calculate Payroll</a></section>
<section class="card"><h2>Recent payroll calculations</h2><div class="table-wrap"><table><thead><tr><th>ID</th><th>Employee</th><th>Month</th><th>Net salary</th></tr></thead><tbody>{recent_rows}</tbody></table></div></section>''')


@app.get("/employees", response_class=HTMLResponse)
def list_employees():
    rows = []
    for employee in employees:
        status = "Active" if employee.active else "Inactive"
        status_class = "status-active" if employee.active else "status-inactive"
        action = "Deactivate" if employee.active else "Reactivate"
        button_class = "" if employee.active else "secondary"
        rows.append(f'''<tr><td>{employee.employee_id}</td><td>{escape(employee.name)}</td>
<td>{escape(employee.department)}</td><td>{escape(employee.role)}</td><td>₹{employee.monthly_basic:.2f}</td>
<td>{employee.joined_on.isoformat()}</td><td class="{status_class}">{status}</td><td>
<form method="post" action="/employees/{employee.employee_id}/toggle-status" onsubmit="return confirm('Change this employee status?');">
<button class="{button_class}" type="submit">{action}</button></form></td></tr>''')
    if not rows:
        row_html = '<tr><td colspan="8" class="muted">No employees yet. Add your first employee.</td></tr>'
    else:
        row_html = "".join(rows)
    return page(f'''<section class="card"><h2>Employee Directory</h2>
<p class="muted">Employee details and status are saved in employees.txt. Inactive employees are retained, not deleted.</p>
<a class="button" href="/employees/new">+ Add Employee</a><div class="table-wrap"><table>
<thead><tr><th>ID</th><th>Name</th><th>Department</th><th>Role</th><th>Basic salary</th><th>Joined</th><th>Status</th><th>Action</th></tr></thead>
<tbody>{row_html}</tbody></table></div></section>''')


@app.get("/employees/new", response_class=HTMLResponse)
def new_employee_form():
    return page('''<section class="card"><h2>Add Employee</h2><form method="post" action="/employees"><div class="grid">
<div><label>Full name *</label><input name="name" required maxlength="80" placeholder="e.g. Ravi Kumar"></div>
<div><label>Department *</label><input name="department" required maxlength="60" placeholder="e.g. Finance"></div>
<div><label>Job role *</label><input name="role" required maxlength="60" placeholder="e.g. Junior Analyst"></div>
<div><label>Monthly basic salary (₹) *</label><input name="monthly_basic" type="number" min="0" step="0.01" required placeholder="25000"></div>
</div><button type="submit">Save Employee</button></form></section>''')


@app.post("/employees")
def add_employee(name: str = Form(...), department: str = Form(...), role: str = Form(...), monthly_basic: str = Form(...)):
    global next_employee_id
    name, department, role = name.strip(), department.strip(), role.strip()
    if not name or not department or not role:
        raise HTTPException(status_code=400, detail="Name, department and role are required.")
    if any(e.name.casefold() == name.casefold() and e.active for e in employees):
        return page('<section class="card"><h2>Employee not added</h2><p class="message">An active employee with this name already exists in this demo.</p><a class="button" href="/employees/new">Go back</a></section>')
    try:
        basic = money(monthly_basic)
    except ValueError as exc:
        return page(f'<section class="card"><h2>Invalid salary</h2><p class="message">{escape(str(exc))}</p><a class="button" href="/employees/new">Go back</a></section>')
    employee = Employee(next_employee_id, name, department, role, basic)
    employees.append(employee)
    # Save the full employee list, including status and joining date.
    persist_employees()
    next_employee_id += 1
    return RedirectResponse("/employees", status_code=303)


@app.post("/employees/{employee_id}/toggle-status")
def toggle_employee_status(employee_id: int):
    employee = employee_by_id(employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    employee.active = not employee.active
    persist_employees()
    return RedirectResponse("/employees", status_code=303)


@app.get("/payroll/new", response_class=HTMLResponse)
def payroll_form():
    active_employees = [employee for employee in employees if employee.active]
    if not active_employees:
        return page('<section class="card"><h2>Calculate Payroll</h2><p class="message">There are no active employees. Add or reactivate an employee before calculating payroll.</p><a class="button" href="/employees">Manage Employees</a></section>')
    options = "".join(f'<option value="{e.employee_id}">{e.employee_id} - {escape(e.name)} (₹{e.monthly_basic:.2f} basic)</option>' for e in active_employees)
    current_month = date.today().strftime("%Y-%m")
    return page(f'''<section class="card"><h2>Payroll Calculator</h2><p class="muted">Only active employees can be selected.</p>
<form method="post" action="/payroll"><label>Employee *</label><select name="employee_id" required>{options}</select><div class="grid">
<div><label>Payroll month *</label><input type="month" name="month" value="{current_month}" required></div>
<div><label>Allowances (₹)</label><input type="number" name="allowances" min="0" step="0.01" value="0" required></div>
<div><label>Bonus (₹)</label><input type="number" name="bonus" min="0" step="0.01" value="0" required></div>
<div><label>Deductions (₹)</label><input type="number" name="deductions" min="0" step="0.01" value="0" required></div>
</div><button type="submit">Calculate and Save</button></form></section>''')


@app.post("/payroll", response_class=HTMLResponse)
def calculate_payroll(employee_id: int = Form(...), month: str = Form(...), allowances: str = Form("0"), bonus: str = Form("0"), deductions: str = Form("0")):
    global next_payroll_id
    employee = employee_by_id(employee_id)
    if employee is None or not employee.active:
        return page('<section class="card"><h2>Unable to calculate payroll</h2><p class="message">Choose an active employee. Inactive employees cannot be used for new payroll calculations.</p><a class="button" href="/payroll/new">Try again</a></section>')
    try:
        datetime.strptime(month, "%Y-%m")
        result = calculator.calculate(employee.monthly_basic, allowances, bonus, deductions)
    except (ValueError, TypeError) as exc:
        return page(f'<section class="card"><h2>Check your inputs</h2><p class="message">{escape(str(exc))}</p><a class="button" href="/payroll/new">Try again</a></section>')
    record = {"payroll_id": next_payroll_id, "employee_id": employee.employee_id, "employee_name": employee.name,
              "department": employee.department, "role": employee.role, "month": month, **result, "created_at": datetime.now()}
    payroll_records.append(record)
    next_payroll_id += 1
    rows = "".join(f'<tr><th>{escape(label)}</th><td>₹{result[key]:.2f}</td></tr>' for label, key in [
        ("Basic salary", "basic"), ("Allowances", "allowances"), ("Bonus", "bonus"),
        ("Gross salary", "gross"), ("Deductions", "deductions"), ("Net salary", "net")])
    return page(f'''<section class="card"><h2>Payroll Calculated Successfully</h2><p><strong>Employee:</strong> {escape(employee.name)} &nbsp; <strong>Month:</strong> {escape(month)}</p>
<div class="table-wrap"><table><tbody>{rows}</tbody></table></div><p class="message">Net salary: <strong>₹{result['net']:.2f}</strong></p>
<a class="button" href="/payroll/new">Calculate another</a> <a class="button" href="/payroll/history">View history</a></section>''')


@app.get("/payroll/history", response_class=HTMLResponse)
def payroll_history():
    rows = "".join(f'''<tr><td>{r['payroll_id']}</td><td>{escape(r['employee_name'])}</td><td>{escape(r['department'])}</td>
<td>{escape(r['month'])}</td><td>₹{r['gross']:.2f}</td><td>₹{r['deductions']:.2f}</td><td><strong>₹{r['net']:.2f}</strong></td>
<td>{r['created_at'].strftime('%d %b %Y %H:%M')}</td></tr>''' for r in reversed(payroll_records))
    if not rows:
        rows = '<tr><td colspan="8" class="muted">No payroll calculations saved yet.</td></tr>'
    return page(f'''<section class="card"><h2>Payroll History</h2><p class="muted">Shows calculations created during this server session.</p>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Employee</th><th>Department</th><th>Month</th><th>Gross</th><th>Deductions</th><th>Net pay</th><th>Created</th></tr></thead><tbody>{rows}</tbody></table></div></section>''')


@app.get("/api/employees")
def api_employees():
    """Return employee data, including each employee's active status."""
    return [{"id": e.employee_id, "name": e.name, "department": e.department, "role": e.role,
             "monthly_basic": str(e.monthly_basic), "joined_on": e.joined_on.isoformat(), "active": e.active}
            for e in employees]


@app.get("/api/payroll/history")
def api_payroll_history():
    return [{"payroll_id": r["payroll_id"], "employee_name": r["employee_name"], "month": r["month"],
             "basic": str(r["basic"]), "allowances": str(r["allowances"]), "bonus": str(r["bonus"]),
             "gross": str(r["gross"]), "deductions": str(r["deductions"]), "net": str(r["net"]),
             "created_at": r["created_at"].isoformat(timespec="seconds")} for r in payroll_records]
