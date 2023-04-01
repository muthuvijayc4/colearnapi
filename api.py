from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pymongo
import random
import string
from bson.objectid import ObjectId
import bson.binary
from io import BytesIO
from starlette.responses import StreamingResponse


client = pymongo.MongoClient("mongodb+srv://ymuthuvijay5:muthuselvapubg@colearn.tbzflt2.mongodb.net/?ssl=true&ssl_cert_reqs=CERT_NONE&retryWrites=true&w=majority")
db = client["colearn"]


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home():
    return {"Hello": "World"}


@app.post("/createroom")
async def createroom(data: dict):
    collection = db["room"]
    user_collection = db["users"]
    random_number = random.randint(100000, 999999)
    
    while collection.find_one({"_id": random_number}):
        random_number = random.randint(100000, 999999)
    
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(6))

    document = {"_id": random_number, "password": password, "name": data["name"], "status": True}
    user_collection.insert_one({"roomID": random_number, "name": data["name"]})
    collection.insert_one(document)
    return document


@app.post("/room")
async def getroom(data: dict):
    collection = db["room"]
    room = collection.find_one({"_id": int(data["roomID"]), "password": data["password"]})

    if room:
        if not room["status"]:
            return {"result": "yes"}
        user_collection = db["users"]
        user = user_collection.find_one({"roomID": int(data["roomID"]), "name": data["name"]})
        if not user:
            user_collection.insert_one({"roomID": int(data["roomID"]), "name": data["name"]})
            return {"result": True}
        return {"result": "no"}
    return {"result": False}


@app.post("/addquestion")
async def create_item(document: dict):
    collection = db["question"]
    collection.insert_one(document)
    return {"result": True}


@app.get("/getquestions")
async def get_questions(roomID: int):
    collection = db["question"]
    documents = []
    for document in collection.find({'roomID': roomID}):
        documents.append(document)
    for i in range(len(documents)):
        documents[i]["_id"] = str(documents[i]["_id"])
    return {"result": documents}


@app.post("/updateanswer")
async def update_answer(data: dict):
    collection = db["question"]
    id = ObjectId(data["id"])
    answer = data["answer"]
    cnt = collection.update_one({"_id": id}, {"$set": {"answer": answer}})
    return {"result": True}


@app.post("/sendmessage")
async def send_message(data: dict):
    collection = db["chat"]
    collection.insert_one(data)
    return {"result": True}


@app.get("/getmessages")
async def get_messages(roomID: int):
    collection = db["chat"]
    documents = []
    for document in collection.find({'roomID': roomID}):
        documents.append(document)
    for i in range(len(documents)):
        del documents[i]["_id"]
    return {"result": documents}


@app.post("/uploadfile")
async def upload_file(file: UploadFile = File(...), roomID: str = Form(...)):
    collection = db["files"]
    contents = await file.read()
    file_dict = {
        "filename": file.filename.replace(" ", ""),
        "contents": contents,
        "roomID": int(roomID)
    }
    collection.insert_one(file_dict)
    return {"result": True}


@app.get("/getfiles")
async def get_files(roomID: int):
    collection = db["files"]
    documents = []
    for document in collection.find({'roomID': roomID}):
        documents.append(document)
    for i in range(len(documents)):
        del documents[i]["_id"]
        del documents[i]["roomID"]
        del documents[i]["contents"]
    return {"result": documents}


@app.get("/getfile")
async def get_file(filename: str, roomID: int):
    collection = db["files"]
    file = collection.find_one({"filename": filename, "roomID": roomID})
    contents = file["contents"]
    file_like = BytesIO(contents)
    return StreamingResponse(file_like, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={file['filename']}"})


@app.post("/closeroom")
async def close_room(data: dict):
    collection = db["room"]
    files = db["files"]
    question = db["question"]
    
    backup_data = ""

    room = collection.find_one({"_id": data["roomID"]})
    roomID = room["_id"]
    password = room["password"]
    roomcreator = room["name"]

    backup_data += f"Room details:\nID: {roomID}\nPassword: {password}\nCreator: {roomcreator}\n\nQuestions:\n"

    questions = question.find({"roomID": data["roomID"]})
    for q in questions:
        if q["questiontype"] == "MCQ":
            que = q["question"]
            o1 = q["option1"]
            o2 = q["option2"]
            o3 = q["option3"]
            o4 = q["option4"]
            answer = "Not selected"
            if q["answer"] != -1:
                answer = "Option " + str(q["answer"])
            ques = f"Type: MCQ\nQuestion: {que}\nOption 1: {o1}\nOption 2: {o2}\nOption 3: {o3}\nOption 4: {o4}\nAnswer: {answer}\n"
            backup_data += ques
        else:
            que = q["question"]
            answer = q["answer"]
            ques = f"Type: Descriptive\nQuestion: {que}\nAnswer: {answer}\n"
            backup_data += ques

    binary_data = bson.binary.Binary(backup_data.encode())

    files.insert_one({"filename": "backup.txt", "contents": binary_data, "roomID": data["roomID"]})

    collection.update_one({"_id": data["roomID"]}, {"$set": {"status": False}})
    return {"result": True}


@app.get("/getcreator")
async def get_creator(roomID: int):
    collection = db["room"]
    document = collection.find_one({'_id': roomID})
    return {"name": document["name"]}


@app.post("/getroomstatus")
async def get_room_status(data: dict):
    collection = db["room"]
    document = collection.find_one({"_id": data["roomID"]})
    return {"status": document["status"]}
