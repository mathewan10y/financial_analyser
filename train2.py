import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer
)

# 1. Load the continuous FiQA dataset
print("Loading FiQA dataset...")
dataset = load_dataset("pauri32/fiqa-2018")

# 2. Load the model you JUST trained in Stage 1
# IMPORTANT: Change this to match the output folder from your first script
model_path = "./fine_tuned_financial_model" 

tokenizer = AutoTokenizer.from_pretrained(model_path)

# Load the model, force it to 1 output label (Regression)
print("Loading Stage 1 model and swapping to Regression Head...")
model = AutoModelForSequenceClassification.from_pretrained(
    model_path, 
    num_labels=1, 
    problem_type="regression",
    ignore_mismatched_sizes=True # CRITICAL: Tells PyTorch not to panic when it deletes the old 3-button head
)

# 3. FREEZE THE FOUNDATION LAYERS (Prevent Catastrophic Forgetting)
print("Freezing the bottom 4 layers to protect financial vocabulary...")
for param in model.distilbert.transformer.layer[:4].parameters():
    param.requires_grad = False

# 4. Data Preparation
def tokenize_function(examples):
    # FiQA uses 'sentence' for the text and 'sentiment_score' for the -1.0 to 1.0 float
    tokenized = tokenizer(examples["sentence"], padding="max_length", truncation=True)
    
    # PyTorch Trainer strictly looks for a column named "labels" to calculate the loss
    tokenized["labels"] = examples["sentiment_score"]
    return tokenized

print("Tokenizing dataset...")
tokenized_datasets = dataset.map(tokenize_function, batched=True)

# 5. Training Arguments (Strictly Optimized for 2GB VRAM)
training_args = TrainingArguments(
    output_dir="./synapse_regression_model", # Saves the final model to a NEW folder
    learning_rate=2e-5,            # Keep learning rate very low for Stage 2 to avoid memory shock
    per_device_train_batch_size=4, # Tiny batch size so your GPU doesn't crash
    gradient_accumulation_steps=4, # Accumulates math over 4 steps to simulate a batch size of 16
    num_train_epochs=3,
    weight_decay=0.01,
    logging_steps=10,
    save_strategy="epoch",
    fp16=True,                     # Activates Nvidia tensor cores for speed
)

# 6. Initialize Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
)

# 7. Start Stage 2 Training
print("Beginning Stage 2 Regression Fine-Tuning...")
trainer.train()