import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_USE_PLUGGABLE_DEVICE"] = "0"  # optional but safer
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # optional: suppress GPU warnings
import numpy as np
from fastapi import FastAPI, File, UploadFile
import uvicorn
from io import BytesIO
from PIL import Image
import tensorflow as tf
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI  # Import the new OpenAI client
import requests

# Load environment variables
load_dotenv()
#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure your GPT API key is set in the .env file
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Ensure your DeepSeek API key is set in the .env file

# Initialize OpenAI client
#client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load TensorFlow model
MODEL = tf.keras.models.load_model(r'D:\project\potatoes_disease\saved_models\2.h5')

CLASS_NAMES = ["Early Blight", "Late Blight", "Healthy"]

@app.get("/ping")
async def ping():
    return {"message": "Hello, I am live Lesi!"}

def read_file_as_image(data) -> np.ndarray:
    image = np.array(Image.open(BytesIO(data)))
    return image

# Function to get feedback from GPT API
'''def get_gpt_feedback(predicted_class):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure the correct model name
            messages=[
                {"role": "system", "content": "You are a helpful assistant providing insights about potato plant diseases."},
                {"role": "user", "content": f"Provide detailed information about a potato plant classified as {predicted_class}."}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content  # Updated response handling
    except Exception as e:
        
        return f"Error fetching GPT feedback: {str(e)}"
'''

# Function to call the DeepSeek API
def get_deepseek_feedback(predicted_class):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a agricultural expert..."},
            {"role": "user", "content": f"Explain potato disease: {predicted_class}"}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"DeepSeek Error: {str(e)}"


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # Read image once
    image_data = await file.read()
    image = read_file_as_image(image_data)

    # Model prediction
    img_batch = np.expand_dims(image, 0)
    predictions = MODEL.predict(img_batch)
    predicted_class = CLASS_NAMES[np.argmax(predictions[0])]
    confidence = float(np.max(predictions[0]))

    # Get DeepSeek feedback
    deepseek_feedback = get_deepseek_feedback(predicted_class)

    return {
        'class': predicted_class,
        'confidence': confidence,
        'ai_feedback': deepseek_feedback
    }

if __name__ == "__main__":
    uvicorn.run(app, host='localhost', port=8000)
