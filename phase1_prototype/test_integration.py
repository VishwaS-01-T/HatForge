import os
import pretty_midi
from phase1_prototype.analyze_beat import extract_features
from phase1_prototype.generate_hats import generate_base_pattern, add_rolls, add_open_hats, apply_genre_pattern, grid_to_notes, HatConfig
from phase1_prototype.humanizer import humanize_velocity, humanize_timing
from phase1_prototype.midi_utils import save_midi

def test_full_chain():
    midi_path = os.path.join(os.path.dirname(__file__), "test_beat.mid")
    assert os.path.exists(midi_path), "test_beat.mid not found!"
    
    # 1. Extract features
    features = extract_features(midi_path)
    assert abs(features.bpm - 140.0) < 0.1
    
    # 2. Config & generate
    config = HatConfig(complexity=0.5)
    grid = generate_base_pattern(features, config)
    grid = add_rolls(grid, features, config)
    open_grid = add_open_hats(grid, features, config)
    grid = apply_genre_pattern(grid, features.estimated_genre)
    notes = grid_to_notes(grid, open_grid, features.bpm, bars=4)
    
    # 3. Humanize
    notes = humanize_velocity(notes)
    notes = humanize_timing(notes, features.bpm)
    
    # 4. Save
    output_path = "output/hats_test.mid"
    save_midi(notes, features.bpm, output_path)
    
    # 5. Verify
    out_midi = pretty_midi.PrettyMIDI(output_path)
    assert len(out_midi.instruments) >= 1
    
    drum_track = out_midi.instruments[0]
    assert len(drum_track.notes) >= 16
    
    for note in drum_track.notes:
        assert note.pitch in [42, 46], f"Invalid pitch found: {note.pitch}"
        
    print("Integration test passed successfully.")

if __name__ == "__main__":
    test_full_chain()
