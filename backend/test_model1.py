import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 1. Load model dynamically from Hugging Face Hub (or environment override)
model_path = os.getenv("HF_MODEL_ID", "mathewan10y/synapse-financial-sentiment")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"📦 [Model Loader] Loading model from: {model_path} on {device}...")
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)
model.to(device)
model.eval()

# 2. Test phrases showing different magnitudes
test_phrases = [
    "The company's quarterly revenue dropped by a minor 0.5 percent.",
    "The firm filed for Chapter 11 bankruptcy security protection today.",
    "Production increased by 100 percent following the factory expansion.",
    "The stock ticked up slightly in pre-market trading."
]

print("\n--- Running Local Model Inference ---")
labels = ["Negative", "Neutral", "Positive"]

for phrase in test_phrases:
    inputs = tokenizer(phrase, return_tensors="pt", truncation=True, padding=True).to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        # Convert raw output logits into clean probabilities
        probabilities = torch.softmax(outputs.logits, dim=-1)[0].tolist()
        
    prediction_idx = probabilities.index(max(probabilities))
    print(f"\nText: \"{phrase}\"")
    print(f"Prediction: {labels[prediction_idx]}")
    print(f"Confidence Distribution -> Neg: {probabilities[0]:.2%}, Neu: {probabilities[1]:.2%}, Pos: {probabilities[2]:.2%}")