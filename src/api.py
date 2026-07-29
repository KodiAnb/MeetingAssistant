from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import ollama
import pydantic
from pydantic import BaseModel
import whisper
import numpy as np
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import subprocess
import atexit
from sqlmodel import SQLModel, Field,create_engine,Session,Relationship,select
import base64
from email.mime.text import MIMEText
from sqlalchemy import create_engine, Column, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY,JSONB
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg://kodianbarasu@localhost:5432/assistant"
engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)

class Meeting(SQLModel, table=True):
    __tablename__ = "meeting"

    meeting_id: int | None = Field(default=None, primary_key=True)
    title: str
    transcript: str
    google_document: list[dict] = Field(sa_column=Column(JSONB))
    google_slides: list[dict] = Field(sa_column=Column(JSONB))
    calendar: list[dict] = Field(sa_column=Column(JSONB))
    gmail: list[dict] = Field(sa_column=Column(JSONB))
    miscellaneous: list[dict] = Field(sa_column=Column(JSONB))


app = FastAPI()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

scopes = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/presentations',  # new
]
service_account_file = 'credentials.json'

def get_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret_two.json', scopes)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

creds = get_credentials()

slides_service = build('slides', 'v1', credentials=creds)
docs_service = build('docs', 'v1', credentials=creds)
tasks_service = build('tasks', 'v1', credentials=creds)
gmail_service = build('gmail', 'v1', credentials=creds)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Define your individual schemas
class Summary(pydantic.BaseModel):
    create_summary: str

prompt = f"""You are extracting actionable to-do items from a video meeting transcript. They must have a unique name between 2-5 words with each description.

Each item must be in a dictionary format with the name of the task as the key and a SHORT ACTION TASK (an imperative instruction someone needs to do), NOT a summary of what was discussed as the value.

GOOD examples (tasks):
- "Budget: Send the Q3 budget draft to finance team"
-  Organize tasks : Summay of key decisions and who is responsible for follow-up tasks
- "Client Scheduling: Schedule follow-up call with client for next Tuesday"
- "Update Slidedeck: Update the onboarding slide deck with new pricing"

BAD examples (summaries - do NOT do this):
- "Talking to the team: The team discussed the Q3 budget and its implications"
- "Slide 9: Write about the pros and cons of our company"
- "name: description"
- "description: "
- "There was a conversation about scheduling a follow-up: There was a conversation about scheduling a follow-up"
- "Pricing changes were mentioned during the meeting: up to 2%."

Extract only real, actionable tasks in this style. If no clear action was mentioned for a category, return an empty dictionary pair for that category rather than inventing a summary.

Sort each task into one of the most relevant Google Workspace category: Google Docs,Slides,Gmail,Calendar, and Miscellaneous.

Transcript:
"""

class ActionList(pydantic.BaseModel):
    
    google_document: dict[str, str] = pydantic.Field(
        description="Name of the task as well as short task descriptions for items that should go into a Google Doc, e.g. 'Summary: Write up meeting summary for stakeholders'"
    ) 
    google_slides: dict[str, str] = pydantic.Field(
        description="Name of the task as well as short task descriptions for items that should become slides, e.g. 'Compare: Create slide comparing Q3 vs Q4 metrics'"
    ) 
    gmail: dict[str, str] = pydantic.Field(
        description="Name of the task as well as short task descriptions for emails that need to be sent, e.g. 'Budget Email: Email John the updated budget by Friday'"
    ) 
    calendar: dict[str, str] = pydantic.Field(  # also fixed the typo: "calender" -> "calendar"
        description="Name of the task as well as short task descriptions for events/meetings that need to be scheduled, e.g. 'Team scheduling: Schedule follow-up with design team next week'"
    )
    miscellaneous: dict[str, str] = pydantic.Field(
        description="Any other actionable to-do items that don't fit the above categories"
    ) 

# 3. Create a parent container schema combining both
class ProcessedTranscript(pydantic.BaseModel):
    summary_data: Summary
    action_data: ActionList



