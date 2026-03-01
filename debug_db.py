import app
from app import db, Interview, Company

with app.app.app_context():
    interviews = Interview.query.all()
    print(f"Total Interviews: {len(interviews)}")
    for i in interviews:
        print(f"ID: {i.id}, Candidate: {i.candidate_name}, Email: {i.candidate_email}, Status: {i.status}")
        print(f"Token: {i.token}")
        print(f"Report: {i.result_report[:50] if i.result_report else 'None'}")
        print("-" * 20)
