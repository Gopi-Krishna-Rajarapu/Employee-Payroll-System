from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import streamlit as st
from employee_storage import get_employees, save_employees

st.set_page_config(page_title="Employee Payroll System", page_icon="💼", layout="wide")


def money(value):
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Enter a valid amount.")
    if not result.is_finite() or result < 0:
        raise ValueError("Amounts must be non-negative valid numbers.")
    return result


def load_employees():
    result = []
    for row in get_employees():
        try:
            result.append({
                "employee_id": int(row["employee_id"]),
                "name": str(row["name"]),
                "department": str(row["department"]),
                "role": str(row["role"]),
                "salary": str(money(row["salary"])),
                "active": str(row.get("active", True)).lower() == "true",
                "joined_on": row.get("joined_on") or date.today().isoformat(),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return result


def save_all():
    save_employees(st.session_state.employees)


if "employees" not in st.session_state:
    st.session_state.employees = load_employees()
if "payroll" not in st.session_state:
    st.session_state.payroll = []
if "next_payroll_id" not in st.session_state:
    st.session_state.next_payroll_id = 1

employees = st.session_state.employees
active = sum(e["active"] for e in employees)
inactive = len(employees) - active

st.title("💼 Employee Payroll System")
st.caption("Employee management • Active/Inactive status • Monthly payroll")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Employees", "Add Employee", "Calculate Payroll", "Payroll History"],
)
st.sidebar.info("Employee data uses employees.txt. Payroll history is session-only.")


def display_rows(rows):
    return [{
        "ID": e["employee_id"],
        "Name": e["name"],
        "Department": e["department"],
        "Role": e["role"],
        "Basic salary (₹)": f'{money(e["salary"]):,.2f}',
        "Joined on": e["joined_on"],
        "Status": "Active" if e["active"] else "Inactive",
    } for e in rows]


if page == "Dashboard":
    st.subheader("Dashboard")
    a, b, c, d = st.columns(4)
    a.metric("Total employees", len(employees))
    b.metric("Active employees", active)
    c.metric("Inactive employees", inactive)
    d.metric("Payroll calculations this session", len(st.session_state.payroll))
    total_net = sum((r["net"] for r in st.session_state.payroll), Decimal("0.00"))
    st.metric("Total net pay this session", f"₹{total_net:,.2f}")
    st.info("Employee details are saved to employees.txt. Payroll history resets when the app session restarts.")
    st.markdown("### Recent payroll")
    if st.session_state.payroll:
        st.dataframe([{
            "Payroll ID": r["payroll_id"], "Employee": r["employee_name"],
            "Month": r["month"], "Gross (₹)": f'{r["gross"]:,.2f}',
            "Net (₹)": f'{r["net"]:,.2f}'
        } for r in reversed(st.session_state.payroll[-5:])], use_container_width=True, hide_index=True)
    else:
        st.write("No payroll calculations yet.")


elif page == "Employees":
