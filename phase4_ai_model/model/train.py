import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from dataset import DrumDataset
from transformer import HatForgeTransformer
import json
import math

BATCH_SIZE = 32
LEARNING_RATE = 1e-4
EPOCHS = 50
WARMUP_STEPS = 500
GRAD_CLIP = 1.0
SAVE_EVERY = 5
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def train():
    os.makedirs("checkpoints", exist_ok=True)
    
    if DEVICE == "cpu":
        print("Warning: Running on CPU. Limiting epochs for test suite.")
        global EPOCHS
        EPOCHS = 2
        
    try:
        train_data = torch.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "train.pt"))
        val_data = torch.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "val.pt"))
    except Exception as e:
        print(f"Error loading data: {e}")
        return
        
    train_ds = DrumDataset(train_data)
    val_ds = DrumDataset(val_data)
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)
    
    if len(train_loader) == 0:
        print("Not enough training data. Exiting.")
        return
        
    model = HatForgeTransformer().to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss(ignore_index=0)
    
    log = []
    best_val_loss = float('inf')
    
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        
        for batch in train_loader:
            ctx = batch["context"].to(DEVICE)
            tgt = batch["target"].to(DEVICE)
            
            tgt_input = tgt[:, :-1]
            tgt_output = tgt[:, 1:]
            
            optimizer.zero_grad()
            logits = model(ctx, tgt_input)
            
            loss = criterion(logits.reshape(-1, 39), tgt_output.reshape(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()
            
            train_loss += loss.item()
            
        train_loss /= len(train_loader)
        
        model.eval()
        val_loss = 0.0
        if len(val_loader) > 0:
            with torch.no_grad():
                for batch in val_loader:
                    ctx = batch["context"].to(DEVICE)
                    tgt = batch["target"].to(DEVICE)
                    tgt_input = tgt[:, :-1]
                    tgt_output = tgt[:, 1:]
                    
                    logits = model(ctx, tgt_input)
                    loss = criterion(logits.reshape(-1, 39), tgt_output.reshape(-1))
                    val_loss += loss.item()
                    
            val_loss /= len(val_loader)
        else:
            val_loss = train_loss
            
        perplexity = math.exp(val_loss)
        
        print(f"Epoch {epoch+1} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val PPL: {perplexity:.4f}")
        
        log.append({"epoch": epoch+1, "train_loss": train_loss, "val_loss": val_loss, "perplexity": perplexity})
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), "checkpoints/best_model.pt")
            
        if (epoch + 1) % SAVE_EVERY == 0:
            torch.save(model.state_dict(), f"checkpoints/model_ep{epoch+1}.pt")
            
    with open("checkpoints/training_log.json", "w") as f:
        json.dump(log, f, indent=2)

if __name__ == "__main__":
    train()
