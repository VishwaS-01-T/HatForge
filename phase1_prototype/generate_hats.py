import random
import logging
import argparse
import pretty_midi
from dataclasses import dataclass
from midi_utils import save_midi
from analyze_beat import extract_features, BeatFeatures

logger = logging.getLogger(__name__)

@dataclass
class HatConfig:
    complexity: float = 0.5
    roll_probability: float = 0.3
    open_hat_probability: float = 0.15
    subdivision: int = 16
    avoid_kick_collision: bool = True
    style: str = "default"

def generate_base_pattern(features: BeatFeatures, config: HatConfig) -> list[int]:
    """Create a 16-step binary grid for hi-hats."""
    grid = [0] * 16
    
    for i in range(16):
        if config.complexity >= 0.8:
            grid[i] = 1
        elif config.complexity >= 0.4:
            if i % 2 == 0:
                grid[i] = 1
        else:
            if i % 4 == 0:
                grid[i] = 1
                
    if config.avoid_kick_collision:
        for i in range(16):
            if features.kick_grid[i] == 1:
                grid[i] = 0
                
    return grid

def add_rolls(grid: list[int], features: BeatFeatures, config: HatConfig) -> list[int]:
    """Identify snare positions and optionally add rolls before them."""
    new_grid = list(grid)
    for i in range(16):
        if features.snare_grid[i] == 1:
            if random.random() < config.roll_probability:
                # Place 1s on steps N-3, N-2, N-1
                new_grid[(i - 3) % 16] = 1
                new_grid[(i - 2) % 16] = 1
                new_grid[(i - 1) % 16] = 1
    return new_grid

def add_open_hats(grid: list[int], features: BeatFeatures, config: HatConfig) -> list[int]:
    """Return a separate grid for open hats (pitch 46)."""
    open_grid = [0] * 16
    for pos in [6, 14]:
        if random.random() < config.open_hat_probability:
            open_grid[pos] = 1
    return open_grid

def apply_genre_pattern(grid: list[int], genre: str) -> list[int]:
    """Override/modify grid based on detected genre."""
    new_grid = list(grid)
    if genre == "trap":
        pass # Emphasize rolls/sparse hats handled by base pattern params mostly
    elif genre == "drill":
        # Dense 1/16 pattern with accent every 4th
        new_grid = [1] * 16
    elif genre == "boom_bap":
        # 1/8 hats
        new_grid = [1 if i % 2 == 0 else 0 for i in range(16)]
    return new_grid

def grid_to_notes(closed_hat_grid: list[int], open_hat_grid: list[int], bpm: float, bars: int = 4) -> list[pretty_midi.Note]:
    """Convert grids to Note objects over N bars."""
    notes = []
    beats_per_bar = 4
    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = beats_per_bar * seconds_per_beat
    seconds_per_16th = seconds_per_bar / 16.0
    
    # 1/32 note duration
    duration = seconds_per_bar / 32.0
    
    for bar in range(bars):
        bar_offset = bar * seconds_per_bar
        for i in range(16):
            start_time = bar_offset + i * seconds_per_16th
            
            # Prioritize open hats over closed hats
            if open_hat_grid[i] == 1:
                note = pretty_midi.Note(velocity=100, pitch=46, start=start_time, end=start_time + duration)
                notes.append(note)
            elif closed_hat_grid[i] == 1:
                note = pretty_midi.Note(velocity=100, pitch=42, start=start_time, end=start_time + duration)
                notes.append(note)
                
    return notes

def main(midi_path: str, config: HatConfig) -> str:
    """Load, analyze beat, generate pattern, and save output."""
    features = extract_features(midi_path)
    
    grid = generate_base_pattern(features, config)
    grid = add_rolls(grid, features, config)
    open_hat_grid = add_open_hats(grid, features, config)
    grid = apply_genre_pattern(grid, features.estimated_genre)
    
    notes = grid_to_notes(grid, open_hat_grid, features.bpm, bars=4)
    
    output_path = "output/hats.mid"
    save_midi(notes, features.bpm, output_path)
    logger.info(f"Generated hi-hats saved to {output_path}")
    return output_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Generate hi-hat patterns")
    parser.add_argument("midi_path", type=str, help="Input drum MIDI file")
    parser.add_argument("--complexity", type=float, default=0.5, help="Complexity 0.0-1.0")
    parser.add_argument("--rolls", type=float, default=0.3, help="Roll probability 0.0-1.0")
    
    args = parser.parse_args()
    config = HatConfig(complexity=args.complexity, roll_probability=args.rolls)
    
    main(args.midi_path, config)
