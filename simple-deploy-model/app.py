import uvicorn
import pandas as pd
import pickle
from fastapi import FastAPI
from pydantic import BaseModel

# Load the model
with open('model.pickle', 'rb') as f:
    model = pickle.load(f)

# Define a request model
class PredictRequest(BaseModel):
    feature_1: str

app = FastAPI()

@app.get('/')
def index():
    return {'message': 'Hey look it\'s working'}

@app.post('/predict') 
def predict(request: PredictRequest):
    # Create a DataFrame with the required column name 'ds'
    features = pd.DataFrame({'ds': [request.feature_1]})
    # Make predictions using the Prophet model
    prediction = model.predict(features)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict(orient='records')
    return {'output': prediction}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=80)
