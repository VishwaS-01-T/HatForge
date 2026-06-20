import os
import glob
import random
import torch
from torch.utils.data import Dataset
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "phase1_prototype"))
from analyze_beat import extract_features
from tokenizer import midi_to_tokens, encode_beat_context, VOCAB

class DrumDataset(Dataset):
    def __init__(self, data_list, max_seq_len: int = 256):
        self.data = data_list
        self.max_seq_len = max_seq_len
        
    def __len__(self) -> int:
        return len(self.data)
        
    def __getitem__(self, idx: int) -> dict:
        item = self.data[idx]
        
        ctx = item["context"][:self.max_seq_len]
        tgt = item["target"][:self.max_seq_len]
        
        ctx = ctx + [VOCAB["PAD"]] * (self.max_seq_len - len(ctx))
        tgt = tgt + [VOCAB["PAD"]] * (self.max_seq_len - len(tgt))
        
        return {
            "context": torch.tensor(ctx, dtype=torch.long),
            "target": torch.tensor(tgt, dtype=torch.long),
            "style": torch.tensor(item["style"], dtype=torch.long)
        }

def build_dataset(raw_dir: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    midi_files = glob.glob(os.path.join(raw_dir, "*.mid"))
    
    data_list = []
    
    for f in midi_files:
        try:
            features = extract_features(f)
            ctx_tokens = encode_beat_context(features)
            
            all_tokens = midi_to_tokens(f, features.estimated_genre)
            hat_tokens = [VOCAB["BOS"]]
            
            i = 1
            while i < len(all_tokens):
                if all_tokens[i] == VOCAB["EOS"]:
                    break
                if VOCAB["STEP_0"] <= all_tokens[i] <= VOCAB["STEP_15"]:
                    if i + 2 < len(all_tokens):
                        pitch_tok = all_tokens[i+1]
                        if pitch_tok in [VOCAB["CLOSED_HAT"], VOCAB["OPEN_HAT"], VOCAB["PEDAL_HAT"]]:
                            hat_tokens.extend([all_tokens[i], all_tokens[i+1], all_tokens[i+2]])
                    i += 3
                else:
                    i += 1
            hat_tokens.append(VOCAB["EOS"])
            
            style_tok = VOCAB.get(f"STYLE_{features.estimated_genre.upper()}", VOCAB["STYLE_UNKNOWN"])
            
            data_list.append({
                "context": ctx_tokens,
                "target": hat_tokens,
                "style": style_tok
            })
        except Exception as e:
            print(f"Error processing {f}: {e}")
            
    random.shuffle(data_list)
    n = len(data_list)
    train_end = int(0.8 * n)
    val_end = int(0.9 * n)
    
    train_data = data_list[:train_end]
    val_data = data_list[train_end:val_end]
    test_data = data_list[val_end:]
    
    torch.save(train_data, os.path.join(output_dir, "train.pt"))
    torch.save(val_data, os.path.join(output_dir, "val.pt"))
    torch.save(test_data, os.path.join(output_dir, "test.pt"))
    
    print(f"Total samples: {n}")
    print(f"Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")

if __name__ == "__main__":
    build_dataset(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
    )
