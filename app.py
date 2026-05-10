from flask import Flask, render_template, request, redirect, make_response
from reportlab.pdfgen import canvas
from io import BytesIO
import sqlite3
import os

app = Flask(__name__)

# ======================================
# UPLOAD FOLDER
# ======================================

UPLOAD_FOLDER = 'static/uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder automatically
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ======================================
# DATABASE CONNECTION
# ======================================

def get_db():
    return sqlite3.connect("database.db")


# ======================================
# CREATE DATABASE TABLES
# ======================================

def create_table():

    conn = get_db()

    # Users table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT
    )
    """)

    # Resume versions table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS resume_versions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        skills TEXT,
        education TEXT,
        experience TEXT,
        photo TEXT,
        template TEXT,
        version_number INTEGER,
        score INTEGER
    )
    """)

    conn.commit()
    conn.close()


create_table()


# ======================================
# CALCULATE RESUME SCORE
# ======================================

def calculate_score(skills, education, experience, photo):

    score = 0

    # =========================
    # SKILLS SCORE
    # =========================

    skills_length = len(skills)

    if skills_length >= 100:
        score += 35

    elif skills_length >= 50:
        score += 25

    elif skills_length >= 20:
        score += 15

    else:
        score += 5

    # =========================
    # EDUCATION SCORE
    # =========================

    education_length = len(education)

    if education_length >= 100:
        score += 25

    elif education_length >= 50:
        score += 18

    elif education_length >= 20:
        score += 10

    else:
        score += 5

    # =========================
    # EXPERIENCE SCORE
    # =========================

    experience_length = len(experience)

    if experience_length >= 100:
        score += 30

    elif experience_length >= 50:
        score += 22

    elif experience_length >= 20:
        score += 15

    else:
        score += 5

    # =========================
    # PHOTO SCORE
    # =========================

    if photo != "noimage.png":
        score += 10

    # =========================
    # BONUS FEATURES
    # =========================

    # Bonus for multiple skills
    if "," in skills:
        score += 5

    # Bonus for professional keywords
    professional_words = [
        "python",
        "java",
        "c++",
        "sql",
        "html",
        "css",
        "javascript",
        "flask"
    ]

    skills_lower = skills.lower()

    for word in professional_words:

        if word in skills_lower:
            score += 2

    # Maximum score limit
    if score > 100:
        score = 100

    return score


# ======================================
# HOME PAGE
# ======================================

@app.route('/')
def home():
    return redirect('/login')


