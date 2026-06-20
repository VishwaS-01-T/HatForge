import logging
from dataclasses import dataclass
from phase1_prototype.midi_utils import load_midi, get_drum_track, get_bpm, notes_to_grid, merge_grids

logger = logging.getLogger(__name__)

@dataclass
class BeatFeatures:
    bpm: float
    kick_grid: list[int]
    snare_grid: list[int]
    kick_positions: list[float]
    snare_positions: list[float]
    density: float
    swing_ratio: float
    estimated_genre: str

def extract_features(midi_path: str) -> BeatFeatures:
    """
    Extract musical features from a drum MIDI file.
    
    Args:
        midi_path: Path to the MIDI file.
        
    Returns:
        A BeatFeatures object with extracted metrics.
    """
    midi = load_midi(midi_path)
    drum_track = get_drum_track(midi)
    bpm = get_bpm(midi)
    
    kick_notes = []
    snare_notes = []
    for note in drum_track.notes:
        if note.pitch in [36, 35]:
            kick_notes.append(note)
        elif note.pitch in [38, 40]:
            snare_notes.append(note)
            
    kick_grid = merge_grids(notes_to_grid(kick_notes, bpm, 16))
    snare_grid = merge_grids(notes_to_grid(snare_notes, bpm, 16))
    
    kick_positions = [note.start for note in kick_notes]
    snare_positions = [note.start for note in snare_notes]
    
    # Compute density
    total_hits = len(kick_notes) + len(snare_notes)
    density = min(1.0, total_hits / 32.0)
    
    # Compute swing ratio
    beats_per_bar = 4
    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = beats_per_bar * seconds_per_beat
    seconds_per_16th = seconds_per_bar / 16.0
    
    swing_sum = 0.0
    swing_count = 0
    for pos in kick_positions + snare_positions:
        pos_in_bar = pos % seconds_per_bar
        step_exact = pos_in_bar / seconds_per_16th
        closest_step = round(step_exact)
        
        if closest_step % 4 == 2:
            offset = step_exact - closest_step
            if 0 < offset < 0.5:
                swing_sum += offset / 0.33
                swing_count += 1
                
    swing_ratio = min(1.0, max(0.0, swing_sum / swing_count)) if swing_count > 0 else 0.0
    
    genre = "unknown"
    if 140 <= bpm <= 155 and sum(kick_grid) > 4:
        genre = "drill"
    elif 130 <= bpm <= 160 and kick_grid[0] == 1 and snare_grid[8] == 1:
        genre = "trap"
    elif 85 <= bpm <= 100 and kick_grid[0] == 1 and kick_grid[8] == 1 and snare_grid[4] == 1 and snare_grid[12] == 1:
        genre = "boom_bap"
        
    return BeatFeatures(
        bpm=bpm,
        kick_grid=kick_grid,
        snare_grid=snare_grid,
        kick_positions=kick_positions,
        snare_positions=snare_positions,
        density=density,
        swing_ratio=swing_ratio,
        estimated_genre=genre
    )

def print_beat_analysis(features: BeatFeatures) -> None:
    """
    Print a readable summary of the beat features to the console.
    
    Args:
        features: A BeatFeatures object.
    """
    print(f"BPM: {features.bpm:.1f}")
    print(f"Density: {features.density:.2f}")
    print(f"Genre: {features.estimated_genre}")
    
    def grid_str(g):
        return " ".join(["X" if x == 1 else "." for x in g])
        
    print(f"K: [{grid_str(features.kick_grid)}]")
    print(f"S: [{grid_str(features.snare_grid)}]")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Test extract_features by running this script on a valid midi file.")
