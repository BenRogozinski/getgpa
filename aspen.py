import requests
from pwinput import pwinput
from bs4 import BeautifulSoup

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

def main():
  aspen_username = input("Aspen username: ")
  aspen_password = pwinput("Aspen password: ")

  print("Logging in to Aspen")

  session = requests.Session()
  
  resp = session.get("https://aspen.cps.edu/aspen/logon.do")
  
  auth_resp = session.post(
    "https://aspen.cps.edu/aspen/logon.do",
    data={
      "org.apache.struts.taglib.html.TOKEN": get_struts(resp.text),
      "userEvent": "930",
      "deploymentId": "aspen",
      "username": aspen_username,
      "password": aspen_password
    },
    allow_redirects=False
  )
  
  if auth_resp.status_code == 302:
    print("Getting transcript information")
    transcript_resp = session.get("https://aspen.cps.edu/aspen/transcriptList.do?navkey=myInfo.trn.list")
    transcript_soup = BeautifulSoup(transcript_resp.text, features="html.parser")
    table = transcript_soup.find("div", id="dataGrid").find("table")
    transcript_rows = table.find_all("tr", class_=["listCell", "listRowHeight"])
    class_info = {}
    for row in transcript_rows:
      cells = row.find_all("td")
      type = cells[2].text.strip()[-1]
      description = cells[4].text.strip()
      class_info[description] = type
    
    print("Getting current grades")
    classes_resp = session.get("https://aspen.cps.edu/aspen/portalClassList.do?navkey=academics.classes.list")
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
    
    print("Calculating GPA\n")
    unweighted, weighted = get_gpa(grades)
    print(f"Un-Weighted GPA: {unweighted:.3f}")
    print(f"Weighted GPA: {weighted:.3f}")
  else:
    print("Authentication failed")
    exit(1)

def get_struts(document: str) -> str:
  soup = BeautifulSoup(document, features="html.parser")
  return soup.find("input", {"name": "org.apache.struts.taglib.html.TOKEN"}).get("value")

def get_gpa(classes: dict[str, dict[str, str]]):
  grade_points_unweighted = []
  grade_points_weighted = []
  for _class in classes:
    unweighted_points = GRADE_POINTS.get(classes[_class]["grade"])
    weighted_points = unweighted_points + TYPE_POINTS.get(classes[_class]["type"])
    grade_points_unweighted.append(unweighted_points)
    grade_points_weighted.append(weighted_points)
  unweighted_gpa = sum(grade_points_unweighted) / len(grade_points_unweighted) * 2
  weighted_gpa = sum(grade_points_weighted) / len(grade_points_weighted) * 2
  return unweighted_gpa, weighted_gpa

if __name__ == "__main__":
  main()