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

    # Skills Score
    skills_length = len(skills)

    if skills_length >= 100:
        score += 35

    elif skills_length >= 50:
        score += 25

    elif skills_length >= 20:
        score += 15

    else:
        score += 5

    # Education Score
    education_length = len(education)

    if education_length >= 100:
        score += 25

    elif education_length >= 50:
        score += 18

    elif education_length >= 20:
        score += 10

    else:
        score += 5

    # Experience Score
    experience_length = len(experience)

    if experience_length >= 100:
        score += 30

    elif experience_length >= 50:
        score += 22

    elif experience_length >= 20:
        score += 15

    else:
        score += 5

    # Photo Score
    if photo != "noimage.png":
        score += 10

    # Bonus
    if "," in skills:
        score += 5

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

    # Maximum score
    if score > 100:
        score = 100

    return score


# ======================================
# GET RESUME RANK
# ======================================

def get_rank(score):

    if score >= 90:
        return "Excellent"

    elif score >= 70:
        return "Good"

    elif score >= 50:
        return "Average"

    else:
        return "Poor"


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

        template = request.form['template']

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

        # Calculate Score
        score = calculate_score(
            skills,
            education,
            experience,
            filename
        )

        # Get Rank
        rank = get_rank(score)

        conn = get_db()

        # Get Latest Version
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
        <html>

        <head>

            <title>Resume Saved</title>

            <style>

                body{{
                    font-family: Arial;
                    background:#f0f2f5;
                    padding:40px;
                }}

                .box{{
                    width:500px;
                    margin:auto;
                    background:white;
                    padding:30px;
                    border-radius:10px;
                    box-shadow:0px 0px 10px gray;
                    text-align:center;
                }}

                h2{{
                    color:green;
                }}

                h3{{
                    color:darkblue;
                }}

                a{{
                    text-decoration:none;
                    background:darkblue;
                    color:white;
                    padding:10px 20px;
                    border-radius:5px;
                }}

            </style>

        </head>

        <body>

        <div class="box">

        <h2>
        Resume Saved Successfully!
        </h2>

        <h3>
        Resume Score: {score}/100
        </h3>

        <h3>
        Resume Rank: {rank}
        </h3>

        <br>

        <a href='/dashboard'>
            Go To Dashboard
        </a>

        </div>

        </body>

        </html>
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

    # ======================================
    # STORE RESUME + RANK
    # ======================================

    resume_data = []

    for r in resumes:

        rank = get_rank(r[8])

        resume_data.append(
            (r, rank)
        )

    return render_template(
        'versions.html',
        resume_data=resume_data
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

    rank = get_rank(resume[8])

    return render_template(
        'preview.html',
        resume=resume,
        rank=rank
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

    rank = get_rank(resume[8])

    return f"""
    <html>

    <head>

        <title>Restored Resume</title>

    </head>

    <body>

    <h1>Restored Resume</h1>

    <p>Name: {resume[1]}</p>

    <p>Skills: {resume[2]}</p>

    <p>Education: {resume[3]}</p>

    <p>Experience: {resume[4]}</p>

    <p>Template: {resume[6]}</p>

    <p>Version: {resume[7]}</p>

    <p>Score: {resume[8]}/100</p>

    <p>Rank: {rank}</p>

    <a href="/versions">
        Back
    </a>

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

    rank = get_rank(resume[8])

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

Resume Rank:
{rank}
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

    rank = get_rank(resume[8])

    buffer = BytesIO()

    p = canvas.Canvas(buffer)

    p.setFont("Helvetica-Bold", 22)
    p.drawString(170, 820, "RESUME")

    p.setFont("Helvetica-Bold", 14)

    p.drawString(70, 760, "Name")
    p.drawString(70, 710, "Skills")
    p.drawString(70, 640, "Education")
    p.drawString(70, 570, "Experience")
    p.drawString(70, 500, "Resume Score")
    p.drawString(70, 460, "Resume Rank")

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
    p.drawString(150, 460, rank)

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