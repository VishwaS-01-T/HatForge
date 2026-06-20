import random
import pretty_midi

def humanize_velocity(notes: list[pretty_midi.Note], strength: float = 0.3,
                      velocity_base: int = 80) -> list[pretty_midi.Note]:
    """Apply human feel to velocity.

    Args:
        notes: Input note list.
        strength: Randomness strength (0.0–1.0).
        velocity_base: Centre velocity value. Defaults to 80; when a preset
                       supplies a custom value via HatConfig.velocity_base,
                       pass it here so the preset is actually honoured.

    Returns:
        A new list of Note objects with humanized velocities.
    """
    new_notes = []
    
    for i, note in enumerate(notes):
        velocity = velocity_base + random.gauss(0, strength * 30)
        
        # Accent every 4th note (downbeat feel)
        if i % 4 == 0:
            velocity *= 1.15
            
        velocity = max(40, min(110, int(velocity)))
        
        new_note = pretty_midi.Note(
            velocity=velocity,
            pitch=note.pitch,
            start=note.start,
            end=note.end
        )
        new_notes.append(new_note)
        
    return new_notes

def humanize_timing(notes: list[pretty_midi.Note], bpm: float,
                    strength: float = 0.2) -> list[pretty_midi.Note]:
    """Apply random micro-timing shifts.

    Safeguards added:
    - start is clamped to >= 0.
    - end is guaranteed to be > start by at least ``min_duration``.
    - Adjacent notes are checked: if a shift would push this note past
      the next note's start, the shift is capped so they don't overlap.
    """
    if not notes:
        return []

    # Sort a copy by start time so we can reason about neighbours
    sorted_notes = sorted(notes, key=lambda n: n.start)

    sixteenth_seconds = 60.0 / bpm / 4.0
    min_duration = sixteenth_seconds * 0.25  # 1/64 note minimum length

    new_notes = []
    
    for idx, note in enumerate(sorted_notes):
        offset = random.gauss(0, strength * (sixteenth_seconds * 0.1))
        
        start_time = max(0.0, note.start + offset)

        # Prevent overlapping with the next note
        if idx < len(sorted_notes) - 1:
            next_start = sorted_notes[idx + 1].start
            # Don't let this note's start go past the next note (minus a small gap)
            start_time = min(start_time, next_start - min_duration)
            start_time = max(0.0, start_time)

        # Preserve the original duration, but guarantee minimum
        original_duration = note.end - note.start
        duration = max(min_duration, original_duration)
        end_time = start_time + duration

        # If end would overlap the next note, shorten duration
        if idx < len(sorted_notes) - 1:
            next_start = sorted_notes[idx + 1].start
            if end_time > next_start:
                end_time = max(start_time + min_duration, next_start)
        
        new_note = pretty_midi.Note(
            velocity=note.velocity,
            pitch=note.pitch,
            start=start_time,
            end=end_time
        )
        new_notes.append(new_note)
        
    return new_notes

def add_ghost_notes(notes: list[pretty_midi.Note], probability: float = 0.1) -> list[pretty_midi.Note]:
    """Insert ghost notes randomly between existing notes."""
    new_notes = list(notes)
    
    for i in range(len(notes) - 1):
        if random.random() < probability:
            curr_note = notes[i]
            next_note = notes[i+1]
            
            # Place ghost note exactly halfway between
            mid_start = (curr_note.start + next_note.start) / 2.0
            mid_end = mid_start + (curr_note.end - curr_note.start)
            
            ghost_vel = random.randint(20, 35)
            
            ghost = pretty_midi.Note(
                velocity=ghost_vel,
                pitch=42, # closed hat
                start=mid_start,
                end=mid_end
            )
            new_notes.append(ghost)
            
    # Sort notes by start time after adding ghosts
    new_notes.sort(key=lambda n: n.start)
    return new_notes

if __name__ == "__main__":
    pass
