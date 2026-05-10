from flask import Flask, render_template, request, redirect, make_response, session
from reportlab.pdfgen import canvas
from io import BytesIO
import sqlite3
import os
import time
import textwrap

app = Flask(__name__)
app.secret_key = "resume_secret_key"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DB =================
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS resume_versions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        linkedin TEXT,
        objective TEXT,
        skills TEXT,
        education TEXT,
        experience TEXT,
        location TEXT,
        photo TEXT,
        template TEXT,
        version_number INTEGER,
        score INTEGER
    )
    """)

    conn.commit()
    conn.close()


create_table()

# ================= SCORE =================
def calculate_score(skills, education, experience, photo):
    skills = skills or ""
    education = education or ""
    experience = experience or ""

    score = 0
    score += min(len(skills)//2, 35)
    score += min(len(education)//3, 25)
    score += min(len(experience)//3, 30)

    if photo and photo != "noimage.png":
        score += 10

    return min(score, 100)


def get_rank(score):
    if score >= 90:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Average"
    return "Poor"

# ================= HOME =================
@app.route('/')
def home():
    return redirect('/login')


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user"] = user["name"]
            return redirect("/dashboard")
        return "Invalid login ❌"

    return render_template("login.html")


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?,?,?)",
            (name, email, password)
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_resumes = conn.execute("SELECT COUNT(*) FROM resume_versions").fetchone()[0]

    conn.close()

    return render_template("dashboard.html",
                           total_users=total_users,
                           total_resumes=total_resumes)


# ================= CREATE RESUME =================
@app.route('/resume', methods=['GET', 'POST'])
def resume():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        linkedin = request.form.get("linkedin")
        objective = request.form.get("objective")
        skills = request.form.get("skills")
        education = request.form.get("education")
        experience = request.form.get("experience")
        location = request.form.get("location")
        template = request.form.get("template")

        photo = request.files.get("photo")

        filename = "noimage.png"

        if photo and photo.filename:
            filename = str(int(time.time())) + "_" + photo.filename
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        score = calculate_score(skills, education, experience, filename)

        conn = get_db()

        last_version = conn.execute(
            "SELECT MAX(version_number) FROM resume_versions"
        ).fetchone()[0]

        version = 1 if last_version is None else last_version + 1

        conn.execute("""
        INSERT INTO resume_versions (
            name, email, phone, linkedin, objective,
            skills, education, experience, location,
            photo, template, version_number, score
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            name, email, phone, linkedin, objective,
            skills, education, experience, location,
            filename, template, version, score
        ))

        conn.commit()
        conn.close()

        return redirect("/versions")

    return render_template("resume.html")


# ================= VERSIONS =================
@app.route('/versions')
def versions():

    conn = get_db()
    resumes = conn.execute("SELECT * FROM resume_versions ORDER BY id DESC").fetchall()
    conn.close()

    data = [(r, get_rank(r["score"])) for r in resumes]

    return render_template("versions.html", resume_data=data)


# ================= PREVIEW =================
@app.route('/preview/<int:id>')
def preview(id):

    conn = get_db()
    resume = conn.execute("SELECT * FROM resume_versions WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template("preview.html",
                           resume=resume,
                           rank=get_rank(resume["score"]))


# ================= DELETE =================
@app.route('/delete/<int:id>')
def delete(id):

    conn = get_db()
    conn.execute("DELETE FROM resume_versions WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/versions")


# ================= PDF (FINAL FIXED + CLEAN OUTPUT) =================
def draw_wrapped_text(canvas_obj, text, x, y, max_chars=95, line_height=14):
    """Proper text wrapping FIX"""
    lines = textwrap.wrap(text or "", max_chars)
    for line in lines:
        canvas_obj.drawString(x, y, line)
        y -= line_height
    return y


@app.route('/pdf/<int:id>')
def pdf(id):

    conn = get_db()
    resume = conn.execute("SELECT * FROM resume_versions WHERE id=?", (id,)).fetchone()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    width, height = 595, 842

    # TITLE BAR
    p.setFont("Helvetica-Bold", 20)
    p.drawString(220, height - 50, "AI RESUME")

    # IMAGE FIX
    if resume["photo"] and resume["photo"] != "noimage.png":
        img_path = os.path.join(app.config["UPLOAD_FOLDER"], resume["photo"])
        if os.path.exists(img_path):
            p.drawImage(img_path, 450, height - 140, width=90, height=90, mask='auto')

    # NAME
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, resume["name"])

    # CONTACT
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 130, f"Email: {resume['email']}")
    p.drawString(50, height - 145, f"Phone: {resume['phone']}")
    p.drawString(50, height - 160, f"LinkedIn: {resume['linkedin']}")
    p.drawString(50, height - 175, f"Location: {resume['location']}")

    y = height - 210

    def section(title, content):
        nonlocal y
        p.setFont("Helvetica-Bold", 13)
        p.drawString(50, y, title)
        y -= 18

        p.setFont("Helvetica", 10)
        y = draw_wrapped_text(p, content, 60, y, 95)
        y -= 10

    section("OBJECTIVE", resume["objective"])
    section("SKILLS", resume["skills"])
    section("EDUCATION", resume["education"])
    section("EXPERIENCE", resume["experience"])

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 80, f"AI SCORE: {resume['score']}/100")

    p.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=resume.pdf"

    return response


if __name__ == "__main__":
    app.run(debug=True)