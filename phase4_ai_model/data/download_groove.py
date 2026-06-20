import os
import random
import pretty_midi
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "phase1_prototype"))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "phase2_prompt_engine"))

from analyze_beat import BeatFeatures
from generate_hats import HatConfig, generate_base_pattern, add_rolls, add_open_hats, grid_to_notes
from midi_utils import save_midi

def generate_synthetic_data(num_samples: int, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(num_samples):
        bpm = random.uniform(85, 160)
        kick_grid = [1 if random.random() < 0.2 else 0 for _ in range(16)]
        kick_grid[0] = 1 # Always kick on 1
        snare_grid = [0] * 16
        snare_grid[4] = 1
        snare_grid[12] = 1
        
        genre = "trap" if 130 <= bpm <= 160 else "boom_bap"
        
        features = BeatFeatures(
            bpm=bpm,
            kick_grid=kick_grid,
            snare_grid=snare_grid,
            kick_positions=[],
            snare_positions=[],
            density=0.5,
            swing_ratio=0.0,
            estimated_genre=genre
        )
        
        config = HatConfig(
            complexity=random.uniform(0.2, 0.9),
            roll_probability=random.uniform(0.1, 0.7),
            open_hat_probability=random.uniform(0.05, 0.4)
        )
        
        grid = generate_base_pattern(features, config)
        grid = add_rolls(grid, features, config)
        open_grid = add_open_hats(grid, features, config)
        
        notes = grid_to_notes(grid, open_grid, bpm, bars=4)
        
        beats_per_bar = 4
        seconds_per_beat = 60.0 / bpm
        seconds_per_bar = beats_per_bar * seconds_per_beat
        seconds_per_16th = seconds_per_bar / 16.0
        
        for bar in range(4):
            bar_offset = bar * seconds_per_bar
            for step in range(16):
                time = bar_offset + step * seconds_per_16th
                if kick_grid[step] == 1:
                    notes.append(pretty_midi.Note(100, 36, time, time+0.1))
                if snare_grid[step] == 1:
                    notes.append(pretty_midi.Note(100, 38, time, time+0.1))
                    
        out_path = os.path.join(output_dir, f"synth_{i}.mid")
        save_midi(notes, bpm, out_path)

if __name__ == "__main__":
    generate_synthetic_data(50, "raw")
