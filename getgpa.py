from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import requests
from bs4 import BeautifulSoup
import uuid

# Constants for grade and type points
GRADE_POINTS = {
    "F": 0,
    "D": 0.5,
    "C": 1,
    "B": 1.5,
    "A": 2
}

TYPE_POINTS = {
    "R": 0,
    "H": 0.5,
    "A": 1
}

# Flask app setup
app = Flask(__name__)
app.config["SECRET_KEY"] = uuid.uuid4()
socketio = SocketIO(app)

@app.route("/")
def index():
    """Render the home page."""
    return render_template("home.html")

@socketio.on("calculate")
def calculate_gpa(credentials: dict):
    """Handle GPA calculation based on user credentials."""
    username = credentials.get("username")
    password = credentials.get("password")
    emit("log", "Logging in to Aspen")

    session = requests.Session()
    login_url = "https://aspen.cps.edu/aspen/logon.do"

    # Perform login
    resp = session.get(login_url)
    auth_resp = session.post(
        login_url,
        data={
            "org.apache.struts.taglib.html.TOKEN": get_struts(resp.text),
            "userEvent": "930",
            "deploymentId": "aspen",
            "username": username,
            "password": password
        },
        allow_redirects=False
    )

    if auth_resp.status_code == 302:
        emit("log", "Getting transcript information")
        class_info = fetch_transcript_info(session)

        emit("log", "Getting current grades")
        grades = fetch_current_grades(session, class_info)

        emit("log", "Calculating GPA\n")
        unweighted, weighted = get_gpa(grades)
        emit("log", f"Un-Weighted GPA: {unweighted:.3f}")
        emit("log", f"Weighted GPA: {weighted:.3f}")
    else:
        emit("log", "Authentication failed")

def get_struts(document: str) -> str:
    """Extract the Struts token from the HTML document."""
    soup = BeautifulSoup(document, features="html.parser")
    return soup.find("input", {"name": "org.apache.struts.taglib.html.TOKEN"}).get("value")

def fetch_transcript_info(session: requests.Session) -> dict:
    """Fetch transcript information and return class types."""
    transcript_url = "https://aspen.cps.edu/aspen/transcriptList.do?navkey=myInfo.trn.list"
    transcript_resp = session.get(transcript_url)
    transcript_soup = BeautifulSoup(transcript_resp.text, features="html.parser")
    table = transcript_soup.find("div", id="dataGrid").find("table")
    transcript_rows = table.find_all("tr", class_=["listCell", "listRowHeight"])

    class_info = {}
    for row in transcript_rows:
        cells = row.find_all("td")
        class_type = cells[2].text.strip()[-1]
        description = cells[4].text.strip()
        class_info[description] = class_type

    return class_info

def fetch_current_grades(session: requests.Session, class_info: dict) -> dict:
    """Fetch current grades and return a dictionary of grades and types."""
    classes_url = "https://aspen.cps.edu/aspen/portalClassList.do?navkey=academics.classes.list"
    classes_resp = session.get(classes_url)
    classes_soup = BeautifulSoup(classes_resp.text, features="html.parser")
    table = classes_soup.find("div", id="dataGrid").find("table")
    class_rows = table.find_all("tr", class_=["listCell", "listRowHeight"])

    grades = {}
    for row in class_rows:
        cells = row.find_all("td")
        description = cells[1].text.strip()
        grade_string = cells[7].text.strip()
        if grade_string and description in class_info and class_info.get(description) != "N":
            grades[description] = {
                "grade": grade_string.split(" ")[1],
                "type": class_info.get(description)
            }

    return grades

def get_gpa(classes: dict[str, dict[str, str]]) -> tuple:
    """
    Calculate unweighted and weighted GPA based on class grades and types.

    Args:
        classes (dict): A dictionary where keys are class descriptions and values are dictionaries
                        containing 'grade' and 'type'.

    Returns:
        tuple: Unweighted GPA and Weighted GPA.
    """
    try:
        unweighted_points = [
            GRADE_POINTS.get(class_info["grade"], 0) for class_info in classes.values()
        ]
        weighted_points = [
            GRADE_POINTS.get(class_info["grade"], 0) + TYPE_POINTS.get(class_info["type"], 0)
            for class_info in classes.values()
        ]

        unweighted_gpa = sum(unweighted_points) / len(unweighted_points) * 2 if unweighted_points else 0
        weighted_gpa = sum(weighted_points) / len(weighted_points) * 2 if weighted_points else 0

        return unweighted_gpa, weighted_gpa
    except Exception as e:
        raise ValueError(f"Error calculating GPA: {e}")

if __name__ == "__main__":
    socketio.run(app, "0.0.0.0", 8080, debug=True)