# ======================================
# REGISTER PAGE
# ======================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db()

        conn.execute(
            "INSERT INTO users(name,email,password) VALUES(?,?,?)",
            (name, email, password)
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


# ======================================
# LOGIN PAGE
# ======================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()

        conn.close()

        if user:
            return redirect('/dashboard')

        else:
            return "Invalid Credentials!"

    return render_template('login.html')


# ======================================
# DASHBOARD PAGE
# ======================================

@app.route('/dashboard')
def dashboard():

    conn = get_db()

    total_users = conn.execute("""
    SELECT COUNT(*) FROM users
    """).fetchone()[0]

    total_resumes = conn.execute("""
    SELECT COUNT(*) FROM resume_versions
    """).fetchone()[0]

    latest_resume = conn.execute("""
    SELECT * FROM resume_versions
    ORDER BY version_number DESC
    LIMIT 1
    """).fetchone()

    conn.close()

    return render_template(
        'dashboard.html',
        total_users=total_users,
        total_resumes=total_resumes,
        latest_resume=latest_resume
    )


# ======================================
# RESUME BUILDER PAGE
# ======================================

@app.route('/resume', methods=['GET', 'POST'])
def resume():

    if request.method == 'POST':

        name = request.form['name']
        skills = request.form['skills']
        education = request.form['education']
        experience = request.form['experience']

        # Template Feature
        template = request.form['template']

        # Photo Upload
        photo = request.files['photo']

        filename = photo.filename

        # Save Image
        if filename != "":

            photo.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

        else:

            filename = "noimage.png"

        # ======================================
        # CALCULATE SCORE
        # ======================================

        score = calculate_score(
            skills,
            education,
            experience,
            filename
        )

        conn = get_db()

        # Latest version number
        last_version = conn.execute(
            "SELECT MAX(version_number) FROM resume_versions"
        ).fetchone()[0]

        if last_version is None:
            version = 1
        else:
            version = last_version + 1

        # Save Resume
        conn.execute("""
        INSERT INTO resume_versions
        (
            name,
            skills,
            education,
            experience,
            photo,
            template,
            version_number,
            score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            skills,
            education,
            experience,
            filename,
            template,
            version,
            score
        ))

        conn.commit()
        conn.close()

        return f"""
        <h2>
        Resume Saved Successfully!
        </h2>

        <h3>
        Resume Score: {score}/100
        </h3>

        <a href='/dashboard'>
            Go To Dashboard
        </a>
        """

    return render_template('resume.html')


# ======================================
# VIEW ALL RESUME VERSIONS
# ======================================

@app.route('/versions')
def versions():

    search = request.args.get('search')

    conn = get_db()

    if search:

        resumes = conn.execute("""
        SELECT * FROM resume_versions
        WHERE name LIKE ?
        ORDER BY version_number DESC
        """, ('%' + search + '%',)).fetchall()

    else:

        resumes = conn.execute("""
        SELECT * FROM resume_versions
        ORDER BY version_number DESC
        """).fetchall()

    conn.close()

    return render_template(
        'versions.html',
        resumes=resumes
    )


# ======================================
# RESUME PREVIEW PAGE
# ======================================

@app.route('/preview/<int:id>')
def preview(id):

    conn = get_db()

    resume = conn.execute("""
    SELECT * FROM resume_versions
    WHERE id=?
    """, (id,)).fetchone()

    conn.close()

    return render_template(
        'preview.html',
        resume=resume
    )


# ======================================
# RESTORE OLD VERSION
# ======================================

@app.route('/restore/<int:id>')
def restore(id):

    conn = get_db()

    resume = conn.execute("""
    SELECT * FROM resume_versions
    WHERE id=?
    """, (id,)).fetchone()

    conn.close()

    return f"""
    <html>

    <head>

        <title>Restored Resume</title>

        <style>

            body{{
                font-family: Arial;
                background:#f0f2f5;
                padding:40px;
            }}

            .box{{
                width:700px;
                margin:auto;
                background:white;
                padding:30px;
                border-radius:10px;
                box-shadow:0px 0px 10px gray;
            }}

            img{{
                border-radius:50%;
            }}

        </style>

    </head>

    <body>

    <div class="box">

    <center>

    <h1>Restored Resume</h1>

    <img
    src="/static/uploads/{resume[5]}"
    width="150"
    height="150"
    >

    </center>

    <hr>

    <p><b>Name:</b> {resume[1]}</p>

    <p><b>Skills:</b> {resume[2]}</p>

    <p><b>Education:</b> {resume[3]}</p>

    <p><b>Experience:</b> {resume[4]}</p>

    <p><b>Template:</b> {resume[6]}</p>

    <p><b>Version:</b> {resume[7]}</p>

    <p><b>Resume Score:</b> {resume[8]}/100</p>

    <br>

    <a href="/versions">
        Back to Versions
    </a>

    </div>

    </body>
    </html>
    """


# ======================================
# DELETE VERSION
# ======================================

@app.route('/delete/<int:id>')
def delete(id):

    conn = get_db()

    conn.execute("""
    DELETE FROM resume_versions
    WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/versions')


# ======================================
# DOWNLOAD TXT
# ======================================

@app.route('/download/<int:id>')
def download(id):

    conn = get_db()

    resume = conn.execute("""
    SELECT * FROM resume_versions
    WHERE id=?
    """, (id,)).fetchone()

    conn.close()

    content = f"""
Resume Version: {resume[7]}

Name:
{resume[1]}

Skills:
{resume[2]}

Education:
{resume[3]}

Experience:
{resume[4]}

Template:
{resume[6]}

Resume Score:
{resume[8]}/100
"""

    response = make_response(content)

    response.headers["Content-Disposition"] = (
        f"attachment; filename=resume_version_{resume[7]}.txt"
    )

    response.headers["Content-type"] = "text/plain"

    return response


# ======================================
# DOWNLOAD PDF
# ======================================

@app.route('/pdf/<int:id>')
def pdf(id):

    conn = get_db()

    resume = conn.execute("""
    SELECT * FROM resume_versions
    WHERE id=?
    """, (id,)).fetchone()

    conn.close()

    buffer = BytesIO()

    p = canvas.Canvas(buffer)

    # ======================================
    # TEMPLATE DESIGNS
    # ======================================

    if resume[6] == "Modern":

        p.setFont("Helvetica-Bold", 22)
        p.drawString(170, 820, "MODERN RESUME")

        p.line(70, 810, 520, 810)

    elif resume[6] == "Professional":

        p.setFont("Times-Bold", 22)
        p.drawString(150, 820, "PROFESSIONAL RESUME")

        p.line(70, 810, 520, 810)

    else:

        p.setFont("Courier-Bold", 22)
        p.drawString(180, 820, "CLASSIC RESUME")

        p.line(70, 810, 520, 810)

    # ======================================
    # PROFILE IMAGE
    # ======================================

    image_path = os.path.join(
        app.config['UPLOAD_FOLDER'],
        resume[5]
    )

    if os.path.exists(image_path):

        try:

            p.drawImage(
                image_path,
                380,
                640,
                width=120,
                height=120
            )

        except:
            pass

    # ======================================
    # CONTENT
    # ======================================

    p.setFont("Helvetica-Bold", 14)

    p.drawString(70, 760, "Name")
    p.drawString(70, 710, "Skills")
    p.drawString(70, 640, "Education")
    p.drawString(70, 570, "Experience")
    p.drawString(70, 500, "Resume Score")

    p.setFont("Helvetica", 12)

    p.drawString(150, 760, resume[1])

    text = p.beginText(150, 710)
    text.textLines(resume[2])
    p.drawText(text)

    text = p.beginText(150, 640)
    text.textLines(resume[3])
    p.drawText(text)

    text = p.beginText(150, 570)
    text.textLines(resume[4])
    p.drawText(text)

    p.drawString(150, 500, f"{resume[8]}/100")

    # Footer
    p.setFont("Helvetica-Oblique", 10)

    p.drawString(
        70,
        100,
        f"Template: {resume[6]} | Version: {resume[7]}"
    )

    p.save()

    pdf_data = buffer.getvalue()

    buffer.close()

    response = make_response(pdf_data)

    response.headers['Content-Type'] = 'application/pdf'

    response.headers['Content-Disposition'] = (
        f'attachment; filename=resume_{resume[7]}.pdf'
    )

    return response


# ======================================
# RUN APPLICATION
# ======================================

if __name__ == '__main__':
    app.run(debug=True)