from flask import Flask, render_template, request, redirect, make_response
from reportlab.pdfgen import canvas
from io import BytesIO
import sqlite3
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DATABASE
# =========================
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
        email TEXT,
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

# =========================
# SCORE SYSTEM
# =========================
def calculate_score(skills, education, experience, photo):

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
    else:
        return "Poor"

# =========================
# HOME
# =========================
@app.route('/')
def home():
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect('/dashboard')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return redirect('/login')
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    conn = get_db()

    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_resumes = conn.execute("SELECT COUNT(*) FROM resume_versions").fetchone()[0]

    conn.close()

    return render_template("dashboard.html",
                           total_users=total_users,
                           total_resumes=total_resumes)

# =========================
# CREATE RESUME
# =========================
@app.route('/resume', methods=['GET', 'POST'])
def resume():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        linkedin = request.form.get('linkedin')
        objective = request.form.get('objective')
        skills = request.form.get('skills')
        education = request.form.get('education')
        experience = request.form.get('experience')
        location = request.form.get('location')
        template = request.form.get('template')

        photo = request.files.get('photo')

        if photo and photo.filename != "":
            filename = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = "noimage.png"

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

        return redirect('/versions')

    return render_template('resume.html')


# =========================
# VERSION HISTORY + SEARCH FIXED
# =========================
@app.route('/versions')
def versions():

    search = request.args.get('search', '').strip()

    conn = get_db()

    if search:
        resumes = conn.execute("""
            SELECT * FROM resume_versions
            WHERE name LIKE ? OR skills LIKE ? OR email LIKE ?
            ORDER BY id DESC
        """, ('%' + search + '%', '%' + search + '%', '%' + search + '%')).fetchall()
    else:
        resumes = conn.execute("""
            SELECT * FROM resume_versions
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    data = [(r, get_rank(r["score"])) for r in resumes]

    return render_template("versions.html", resume_data=data)


# =========================
# PREVIEW
# =========================
@app.route('/preview/<int:id>')
def preview(id):

    conn = get_db()
    resume = conn.execute("SELECT * FROM resume_versions WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template("preview.html",
                           resume=resume,
                           rank=get_rank(resume["score"]))


# =========================
# DELETE
# =========================
@app.route('/delete/<int:id>')
def delete(id):

    conn = get_db()
    conn.execute("DELETE FROM resume_versions WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/versions')


# =========================
# PDF (CLEAN + IMAGE FIXED)
# =========================
@app.route('/pdf/<int:id>')
def pdf(id):

    conn = get_db()
    resume = conn.execute("SELECT * FROM resume_versions WHERE id=?", (id,)).fetchone()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # HEADER
    p.setFont("Helvetica-Bold", 20)
    p.drawString(200, 800, "AI RESUME")

    # IMAGE
    if resume["photo"] and resume["photo"] != "noimage.png":
        img_path = os.path.join("static/uploads", resume["photo"])
        try:
            p.drawImage(img_path, 450, 720, width=90, height=90)
        except:
            pass

    # NAME
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 760, resume["name"])

    # CONTACT
    p.setFont("Helvetica", 11)
    p.drawString(50, 735, f"Email: {resume['email']}")
    p.drawString(50, 720, f"Phone: {resume['phone']}")
    p.drawString(50, 705, f"LinkedIn: {resume['linkedin']}")
    p.drawString(50, 690, f"Location: {resume['location']}")

    p.line(50, 680, 550, 680)

    # OBJECTIVE
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, 655, "Objective")
    text = p.beginText(50, 640)
    text.textLines(resume["objective"] or "")
    p.drawText(text)

    # SKILLS
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, 600, "Skills")
    text = p.beginText(50, 585)
    text.textLines(resume["skills"] or "")
    p.drawText(text)

    # EDUCATION
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, 545, "Education")
    text = p.beginText(50, 530)
    text.textLines(resume["education"] or "")
    p.drawText(text)

    # EXPERIENCE
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, 490, "Experience")
    text = p.beginText(50, 475)
    text.textLines(resume["experience"] or "")
    p.drawText(text)

    # SCORE
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, 430, f"AI Score: {resume['score']}/100")

    p.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=resume.pdf'

    return response


if __name__ == "__main__":
    app.run(debug=True)