@app.post("/upload")
async def upload(video: UploadFile = File(...)):

    contents = await video.read()

    with open(video.filename, "wb") as f:
        f.write(contents)

    model = whisper.load_model("base")

    result = model.transcribe(video.filename)
    transp = result["text"]

    mod = "gemma4:e4b"

    answer = ollama.chat(
        model=mod,
        messages=[
            {
                "role": "user", 
                "content": prompt + transp
            }
        ],
        options={
            "num_ctx": 8192,
            "num_predict": 12300,
            "temperature": .2  # increase max output tokens (default is often too low, sometimes 128-512)
        },
        format=ActionList.model_json_schema()
    )
    #Ensure the code stays awake
    caffeinate_process = subprocess.Popen(['caffeinate', '-dims'])

    # 5. Validate the nested JSON structure
    final_result = ActionList.model_validate_json(answer.message.content)
    print(final_result)
    parent_list = []

    with Session(engine) as session:
        for dict in final_result:
            print(dict)
            lis = []
            tasks = dict[1]
            for x, y in tasks.items():
                lis.append({'name':x, 'description':y})
                
            parent_list.append(lis)
        print(parent_list)
        meeting = Meeting(title=video.filename, transcript=transp, google_document=parent_list[0], google_slides=parent_list[1],calendar=parent_list[2],gmail=parent_list[3], miscellaneous=parent_list[4] )
        session.add(meeting)
        session.commit()
        session.refresh(meeting)


    #Kill the wake
    atexit.register(caffeinate_process.terminate)
    return {
        "result": final_result,
        "id": meeting.meeting_id
    }

class TaskRequest(BaseModel): #Variables must match post request in client
    Name: str
    Description: str
    Suite: int

@app.post("/gsuite")
async def handle_gsuite(info_list: TaskRequest):
    if (info_list.Suite == 0):
        drive_service = build('drive', 'v3', credentials=creds)

        doc = docs_service.documents().create(body={'title': info_list.Name}).execute()
        doc_id = doc.get('documentId')

        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{'insertText': {'location': {'index': 1}, 'text': info_list.Description}}]}
        ).execute()

        return {
                "url": f"https://docs.google.com/document/d/{doc_id}/edit"
        }
    elif (info_list.Suite == 1):
        presentation = slides_service.presentations().create(body={'title': info_list.Name}).execute()
        presentation_id = presentation['presentationId']

        requests = [
            {
                'createSlide': {
                    'objectId': 'slide_1',
                    'slideLayoutReference': {'predefinedLayout': 'TITLE_AND_BODY'},
                    'placeholderIdMappings': [
                        {
                            'layoutPlaceholder': {'type': 'TITLE'},
                            'objectId': 'slide_1_title'
                        },
                        {
                            'layoutPlaceholder': {'type': 'BODY'},
                            'objectId': 'slide_1_body'
                        }
                        
                    ]
                }
            }
        ]

        requests.append({
            'insertText': {
                'objectId': 'slide_1_title',
                'text': info_list.Name
            }
        })
        requests.append({
            'insertText': {
                'objectId': 'slide_1_body',
                'text': info_list.Description
            }
        })
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        return {
                "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit"
                }
    elif (info_list.Suite == 2):
        task = {
            'title': info_list.Name,
            'notes': info_list.Description,
        }

        tasks_service.tasks().insert(tasklist='@default', body=task).execute()

        return{
            "url": f'https://tasks.google.com/'

        }
    elif (info_list.Suite == 3):

        message = MIMEText(info_list.Description)
        message['subject'] = info_list.Name
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        mail = gmail_service.users().drafts().create(userId='me',body={'message':{'raw':raw}}).execute()
        mail_id = mail.get('id')

        return{
            'url': f'https://mail.google.com/mail/u/0/#drafts?compose={mail_id}'
        }
    else:
        return {"error": f"Unsupported suite type: {info_list.Suite}"}


def get_meeting(db: Session, meeting_id: int):
    return db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/upload-complete/{meeting_id}")
def uploadcomplete(meeting_id: int, db: Session = Depends(get_db)): #Depends handles when to run "finally" and cleans up
    print(meeting_id)
    meeting = get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)


