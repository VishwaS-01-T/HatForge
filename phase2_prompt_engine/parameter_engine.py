import sys
import os
import pretty_midi

from phase1_prototype.generate_hats import HatConfig, generate_base_pattern, add_rolls, add_open_hats, apply_genre_pattern, grid_to_notes
from phase1_prototype.analyze_beat import BeatFeatures
from phase1_prototype.humanizer import humanize_velocity, humanize_timing

def apply_config_to_generator(config: HatConfig, features: BeatFeatures) -> list[pretty_midi.Note]:
    """Applies HatConfig to the Phase 1 generator and returns MIDI notes.

    The full pipeline: base pattern → rolls → open hats → genre merge →
    grid-to-notes (with swing & velocity) → humanize velocity → humanize timing.
    """
    grid = generate_base_pattern(features, config)
    grid = add_rolls(grid, features, config)
    open_hat_grid = add_open_hats(grid, features, config)
    grid = apply_genre_pattern(grid, features.estimated_genre)
    
    notes = grid_to_notes(grid, open_hat_grid, features.bpm, bars=4,
                          swing_ratio=config.swing_ratio,
                          velocity_base=config.velocity_base)
    
    notes = humanize_velocity(notes, strength=config.complexity * 0.4,
                              velocity_base=config.velocity_base)
    notes = humanize_timing(notes, features.bpm, strength=0.15)
    
    return notes

if __name__ == "__main__":
    pass
