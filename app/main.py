# FastAPI related imports and Machine learning related.
import pathlib
import shutil
import numpy as np
import tensorflow as tf
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
# Authentication related imports.
from sqlalchemy.orm import Session

# PostgreSQL database import statements. (Autogenerate tables).
import app.db.model as model
from app.auth import AuthHandler
from app.db import crud
from app.db.crud import insert_user
from app.db.database import get_db, engine
from app.db.model import User, Classification
from app.db.schema import CreateUsers, CreateClassification
from app.schemas import AuthDetails

model.Base.metadata.create_all(bind=engine)

from app.methods.audio_methods import preprocess_dataset, audio_labels, create_upload_file

app = FastAPI()

auth_handler = AuthHandler()

# Store all the username from the db when application start.
users = []
audio_model = tf.keras.models.load_model('app/models/audio/audio_model.h5')
CLASS_NAMES_Plesispa = ['clean', 'infected']

# ----------------------------------------------------------------------------
# Created By  : Anawaratne M.A.N.A.
# Created Date: 2022/7/18
# version ='1.0'
# ---------------------------------------------------------------------------
""" JWT Auth related endpoints """


# ---------------------------------------------------------------------------
# Status : Work in Progress.
# ---------------------------------------------------------------------------

# User registration (With password hashing).
@app.post('/register', status_code=201)
def register(auth_details: CreateUsers, db: Session = Depends(get_db)):
    db_user = crud.get_by_name(name=auth_details.username, db=db)
    if db_user:
        raise HTTPException(status_code=400, detail="Username is taken")
    hashed_password = auth_handler.get_password_hash(auth_details.password)
    auth_details.password = hashed_password
    response = insert_user(details=auth_details, db=db)
    return response


# User login with JWT auth.
@app.post('/login')
def login(auth_details: AuthDetails, db: Session = Depends(get_db)):
    user = None
    db_user = crud.get_by_name(name=auth_details.username, db=db)
    if db_user:
        user = User(
            name=db_user.name,
            hash_password=db_user.hash_password
        )
        print(user.hash_password)
    if (user is None) or (not auth_handler.verify_password(auth_details.password, user.hash_password)):
        raise HTTPException(status_code=401, detail='Invalid username and, or password')
    token = auth_handler.encode_token(user.name)
    return {'token': token}


# Testing endpoint with JWT (Protected routes).
@app.get("/ping")
async def ping(db: Session = Depends(get_db)):
    return "Something"


# Testing endpoint with JWT (Protected routes).
@app.get("/protect/ping", dependencies=[Depends(auth_handler.auth_wrapper)])
async def ping():
    return "Hello, I am alive (Protected)"


# ----------------------------------------------------------------------------
# Created By  : @Team
# Created Date: -
# version ='1.0'
# ---------------------------------------------------------------------------
""" Machine learning model related endpoints """


# ---------------------------------------------------------------------------
# Status : Work in Progress.
# ---------------------------------------------------------------------------

@app.post("/audio")
async def audio_predict(
        # Save the file.
        file: UploadFile = File(...)
):
    print(await create_upload_file(await file.read())['info'])
    audio = preprocess_dataset(await file.read())
    audio_batch = np.expand_dims(audio, 0)
    predictions = audio_model.predict(audio_batch)
    predicted_class = audio_labels[np.argmax(predictions[0])]
    confidence = np.max(predictions[0])
    return {
        'class': predicted_class,
        'confidence': float(confidence)
    }


@app.post("/upload-file/")
async def create_upload_file(file: UploadFile = File(...)):
    working_dir = pathlib.Path().absolute()
    file_location = f"{working_dir}\\app\\temp\\{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    audio = preprocess_dataset([str(file_location)])
    for spectrogram, label in audio.batch(1):
        predictions = audio_model(spectrogram)
        predicted_class = audio_labels[np.argmax(predictions[0])]
        confidence = np.max(predictions[0])
        return {
            'class': predicted_class,
            'confidence': float(confidence)
        }


# ----------------------------------------------------------------------------
# Created By  : Anawaratne M.A.N.A.
# Created Date: 2022/7/19
# version ='1.0'
# ---------------------------------------------------------------------------
""" Database CRUD related endpoints - TEST """


# ---------------------------------------------------------------------------
# Status : Work in Progress. Remove after working.
# ---------------------------------------------------------------------------

# Database INSERT  (Related to users) - Testing method / Hash the password.
@app.post('/add-user')
def add_user(details: CreateUsers, db: Session = Depends(get_db)):
    to_create = User(
        name=details.username,
        hash_password=details.password
    )
    db.add(to_create)
    db.commit()
    return {
        "success": True,
        "create_id": to_create.id
    }


# Database GET (Related to user)
@app.get("/get-user")
def get_by_id(id: int, db: Session = Depends(get_db)):
    return db.query(User).filter(User.id == id).first()


# Database GET-ALL (Related to user) - TEST
@app.get("/get-users")
def get_by_id(db: Session = Depends(get_db)):
    return db.query(User).offset(0).limit(100).all()


# Database GET-ALL (Related to user) - TEST
@app.get("/get-users-name")
def get_by_name(name: str, db: Session = Depends(get_db)):
    return db.query(User).filter(User.name == name).first()


# Database DELETE (Related to user) - @Implement here.

# Database UPDATE (Related to user) - @Implement here.

# ----------------------------------------------------------------------------
# Created By  : Anawaratne M.A.N.A.
# Created Date: 2022/7/19
# version ='1.0'
# ---------------------------------------------------------------------------
""" Classification history related. """


# Database INSERT (Related to classification)
@app.post('/add-classification')
def add_classification(details: CreateClassification, db: Session = Depends(get_db)):
    to_create = Classification(
        category=details.classification_category,
        filename=details.classification_filename,
        label=details.classification_label,
        confidence=details.confidence_value,
        date=details.date,
        user_id=details.user_id
    )

    db.add(to_create)
    db.commit()
    return {
        "success": True,
        "create_id": to_create.id
    }


# Database GET (Related to classification)
@app.get("/get-classification")
def get_by_id(db: Session = Depends(get_db)):
    return db.query(Classification).offset(0).limit(100).all()

# ---------------------------------------------------------------------------
# Status : Work in Progress.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host='localhost', port=8000)
