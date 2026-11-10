import os
import mysql.connector
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


# MySQL configuration — keep this the same as app.py
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Bhargav@2008")
DB_NAME = "student_feedback"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(STATIC_DIR, exist_ok=True)


def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def get_feedback_analysis():
    connection = None

    try:
        connection = get_connection()

        query = """
            SELECT
                student_name,
                student_id,
                course_name,
                teacher_name,
                section,
                degree,
                branch,
                year_of_study,
                semester,
                rating,
                comments
            FROM feedback
        """

        df = pd.read_sql(query, connection)

    finally:
        if connection and connection.is_connected():
            connection.close()

    # Ensure ratings are numeric
    if not df.empty:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df = df.dropna(subset=["rating"])
        df = df[(df["rating"] >= 1) & (df["rating"] <= 5)]

    total_responses = len(df)

    if total_responses > 0:
        overall_average = float(np.mean(df["rating"].to_numpy()))
        course_count = int(df["course_name"].nunique())

        # Course-wise analysis
        course_group = (
            df.groupby("course_name", dropna=False)["rating"]
            .agg(["count", "mean"])
            .reset_index()
        )

        course_group.columns = [
            "course_name", "responses", "average_rating"
        ]

        course_results = [
            {
                "course_name": str(row["course_name"]),
                "responses": int(row["responses"]),
                "average_rating": float(row["average_rating"])
            }
            for _, row in course_group.iterrows()
        ]

        # Rating distribution: always include ratings 1 to 5
        counts = df["rating"].value_counts().reindex(
            [1, 2, 3, 4, 5], fill_value=0
        )

        rating_counts = {
            int(rating): int(count)
            for rating, count in counts.items()
        }

        # Course ratings chart
        course_plot = course_group.sort_values(
            "average_rating", ascending=False
        )

        plt.figure(figsize=(10, 5))
        plt.bar(
            course_plot["course_name"].astype(str),
            course_plot["average_rating"],
            color="#35633e"
        )
        plt.title("Average Rating by Course")
        plt.xlabel("Course")
        plt.ylabel("Average Rating")
        plt.ylim(0, 5)
        plt.xticks(rotation=35, ha="right")
        plt.tight_layout()

        plt.savefig(
            os.path.join(STATIC_DIR, "course_ratings.png"),
            dpi=120
        )
        plt.close()

        # Teacher ratings chart — separate ratings by teacher and section
        teacher_df = df.dropna(
            subset=["teacher_name", "section"]
        ).copy()

        teacher_df["teacher_name"] = (
            teacher_df["teacher_name"].astype(str).str.strip()
        )
        teacher_df["section"] = (
            teacher_df["section"].astype(str).str.strip()
        )

        teacher_df = teacher_df[
            (teacher_df["teacher_name"] != "")
            & (teacher_df["teacher_name"] != "Not Assigned")
            & (teacher_df["section"] != "")
            & (teacher_df["section"] != "Not Assigned")
        ]

        if not teacher_df.empty:
            teacher_group = (
                teacher_df.groupby(
                    ["teacher_name", "section"]
                )["rating"]
                .mean()
                .sort_index()
            )

            labels = [
                f"{teacher} - {section}"
                for teacher, section in teacher_group.index
            ]

            plt.figure(figsize=(9, 5))
            plt.bar(labels, teacher_group.values, color="#4e8958")
            plt.title("Average Rating by Teacher (with Section)")
            plt.xlabel("Teacher - Section")
            plt.ylabel("Average Rating")
            plt.ylim(0, 5)
            plt.xticks(rotation=35, ha="right")
            plt.tight_layout()

            plt.savefig(
                os.path.join(STATIC_DIR, "teacher_ratings.png"),
                dpi=120
            )
            plt.close()
        else:
            create_empty_chart(
                "Teacher Ratings",
                "No assigned teacher and section ratings available",
                "teacher_ratings.png"
            )

        has_data = True

    # Convert full dataframe rows for admin view (showing Student ID / Roll No to higher authorities)
        student_feedback_list = df.to_dict(orient="records") if not df.empty else []

        has_data = True

    else:
        overall_average = None
        course_count = 0
        course_results = []
        rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        student_feedback_list = []
        has_data = False

        create_empty_chart(
            "Course Ratings",
            "No feedback available yet",
            "course_ratings.png"
        )

        create_empty_chart(
            "Teacher Ratings",
            "No feedback available yet",
            "teacher_ratings.png"
        )

    return {
        "total_responses": total_responses,
        "overall_average": overall_average,
        "course_count": course_count,
        "course_results": course_results,
        "rating_counts": rating_counts,
        "student_feedback_list": student_feedback_list,
        "has_data": has_data
    }


def create_empty_chart(title, message, filename):
    plt.figure(figsize=(8, 4))
    plt.text(
        0.5, 0.5, message,
        horizontalalignment="center",
        verticalalignment="center",
        transform=plt.gca().transAxes
    )
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(
        os.path.join(STATIC_DIR, filename),
        dpi=120
    )
    plt.close()


if __name__ == "__main__":
    try:
        results = get_feedback_analysis()
        print("Feedback analysis completed successfully.")
        print("Total responses:", results["total_responses"])
        print("Overall average:", results["overall_average"])
        print("Courses reviewed:", results["course_count"])
        print("Rating distribution:", results["rating_counts"])
        print("Charts saved in:", STATIC_DIR)

    except Exception as error:
        print("Analysis error:", repr(error))
