import random
import pretty_midi

def humanize_velocity(notes: list[pretty_midi.Note], strength: float = 0.3) -> list[pretty_midi.Note]:
    """Apply human feel to velocity."""
    new_notes = []
    base_velocity = 80
    
    for i, note in enumerate(notes):
        velocity = base_velocity + random.gauss(0, strength * 30)
        
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

def humanize_timing(notes: list[pretty_midi.Note], bpm: float, strength: float = 0.2) -> list[pretty_midi.Note]:
    """Apply random micro-timing shifts."""
    new_notes = []
    sixteenth_seconds = 60.0 / bpm / 4.0
    
    for note in notes:
        offset = random.gauss(0, strength * (sixteenth_seconds * 0.1))
        
        start_time = max(0.0, note.start + offset)
        end_time = max(0.0, note.end + offset)
        
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
