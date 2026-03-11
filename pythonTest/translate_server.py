from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

app = FastAPI()

# Load once at startup
model_id = "facebook/m2m100_418M"  # More reliable multilingual model
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForSeq2SeqLM.from_pretrained(model_id, device_map="auto")

class TranslationRequest(BaseModel):
    text: str
    target_lang: str  # e.g. "ja", "fr", "hi"

@app.post("/translate")
def translate(req: TranslationRequest):
    prompt = f"<2{req.target_lang}> {req.text}"
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(**inputs, max_length=256)
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return {"translation": result}