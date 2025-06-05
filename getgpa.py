from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import uuid
from aspen import Aspen, GRADE_POINTS, TYPE_POINTS

app = Flask(__name__)
app.config["SECRET_KEY"] = uuid.uuid4()
socketio = SocketIO(app)

@app.route("/")
def index():
    """Render the home page."""
    return render_template("home.html")

@socketio.on("calculate")
def calculate_gpa(credentials: dict):
    username = credentials.get("username")
    password = credentials.get("password")
    emit("log", "Logging in to Aspen")

    try:
        aspen = Aspen(username, password)
    except Exception as e:
        emit("log", str(e))
        emit("results", { "error": True })
        return
    
    emit("log", "Getting current transcript")
    transcript = aspen.get_transcript_classes()

    emit("log", "Getting current grades")
    grades = aspen.get_current_grades()

    emit("log", "Calculating GPA")
    unweighted_gpa, weighted_gpa = calculate_gpa(transcript, grades)

    emit("results", {
        "unweighted": f"{unweighted_gpa:.3f}",
        "weighted": f"{weighted_gpa:.3f}"
    })

    emit("log", "Done!")


def calculate_gpa(transcript, grades):
    unweighted_points = [
        GRADE_POINTS.get(grades[_class], 0)
        for _class in grades
        if not transcript.get(_class, "").endswith("N")
    ]
    weighted_points = [
        GRADE_POINTS.get(grades[_class], 0) + TYPE_POINTS.get(transcript.get(_class, "")[-1], 0)
        for _class in grades
        if not transcript.get(_class, "").endswith("N")
    ]

    unweighted_gpa = sum(unweighted_points) / len(unweighted_points) * 2 if unweighted_points else 0
    weighted_gpa = sum(weighted_points) / len(weighted_points) * 2 if weighted_points else 0

    return unweighted_gpa, weighted_gpa

if __name__ == "__main__":
    socketio.run(app, "0.0.0.0", 8080, debug=True, allow_unsafe_werkzeug=True)