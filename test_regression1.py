import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 1. Point to your NEW Stage 2 model folder
model_path = "./synapse_regression_model/checkpoint-183" 

print("Loading Synapse Risk Engine...")
# We use the base dictionary because our vocabulary hasn't changed
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
# Load the brain
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# Push to your GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

# 2. The Translation Layer (For the Hackathon Judges)
def interpret_risk_signal(score):
    # Ensure the score stays within bounds just in case of outliers
    score = max(-1.0, min(1.0, score))
    
    # Map the continuous magnitude to dynamic underwriting actions
    if score <= -0.5:
        action = "🛑 AUTO-REJECT / CRITICAL RISK"
    elif score <= -0.1:
        action = "⚠️ INCREASE YIELD / HIGH RISK"
    elif score >= 0.3:
        action = "✅ APPROVE / LOW RISK"
    else:
        action = "🔎 MANUAL REVIEW / NEUTRAL"
        
    return score, action

# 3. The Test Cases (Including the one that failed earlier!)
test_phrases = [
    "The firm filed for Chapter 11 bankruptcy security protection today.", # Let's see if it's still "Neutral"!
    "The company's quarterly revenue dropped by a minor 0.5 percent.",
    "Production increased by 100 percent following the factory expansion.",
    "The board slashed its dividend by 50% amidst a severe cash flow crisis."
]

print("\n--- SYNAPSE MULTI-AGENT INFERENCE TEST ---")
for phrase in test_phrases:
    inputs = tokenizer(phrase, return_tensors="pt", truncation=True, padding=True).to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        # Because num_labels=1, the output is a single continuous float
        raw_score = outputs.logits.item()
        
    final_score, agent_action = interpret_risk_signal(raw_score)
    
    print(f"\nDocument: \"{phrase}\"")
    print(f"Risk Magnitude: {final_score:+.3f}")
    print(f"Agent Action:   {agent_action}")