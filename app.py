from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
from functools import wraps
from analysis import get_feedback_analysis

app = Flask(__name__, template_folder="Templates", static_folder="static")
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "change-this-secret-key"
)

# MySQL configuration
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Bhargav@2008")
DB_NAME = "student_feedback"

# Change these before using the admin login
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD", "ChangeThisPassword123!"
)


def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return function(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    try:
        get_feedback_analysis()
    except Exception as e:
        print("Chart refresh note:", repr(e))
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    connection = None
    cursor = None

    try:
        student_name = request.form.get("student_name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        degree = request.form.get("degree", "").strip()
        branch = request.form.get("branch", "").strip()
        year = request.form.get("year_of_study", "").strip()
        semester = request.form.get("semester", "").strip()
        section = request.form.get("section", "").strip()
        course = request.form.get("course_name", "").strip()
        teacher = request.form.get("teacher_name", "").strip()
        rating = request.form.get("rating", "").strip()
        comments = request.form.get("comments", "").strip()

        if not all([
            student_name, student_id, degree, branch, year,
            semester, section, course, teacher, rating
        ]):
            return "Please fill in all required fields.", 400

        connection = get_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO feedback (
                student_name, student_id, degree, branch,
                year_of_study, semester, course_name, rating,
                comments, teacher_name, section
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            student_name, student_id, degree, branch,
            int(year), int(semester), course, int(rating),
            comments if comments else None, teacher, section
        )

        cursor.execute(query, values)
        connection.commit()

        return redirect(url_for("thankyou"))

    except Exception as e:
        if connection and connection.is_connected():
            connection.rollback()
        print("Feedback submission error:", repr(e))
        return "Feedback could not be submitted. Check the terminal.", 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("analysis_dashboard"))

        error = "Invalid username or password."

    return render_template("admin_login.html", error=error)


@app.route("/analysis")
@admin_required
def analysis_dashboard():
    try:
        results = get_feedback_analysis()
        return render_template("analysis.html", **results)
    except Exception as e:
        print("Admin dashboard error:", repr(e))
        return "Could not load feedback analysis. Check the VS Code terminal.", 500


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    app.run(debug=True)
