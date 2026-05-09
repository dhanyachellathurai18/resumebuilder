from flask import Flask, render_template, request, redirect, make_response
from reportlab.pdfgen import canvas
from io import BytesIO
import sqlite3

app = Flask(__name__)

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
        version_number INTEGER
    )
    """)

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
    return render_template('dashboard.html')

# Resume Builder Page
@app.route('/resume', methods=['GET', 'POST'])
def resume():

    if request.method == 'POST':

        name = request.form['name']
        skills = request.form['skills']
        education = request.form['education']
        experience = request.form['experience']

        conn = get_db()

        # Get latest version number
        last_version = conn.execute(
            "SELECT MAX(version_number) FROM resume_versions"
        ).fetchone()[0]

        if last_version is None:
            version = 1
        else:
            version = last_version + 1

        # Save new snapshot
        conn.execute("""
        INSERT INTO resume_versions
        (name, skills, education, experience, version_number)
        VALUES (?, ?, ?, ?, ?)
        """, (name, skills, education, experience, version))

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
    <body>

    <h1>Restored Resume</h1>

    <hr>

    <p><b>Name:</b> {resume[1]}</p>

    <p><b>Skills:</b> {resume[2]}</p>

    <p><b>Education:</b> {resume[3]}</p>

    <p><b>Experience:</b> {resume[4]}</p>

    <p><b>Version:</b> {resume[5]}</p>

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
Resume Version: {resume[5]}

Name:
{resume[1]}

Skills:
{resume[2]}

Education:
{resume[3]}

Experience:
{resume[4]}
"""

    response = make_response(content)

    response.headers["Content-Disposition"] = (
        f"attachment; filename=resume_version_{resume[5]}.txt"
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

    p.drawString(100, 800, f"Resume Version: {resume[5]}")

    p.drawString(100, 760, f"Name: {resume[1]}")

    p.drawString(100, 720, "Skills:")
    p.drawString(120, 700, resume[2])

    p.drawString(100, 660, "Education:")
    p.drawString(120, 640, resume[3])

    p.drawString(100, 600, "Experience:")
    p.drawString(120, 580, resume[4])

    p.save()

    pdf_data = buffer.getvalue()

    buffer.close()

    response = make_response(pdf_data)

    response.headers['Content-Type'] = 'application/pdf'

    response.headers['Content-Disposition'] = (
        f'attachment; filename=resume_{resume[5]}.pdf'
    )

    return response

if __name__ == '__main__':
    app.run(debug=True)