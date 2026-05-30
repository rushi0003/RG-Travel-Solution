
import sqlite3

def check_db():
    conn = sqlite3.connect('rg_travel.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    trip_day = '20260219'
    absence_date = '2026-02-19'
    time_val = '09:00'
    
    print(f"--- DIAGNOSING ELIGIBILITY FOR {trip_day} AT {time_val} ---")
    
    cur.execute("SELECT id, name, login_time, is_active FROM employees")
    employees = cur.fetchall()
    print(f"Total employees in DB: {len(employees)}")
    
    for e in employees:
        e_id = e['id']
        name = e['name']
        login = e['login_time']
        active = e['is_active']
        
        # Check Busy
        cur.execute("""
            SELECT 1 FROM trip_employees te 
            JOIN trips t ON t.id = te.trip_id
            WHERE CAST(te.employee_id AS TEXT) = ? AND t.trip_day = ?
              AND t.status IN ('created', 'assigned', 'started', 'active')
        """, (str(e_id), trip_day))
        busy = cur.fetchone() is not None
        
        # Check Absent
        cur.execute("""
            SELECT 1 FROM employee_absences 
            WHERE CAST(employee_id AS TEXT) = ? AND absence_date = ? AND status = 'approved'
        """, (str(e_id), absence_date))
        absent = cur.fetchone() is not None
        
        eligible = (login == time_val) and (active == 1) and not busy and not absent
        
        print(f"ID={e_id} Name={name} Login={login} Active={active} Busy={busy} Absent={absent} -> ELIGIBLE={eligible}")

    conn.close()

if __name__ == "__main__":
    check_db()
