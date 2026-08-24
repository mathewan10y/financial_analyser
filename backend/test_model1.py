import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 1. Load your newly trained model  and tokenizer
# (Change './results' to match the output folder specified in your train.py)
model_path = "./fine_tuned_financial_model" 
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# Ensure it uses your GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
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