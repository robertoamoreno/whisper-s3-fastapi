# whisper-s3-fastapi
Whisper With s3 and FastAPI 


Curl Example Upload File 

curl --location 'http://localhost:8000/transcribe/' \
--header 'accept: application/json' \
--form 'file=@"jfk.wav"' \
--form 'selected_source_lang="en"' \
--form 'whisper_model="base"'


Curl Example Grab file from S3 

curl --location 'http://localhost:8000/transcribe_from_bucket/' \
--header 'accept: application/json' \
--header 'Content-Type: application/json' \
--data '{
  "model": "openai/whisper-large-v3",
  "response_format": "srt",
  "file": {
    "key": "C7cde0.wav",
    "content_type": "audio/wav"
  },
  "results": {
    "key": "23289.json"
  },
  "metadata": {
    "speaker": "Example"
  }
}'
