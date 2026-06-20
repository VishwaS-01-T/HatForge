import pretty_midi
import logging
from collections import Counter

logger = logging.getLogger(__name__)

def load_midi(filepath: str) -> pretty_midi.PrettyMIDI:
    """
    Load a MIDI file using pretty_midi.
    
    Args:
        filepath: Path to the MIDI file.
        
    Returns:
        A pretty_midi.PrettyMIDI object.
        
    Raises:
        ValueError: If no drum track is found in the MIDI file.
    """
    midi = pretty_midi.PrettyMIDI(filepath)
    has_drum = any(inst.is_drum for inst in midi.instruments)
    if not has_drum:
        raise ValueError("No drum track in MIDI file")
        
    return midi

def get_drum_track(midi: pretty_midi.PrettyMIDI) -> pretty_midi.Instrument:
    """
    Find the first drum instrument track in the MIDI file.
    
    Args:
        midi: A pretty_midi.PrettyMIDI object.
        
    Returns:
        The first drum instrument found.
        
    Raises:
        ValueError: If no drum track is found.
    """
    for inst in midi.instruments:
        if inst.is_drum:
            return inst
    raise ValueError("No drum track in MIDI file")

def get_bpm(midi: pretty_midi.PrettyMIDI) -> float:
    """
    Extract the most common tempo from the MIDI file.
    
    Args:
        midi: A pretty_midi.PrettyMIDI object.
        
    Returns:
        The extracted tempo in BPM. Defaults to 120.0 if no tempo found.
    """
    try:
        times, tempos = midi.get_tempo_changes()
    except Exception:
        return 120.0
        
    if len(tempos) == 0:
        return 120.0
        
    if len(tempos) == 1:
        return float(tempos[0])
        
    tempo_counts = Counter(tempos)
    most_common = tempo_counts.most_common(1)
    if most_common:
        return float(most_common[0][0])
        
    return 120.0

def notes_to_grid(notes: list, bpm: float, subdivisions: int = 16) -> list[list[int]]:
    """
    Convert a list of Notes to a list of per-bar binary grids.
    
    Instead of folding all notes into a single bar via modulo, this function
    returns one grid per bar so that multi-bar patterns are preserved.  When
    only a single summary grid is needed (e.g. for genre detection), the
    caller can merge the bars with ``merge_grids()``.
    
    Args:
        notes: List of pretty_midi.Note objects.
        bpm: Beats per minute.
        subdivisions: Number of grid slots per bar (default 16).
        
    Returns:
        A list of grids (each a list of 0s and 1s of length ``subdivisions``).
        If no notes are found, returns a single empty bar.
    """
    if not notes:
        return [[0] * subdivisions]

    beats_per_bar = 4
    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = beats_per_bar * seconds_per_beat
    seconds_per_step = seconds_per_bar / subdivisions
    
    # Determine how many bars we need
    max_time = max(n.start for n in notes)
    num_bars = max(1, int(max_time / seconds_per_bar) + 1)
    
    grids = [[0] * subdivisions for _ in range(num_bars)]
    
    for note in notes:
        bar_index = int(note.start / seconds_per_bar)
        if bar_index >= num_bars:
            bar_index = num_bars - 1
        start_in_bar = note.start - bar_index * seconds_per_bar
        step = int(round(start_in_bar / seconds_per_step)) % subdivisions
        grids[bar_index][step] = 1
        
    return grids

def merge_grids(grids: list[list[int]]) -> list[int]:
    """OR-merge a list of per-bar grids into a single summary grid.
    
    This is the backward-compatible replacement for the old notes_to_grid()
    behaviour that folded everything into one bar.
    
    Args:
        grids: A list of per-bar grids (from notes_to_grid).
        
    Returns:
        A single grid of 0s and 1s.
    """
    if not grids:
        return [0] * 16
    
    subdivisions = len(grids[0])
    merged = [0] * subdivisions
    for grid in grids:
        for i in range(subdivisions):
            if grid[i] == 1:
                merged[i] = 1
    return merged

def save_midi(notes: list, bpm: float, output_path: str) -> None:
    """
    Create a new MIDI file with the provided notes and BPM.
    
    Args:
        notes: List of pretty_midi.Note objects to add to the instrument.
        bpm: Tempo to set in the MIDI file.
        output_path: Path to save the MIDI file.
    """
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    instrument = pretty_midi.Instrument(program=0, is_drum=True, name="HatForge Hats")
    instrument.notes.extend(notes)
    midi.instruments.append(instrument)
    midi.write(output_path)
    logger.info(f"Saved MIDI to {output_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing notes_to_grid logic...")
    bpm = 120.0
    sec_per_beat = 60.0 / bpm
    notes = [
        pretty_midi.Note(velocity=100, pitch=42, start=0, end=0.1),
        pretty_midi.Note(velocity=100, pitch=42, start=sec_per_beat/2, end=0.1+sec_per_beat/2),
        pretty_midi.Note(velocity=100, pitch=42, start=sec_per_beat, end=0.1+sec_per_beat),
    ]
    grids = notes_to_grid(notes, bpm)
    # All notes fit in bar 0
    grid = merge_grids(grids)
    print("Grid:", grid)
    assert grid[0] == 1
    assert grid[2] == 1
    assert grid[4] == 1
    print("All tests passed.")
