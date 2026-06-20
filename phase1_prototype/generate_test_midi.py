import pretty_midi

midi = pretty_midi.PrettyMIDI(initial_tempo=140.0)
instrument = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")

# 4/4 time, 140 BPM
# 1 beat = 60/140 = 0.4285s
# 1 bar = 4 beats = 1.714s
bpb = 4
spb = 60.0 / 140.0

# Kick on 1
kick1 = pretty_midi.Note(velocity=100, pitch=36, start=0.0, end=0.1)
# Snare on 3 (beat 3 is start time: 2 * spb)
snare1 = pretty_midi.Note(velocity=100, pitch=38, start=2 * spb, end=2 * spb + 0.1)

instrument.notes.extend([kick1, snare1])
midi.instruments.append(instrument)
midi.write("test_beat.mid")
