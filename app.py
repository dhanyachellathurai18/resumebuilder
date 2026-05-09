from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# Database connection
def get_db():
    return sqlite3.connect("database.db")

# Create tables
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

        return "Registered Successfully!"

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
            return redirect('/resume')
        else:
            return "Invalid Credentials!"

    return render_template('login.html')

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

        # Insert new snapshot
        conn.execute("""
        INSERT INTO resume_versions
        (name, skills, education, experience, version_number)
        VALUES (?, ?, ?, ?, ?)
        """, (name, skills, education, experience, version))

        conn.commit()
        conn.close()

        return f"Resume Saved Successfully! Version {version}"

    return render_template('resume.html')

if __name__ == '__main__':
    app.run(debug=True)