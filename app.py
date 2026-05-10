from flask import Flask, render_template, request, redirect, make_response
from reportlab.pdfgen import canvas
from io import BytesIO
import sqlite3
import os

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = 'static/uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder automatically
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database connection
def get_db():
    return sqlite3.connect("database.db")

# Create database tables
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
        version_number INTEGER
    )
    """)

    conn.commit()
    conn.close()

create_table()

# Home page
@app.route('/')
def home():
    return redirect('/login')

# Register page
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

# Login page
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

# Dashboard page
@app.route('/dashboard')
def dashboard():

    conn = get_db()

    total_users = conn.execute("""
    SELECT COUNT(*) FROM users
    """).fetchone()[0]

    total_resumes = conn.execute("""
    SELECT COUNT(*) FROM resume_versions
    """).fetchone()[0]

    conn.close()

    return render_template(
        'dashboard.html',
        total_users=total_users,
        total_resumes=total_resumes
    )

# Resume Builder Page
@app.route('/resume', methods=['GET', 'POST'])
def resume():

    if request.method == 'POST':

        name = request.form['name']
        skills = request.form['skills']
        education = request.form['education']
        experience = request.form['experience']

        # Template feature
        template = request.form['template']

        # Photo upload
        photo = request.files['photo']

        filename = photo.filename

        # Save image safely
        if filename != "":

            photo.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

        else:

            filename = "noimage.png"

        conn = get_db()

        # Get latest version number
        last_version = conn.execute(
            "SELECT MAX(version_number) FROM resume_versions"
        ).fetchone()[0]

        if last_version is None:
            version = 1
        else:
            version = last_version + 1

        # Save resume snapshot
        conn.execute("""
        INSERT INTO resume_versions
        (name, skills, education, experience, photo, template, version_number)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            skills,
            education,
            experience,
            filename,
            template,
            version
        ))

        conn.commit()
        conn.close()

        return f"Resume Saved Successfully! Version {version}"

    return render_template('resume.html')

# View all versions + search
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

# Resume Preview Page
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

# Restore old version
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
    </head>

    <body>

    <h1>Restored Resume</h1>

    <hr>

    <img
    src="/static/uploads/{resume[5]}"
    width="150"
    height="150"
    >

    <p><b>Name:</b> {resume[1]}</p>

    <p><b>Skills:</b> {resume[2]}</p>

    <p><b>Education:</b> {resume[3]}</p>

    <p><b>Experience:</b> {resume[4]}</p>

    <p><b>Template:</b> {resume[6]}</p>

    <p><b>Version:</b> {resume[7]}</p>

    <br>

    <a href="/versions">
        Back to Versions
    </a>

    </body>
    </html>
    """

# Delete version
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

# Download resume as TXT
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
"""

    response = make_response(content)

    response.headers["Content-Disposition"] = (
        f"attachment; filename=resume_version_{resume[7]}.txt"
    )

    response.headers["Content-type"] = "text/plain"

    return response

# Download resume as PDF
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

    # Different Template Designs
    if resume[6] == "Modern":

        p.setFont("Helvetica-Bold", 20)
        p.drawString(180, 820, "MODERN RESUME")

    elif resume[6] == "Professional":

        p.setFont("Times-Bold", 18)
        p.drawString(160, 820, "PROFESSIONAL RESUME")

    else:

        p.setFont("Courier-Bold", 18)
        p.drawString(180, 820, "CLASSIC RESUME")

    # Normal text
    p.setFont("Helvetica", 12)

    p.drawString(100, 780, f"Resume Version: {resume[7]}")

    p.drawString(100, 750, f"Name: {resume[1]}")

    p.drawString(100, 720, "Skills:")
    p.drawString(120, 700, resume[2])

    p.drawString(100, 670, "Education:")
    p.drawString(120, 650, resume[3])

    p.drawString(100, 620, "Experience:")
    p.drawString(120, 600, resume[4])

    p.drawString(100, 570, f"Template: {resume[6]}")

    # Add profile image
    image_path = os.path.join(
        app.config['UPLOAD_FOLDER'],
        resume[5]
    )

    if os.path.exists(image_path):

        p.drawImage(
            image_path,
            350,
            650,
            width=120,
            height=120
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

if __name__ == '__main__':
    app.run(debug=True)