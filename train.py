import numpy as np
import evaluate
from datasets import load_dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer
)

def main():
    print("Step 1: Loading Financial PhraseBank dataset (Secure Mirror)...")
    # Using a modern, script-free parquet mirror to bypass legacy script security blocks
    dataset = load_dataset("FinanceMTEB/financial_phrasebank", split="train")
    
    # Split the dataset into 80% training and 20% testing
    dataset = dataset.train_test_split(test_size=0.2, seed=42)
    train_data = dataset["train"]
    test_data = dataset["test"]

    print("\nStep 2: Initializing DistilBERT Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")

    def tokenize_function(examples):
        # Using 'text' to match the dataset's column name
        return tokenizer(examples["text"], padding="max_length", truncation=True)

    print("Tokenizing train and test datasets...")
    tokenized_train = train_data.map(tokenize_function, batched=True)
    tokenized_test = test_data.map(tokenize_function, batched=True)

    print("\nStep 3: Loading Pre-trained DistilBERT Model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased", 
        num_labels=3
    )

    print("\nStep 4: Configuring Training Parameters for Quadro P600 (2GB VRAM)...")
    training_args = TrainingArguments(
        output_dir="./results",          
        learning_rate=2e-5,              
        per_device_train_batch_size=4,   # Fits safely inside 2GB VRAM
        per_device_eval_batch_size=4,    
        gradient_accumulation_steps=4,   # Simulates a stable batch size of 16
        num_train_epochs=3,              
        weight_decay=0.01,               
        eval_strategy="epoch",           
        save_strategy="epoch",
        load_best_model_at_end=True,     
        logging_steps=10
    )

    metric = evaluate.load("accuracy")
    
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        return metric.compute(predictions=predictions, references=labels)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_test,
        processing_class=tokenizer,      # Modernized parameter name
        compute_metrics=compute_metrics,
    )

    print("\nStep 5: Beginning Fine-Tuning Execution...")
    # This is when your NVIDIA Quadro P600 will wake up!
    trainer.train()

    print("\nStep 6: Running Final Model Evaluation on Test Data...")
    eval_results = trainer.evaluate()
    print(f"\n>>> Final Test Accuracy: {eval_results['eval_accuracy'] * 100:.2f}% <<<")

    print("\nStep 7: Saving Fine-Tuned Weights and Vocabulary...")
    model.save_pretrained("./fine_tuned_financial_model")
    tokenizer.save_pretrained("./fine_tuned_financial_model")
    print("Model saved successfully to './fine_tuned_financial_model'")

if __name__ == "__main__":
    main()