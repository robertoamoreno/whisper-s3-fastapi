from fastapi import FastAPI, File, UploadFile, BackgroundTasks
import os
import shutil
import subprocess
import uuid
import boto3
from botocore.exceptions import NoCredentialsError
from pydantic import BaseModel
from typing import Optional, Dict

class FileDetails(BaseModel):
    key: str
    content_type: str

class ResultsDetails(BaseModel):
    key: str

class Metadata(BaseModel):
    speaker: Optional[str]

class TranscriptionRequest(BaseModel):
    model: str
    response_format: str
    file: FileDetails
    results: ResultsDetails
    metadata: Optional[Metadata]


s3_client = boto3.client('s3')


app = FastAPI()


def download_file_from_s3(bucket_name, file_key, download_path):
    try:
        s3_client.download_file(bucket_name, file_key, download_path)
        return True
    except NoCredentialsError:
        print("Credentials not available")
        return False


def get_sample_rate(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT
        )
        sample_rate = int(result.stdout.decode('utf-8').strip())
        return sample_rate
    except Exception as e:
        print(f"Error checking sample rate: {e}")
        return None

def transcribe_audio_task(file_path: str, selected_source_lang: str, whisper_model: str, srt_path: str):
    unique_id = str(uuid.uuid4())
    converted_file_path = f"converted_audio_{unique_id}.wav"
    sample_rate = get_sample_rate(file_path)

    if sample_rate != 16000:
        os.system(f"ffmpeg -i {file_path} -ar 16000 -ac 1 {converted_file_path}")
    else:
        converted_file_path = file_path

    whisper_command = f'./whisper.cpp/main "{converted_file_path}" -t 4 -l "en" -m ./whisper.cpp/models/ggml-large-v3.bin -osrt -of {srt_path}'
    print("Executing Whisper command:", whisper_command)
    os.system(whisper_command)


@app.post("/transcribe_from_bucket/")
async def transcribe_from_bucket(background_tasks: BackgroundTasks, request: TranscriptionRequest):
    file_key = request.file.key
    bucket_name = "recordings"  # Replace with your bucket name

    # Unique ID for the file
    unique_id = str(uuid.uuid4())
    temp_file_path = f"temp_audio_{unique_id}.wav"
    srt_path = f"output_{unique_id}.srt"

    # Download the file from S3
    if download_file_from_s3(bucket_name, file_key, temp_file_path):
        # Start the background task for transcription
        background_tasks.add_task(transcribe_audio_task, temp_file_path, "en", "whisper-large-v3", srt_path)
        return {"message": "Transcription started for file from bucket", "unique_id": unique_id}
    else:
        return {"message": "Failed to download file from S3"}



@app.post("/transcribe/")
async def transcribe_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...), selected_source_lang: str = "en", whisper_model: str = "base"):
    unique_id = str(uuid.uuid4())
    temp_file_path = f"temp_audio_{unique_id}.wav"
    srt_path = f"output_{unique_id}.srt"

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(transcribe_audio_task, temp_file_path, selected_source_lang, whisper_model, srt_path)

    return {"message": "Transcription started", "unique_id": unique_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

