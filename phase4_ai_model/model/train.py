import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from phase4_ai_model.model.dataset import DrumDataset
from phase4_ai_model.model.transformer import HatForgeTransformer
from phase4_ai_model.model.tokenizer import VOCAB_SIZE
import json
import math

BATCH_SIZE = 32
LEARNING_RATE = 1e-4
EPOCHS = 50
WARMUP_STEPS = 500
GRAD_CLIP = 1.0
SAVE_EVERY = 5
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def calc_edit_distance(seq1, seq2):
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i-1] == seq2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n]

def compute_rhythm_similarity(logits, targets):
    preds = logits.argmax(dim=-1)
    total_sim = 0.0
    count = 0
    for p, t in zip(preds, targets):
        valid_t = t[t != 0].tolist()
        valid_p = p[:len(valid_t)].tolist()
        if len(valid_t) > 0:
            ed = calc_edit_distance(valid_p, valid_t)
            sim = 1.0 - (ed / max(len(valid_t), len(valid_p)))
            total_sim += max(0.0, sim)
            count += 1
    return total_sim / max(1, count)

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
        
    model = HatForgeTransformer(vocab_size=VOCAB_SIZE).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss(ignore_index=0)
    
    log = []
    best_val_loss = float('inf')
    patience = 5
    patience_counter = 0
    
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
            
            loss = criterion(logits.reshape(-1, VOCAB_SIZE), tgt_output.reshape(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()
            
            train_loss += loss.item()
            
        train_loss /= len(train_loader)
        
        model.eval()
        val_loss = 0.0
        val_similarity = 0.0
        if len(val_loader) > 0:
            with torch.no_grad():
                for batch in val_loader:
                    ctx = batch["context"].to(DEVICE)
                    tgt = batch["target"].to(DEVICE)
                    tgt_input = tgt[:, :-1]
                    tgt_output = tgt[:, 1:]
                    
                    logits = model(ctx, tgt_input)
                    loss = criterion(logits.reshape(-1, VOCAB_SIZE), tgt_output.reshape(-1))
                    val_loss += loss.item()
                    
                    sim = compute_rhythm_similarity(logits, tgt_output)
                    val_similarity += sim
                    
            val_loss /= len(val_loader)
            val_similarity /= len(val_loader)
        else:
            val_loss = train_loss
            val_similarity = 0.0
            
        perplexity = math.exp(val_loss)
        
        print(f"Epoch {epoch+1} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val PPL: {perplexity:.4f} | Val Sim: {val_similarity:.4f}")
        
        log.append({
            "epoch": epoch+1, 
            "train_loss": train_loss, 
            "val_loss": val_loss, 
            "perplexity": perplexity,
            "val_similarity": val_similarity
        })
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), "checkpoints/best_model.pt")
        else:
            patience_counter += 1
            
        if (epoch + 1) % SAVE_EVERY == 0:
            torch.save(model.state_dict(), f"checkpoints/model_ep{epoch+1}.pt")
            
        if patience_counter >= patience:
            print(f"Early stopping triggered at epoch {epoch+1}.")
            break
            
    with open("checkpoints/training_log.json", "w") as f:
        json.dump(log, f, indent=2)

if __name__ == "__main__":
    train()
