import pretty_midi
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "phase1_prototype"))
from analyze_beat import BeatFeatures

VOCAB = {
    "PAD": 0,
    "BOS": 1,      
    "EOS": 2,      
    "KICK": 3,     
    "KICK2": 4,    
    "SNARE": 5,    
    "SNARE2": 6,   
    "CLOSED_HAT": 7,   
    "OPEN_HAT": 8,     
    "PEDAL_HAT": 9,    
}

# Time tokens
for i in range(16):
    VOCAB[f"STEP_{i}"] = 10 + i

# Velocity tokens
for i in range(1, 9):
    VOCAB[f"VEL_{i}"] = 25 + i

VOCAB["STYLE_TRAP"] = 34
VOCAB["STYLE_DRILL"] = 35
VOCAB["STYLE_BOOMBAP"] = 36
VOCAB["STYLE_JERSEY"] = 37
VOCAB["STYLE_UNKNOWN"] = 38

VOCAB_SIZE = 39

PITCH_TO_TOKEN = {
    36: "KICK", 35: "KICK2",
    38: "SNARE", 40: "SNARE2",
    42: "CLOSED_HAT", 46: "OPEN_HAT", 44: "PEDAL_HAT"
}

TOKEN_TO_PITCH = {
    "KICK": 36, "KICK2": 35,
    "SNARE": 38, "SNARE2": 40,
    "CLOSED_HAT": 42, "OPEN_HAT": 46, "PEDAL_HAT": 44
}

def velocity_to_token(vel: int) -> str:
    level = max(1, min(8, (vel // 16) + 1))
    return f"VEL_{level}"

def token_to_velocity(tok: str) -> int:
    level = int(tok.split("_")[1])
    return level * 16 - 8

def midi_to_tokens(midi_path: str, style: str = "unknown") -> list[int]:
    midi = pretty_midi.PrettyMIDI(midi_path)
    drum_track = None
    for inst in midi.instruments:
        if inst.is_drum:
            drum_track = inst
            break
    if not drum_track:
        return [VOCAB["BOS"], VOCAB["EOS"]]
        
    try:
        times, tempos = midi.get_tempo_changes()
        bpm = float(tempos[0]) if len(tempos) > 0 else 120.0
    except:
        bpm = 120.0
        
    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = 4 * seconds_per_beat
    seconds_per_16th = seconds_per_bar / 16.0
    
    style_tok = VOCAB.get(f"STYLE_{style.upper()}", VOCAB["STYLE_UNKNOWN"])
    tokens = [VOCAB["BOS"], style_tok]
    
    for note in drum_track.notes:
        if note.pitch not in PITCH_TO_TOKEN:
            continue
            
        bar_num = int(note.start / seconds_per_bar)
        start_in_bar = note.start % seconds_per_bar
        step = int(round(start_in_bar / seconds_per_16th)) % 16
        
        # We only consider first bar for simplicity in this dataset
        if bar_num > 0:
            continue
            
        pitch_tok = PITCH_TO_TOKEN[note.pitch]
        vel_tok = velocity_to_token(note.velocity)
        
        tokens.extend([
            VOCAB[f"STEP_{step}"],
            VOCAB[pitch_tok],
            VOCAB[vel_tok]
        ])
        
    tokens.append(VOCAB["EOS"])
    return tokens

def tokens_to_midi(tokens: list[int], bpm: float) -> pretty_midi.PrettyMIDI:
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    instrument = pretty_midi.Instrument(program=0, is_drum=True, name="HatForge AI")
    
    INV_VOCAB = {v: k for k, v in VOCAB.items()}
    
    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = 4 * seconds_per_beat
    seconds_per_16th = seconds_per_bar / 16.0
    duration = seconds_per_16th * 0.5
    
    i = 0
    while i < len(tokens):
        tok_val = tokens[i]
        if tok_val not in INV_VOCAB:
            i += 1
            continue
            
        tok_str = INV_VOCAB[tok_val]
        
        if tok_str.startswith("STEP_"):
            if i + 2 < len(tokens):
                pitch_tok_val = tokens[i+1]
                vel_tok_val = tokens[i+2]
                
                if pitch_tok_val in INV_VOCAB and vel_tok_val in INV_VOCAB:
                    pitch_str = INV_VOCAB[pitch_tok_val]
                    vel_str = INV_VOCAB[vel_tok_val]
                    
                    if pitch_str in TOKEN_TO_PITCH and vel_str.startswith("VEL_"):
                        step = int(tok_str.split("_")[1])
                        pitch = TOKEN_TO_PITCH[pitch_str]
                        velocity = token_to_velocity(vel_str)
                        
                        start_time = step * seconds_per_16th
                        note = pretty_midi.Note(velocity, pitch, start_time, start_time + duration)
                        instrument.notes.append(note)
            i += 3
        else:
            i += 1
            
    midi.instruments.append(instrument)
    return midi

def encode_beat_context(features: BeatFeatures) -> list[int]:
    tokens = []
    # Style token as BOS equivalent for context
    style_tok = VOCAB.get(f"STYLE_{features.estimated_genre.upper()}", VOCAB["STYLE_UNKNOWN"])
    tokens.append(style_tok)
    
    for i in range(16):
        if features.kick_grid[i] == 1:
            tokens.extend([VOCAB[f"STEP_{i}"], VOCAB["KICK"], VOCAB["VEL_6"]])
        if features.snare_grid[i] == 1:
            tokens.extend([VOCAB[f"STEP_{i}"], VOCAB["SNARE"], VOCAB["VEL_6"]])
            
    return tokens
