import os
import glob
import pandas as pd
import torch
import pretty_midi
from tqdm import tqdm
import sys

# Ensure phase1 and phase4 are in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from phase1_prototype.analyze_beat import extract_features
from phase4_ai_model.model.tokenizer import midi_to_tokens, encode_beat_context, VOCAB

def process_gmd(gmd_csv_path: str, gmd_midi_dir: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(gmd_csv_path)
    
    splits = {"train": [], "validation": [], "test": []}
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing GMD"):
        midi_filename = row['midi_filename']
        split = row['split']
        style = row['style'].split('/')[0] # e.g., 'funk/groove1' -> 'funk'
        
        midi_path = os.path.join(gmd_midi_dir, midi_filename)
        if not os.path.exists(midi_path):
            continue
            
        try:
            features = extract_features(midi_path)
            ctx_tokens = encode_beat_context(features)
            
            all_tokens = midi_to_tokens(midi_path, style="unknown")
            hat_tokens = [VOCAB["BOS"]]
            
            i = 1
            while i < len(all_tokens):
                if all_tokens[i] == VOCAB["EOS"]:
                    break
                is_step = False
                for j in range(64):
                    if all_tokens[i] == VOCAB[f"STEP_{j}"]:
                        is_step = True
                        break
                
                if is_step:
                    if i + 2 < len(all_tokens):
                        pitch_tok = all_tokens[i+1]
                        if pitch_tok in [VOCAB["CLOSED_HAT"], VOCAB["OPEN_HAT"], VOCAB["PEDAL_HAT"]]:
                            hat_tokens.extend([all_tokens[i], all_tokens[i+1], all_tokens[i+2]])
                    i += 3
                else:
                    i += 1
            hat_tokens.append(VOCAB["EOS"])
            
            if len(hat_tokens) > 2:
                splits[split].append({
                    "context": ctx_tokens,
                    "target": hat_tokens,
                    "style": VOCAB["STYLE_UNKNOWN"]
                })
        except Exception as e:
            pass
            
    print(f"GMD Processing Complete!")
    print(f"Train: {len(splits['train'])}, Val: {len(splits['validation'])}, Test: {len(splits['test'])}")
    
    torch.save(splits["train"], os.path.join(output_dir, "train.pt"))
    torch.save(splits["validation"], os.path.join(output_dir, "val.pt"))
    torch.save(splits["test"], os.path.join(output_dir, "test.pt"))

if __name__ == "__main__":
    gmd_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase4_ai_model", "data", "groove-v1.0.0-midionly", "groove")
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase4_ai_model", "data", "processed")
    csv_path = os.path.join(gmd_dir, "info.csv")
    
    if os.path.exists(csv_path):
        process_gmd(csv_path, gmd_dir, out_dir)
    else:
        print(f"Cannot find GMD at {csv_path}")
