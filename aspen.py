import requests
from bs4 import BeautifulSoup

GRADE_POINTS = { "F": 0, "D": 0.5, "C": 1, "B": 1.5, "A": 2 }
TYPE_POINTS = { "R": 0, "H": 0.5, "A": 1 }

class Aspen:
  def __init__(self, username, password):
    self.session = requests.Session()
    self.session.hooks = {
      "response": lambda r, *args, **kwargs: r.raise_for_status()
    }
    logon_resp = self.session.get("https://aspen.cps.edu/aspen/logon.do")
    logon_soup = BeautifulSoup(logon_resp.text, features="html.parser")
    struts_token = logon_soup.find(
      "input",
      {"name": "org.apache.struts.taglib.html.TOKEN"}
    ).get("value")

    auth_resp = self.session.post(
      "https://aspen.cps.edu/aspen/logon.do",
      data={
        "org.apache.struts.taglib.html.TOKEN": struts_token,
        "userEvent": "930",
        "deploymentId": "aspen",
        "username": username,
        "password": password
      },
      allow_redirects=False
    )
    if auth_resp.status_code != 302:
      raise ValueError("Authentication failed")
  
  def get_transcript_classes(self) -> dict[str, str]:
    transcript_resp = self.session.get(
      "https://aspen.cps.edu/aspen/transcriptList.do?navkey=myInfo.trn.list"
    )
    transcript_table = self._parse_datagrid(transcript_resp.text)
    class_ids = {}
    for row in transcript_table:
      class_ids[row[4]] = row[2]
    return class_ids
  
  def get_current_grades(self) -> dict[str, str]:
    classes_resp = self.session.get(
      "https://aspen.cps.edu/aspen/portalClassList.do?navkey=academics.classes.list"
    )
    classes_table = self._parse_datagrid(classes_resp.text)
    class_grades = {}
    for row in classes_table:
      if row[7]:
        class_grades[row[1]] = row[7].split(" ")[-1]
    return class_grades
  
  @staticmethod
  def _parse_datagrid(document: str) -> list[list[str]]:
    soup = BeautifulSoup(document, features="html.parser")
    table = soup.find("div", id="dataGrid").find("table")
    rows = table.find_all("tr", class_=["listCell", "listRowHeight"])
    row_data = []
    for row in rows:
      row_data.append([x.text.strip() for x in row.find_all("td")])
    return row_data