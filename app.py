from flask import Flask, render_template, request, redirect, session, url_for, flash, Response
import mysql.connector
import os

app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecretkey123"

app.permanent_session_lifetime = 3600

app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False
)

# ================= DATABASE =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Knpfae@v327dt",
        database="student_db"
    )

# ================= HOME =================
@app.route('/')
def home():
    return render_template('index.html')

# ================= LOGIN (FIXED CORE ISSUE) =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)

        cursor.execute(
            "SELECT username, password, role FROM users WHERE username=%s",
            (username,)
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and user[1] == password:

            session.clear()
            session.permanent = True

            role = user[2].strip().lower()   # 🔥 FIX MOST IMPORTANT

            session['user'] = user[0]
            session['role'] = role

            flash("Login successful!", "success")

            if role == "admin":
                return redirect(url_for('dashboard'))
            elif role == "student":
                return redirect(url_for('student_dashboard'))
            elif role == "teacher":
                return redirect(url_for('teacher_dashboard'))
            else:
                flash("Invalid role in database", "danger")
                return redirect(url_for('login'))

        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'].strip().lower()

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)

        try:
            cursor.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, %s)
            """, (username, password, role))

            conn.commit()
            flash("Registration successful! Please login", "success")

        except:
            flash("Username already exists", "danger")

        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# ================= DASHBOARDS =================
@app.route('/student_dashboard')
def student_dashboard():
    if 'user' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    return render_template("student_dashboard.html")

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    return render_template("teacher_dashboard.html")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE marks >= 40")
    pass_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE marks < 40")
    fail_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT id, name, roll, dept, marks 
        FROM students 
        ORDER BY id DESC 
        LIMIT 5
    """)
    recent_students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        pass_count=pass_count,
        fail_count=fail_count,
        recent_students=recent_students
    )

# ================= VIEW =================
@app.route('/view')
def view_students():
    if session.get('role') not in ['admin', 'teacher']:
        return redirect(url_for('login'))

    search = request.args.get('search', '')

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    if search:
        cursor.execute("""
            SELECT id, name, roll, dept, marks
            FROM students
            WHERE name LIKE %s OR roll LIKE %s OR dept LIKE %s
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT id, name, roll, dept, marks FROM students")

    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("view_students.html", students=students, search=search)

# ================= ADD =================
@app.route('/add', methods=['GET', 'POST'])
def add_student():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        roll = request.form['roll']
        dept = request.form['dept']
        marks = request.form['marks']

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)

        cursor.execute("""
            INSERT INTO students (name, roll, dept, marks)
            VALUES (%s, %s, %s, %s)
        """, (name, roll, dept, marks))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Student added successfully!", "success")
        return redirect(url_for('view_students'))

    return render_template('add_student.html')

# ================= PROFILE =================
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template("profile.html")

# ================= STUDENT MARKS =================
@app.route('/student_marks')
def student_marks():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute("""
        SELECT name, roll, marks 
        FROM students 
        WHERE name=%s
    """, (session['user'],))

    data = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("student_marks.html", data=data)

# ================= EDIT =================
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    if request.method == 'POST':
        cursor.execute("""
            UPDATE students
            SET name=%s, roll=%s, dept=%s, marks=%s
            WHERE id=%s
        """, (
            request.form['name'],
            request.form['roll'],
            request.form['dept'],
            request.form['marks'],
            id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Student updated successfully!", "info")
        return redirect(url_for('manage_students'))

    cursor.execute("SELECT id, name, roll, dept, marks FROM students WHERE id=%s", (id,))
    student = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('edit_student.html', student=student)

# ================= DELETE =================
@app.route('/delete/<int:id>')
def delete_student(id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute("DELETE FROM students WHERE id=%s", (id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Student deleted successfully!", "danger")
    return redirect(url_for('manage_students'))

# ================= MANAGE =================
@app.route('/manage')
def manage_students():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute("SELECT id, name, roll, dept, marks FROM students")
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('manage_students.html', students=students)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

# ================= EXPORT =================
@app.route('/export')
def export_csv():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute("SELECT id, name, roll, dept, marks FROM students")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    def generate():
        yield "ID,Name,Roll,Department,Marks\n"
        for row in data:
            yield f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"}
    )

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)