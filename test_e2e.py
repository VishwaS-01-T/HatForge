import os
import pretty_midi
import json
import base64
import socket
import struct
import subprocess
import time
import sys

from phase1_prototype.analyze_beat import extract_features
from phase2_prompt_engine.prompt_parser import parse_prompt
from phase1_prototype.generate_hats import generate_base_pattern, add_rolls, apply_genre_pattern, grid_to_notes, HatConfig, add_open_hats
from phase2_prompt_engine.parameter_engine import apply_config_to_generator
from phase1_prototype.humanizer import humanize_velocity, humanize_timing
from phase1_prototype.midi_utils import save_midi

def run_test_1():
    print("Test 1: Phase 1 standalone")
    midi_path = "phase1_prototype/test_beat.mid"
    features = extract_features(midi_path)
    config = HatConfig(complexity=0.5, style="trap")
    
    grid = generate_base_pattern(features, config)
    grid = add_rolls(grid, features, config)
    open_grid = add_open_hats(grid, features, config)
    grid = apply_genre_pattern(grid, features.estimated_genre)
    
    notes = grid_to_notes(grid, open_grid, features.bpm, bars=4)
    os.makedirs("phase1_prototype/output", exist_ok=True)
    out_path = "phase1_prototype/output/hats.mid"
    save_midi(notes, features.bpm, out_path)
    
    m = pretty_midi.PrettyMIDI(out_path)
    assert len(m.instruments[0].notes) >= 16
    for note in m.instruments[0].notes:
        assert note.pitch in [42, 46]
    print("Test 1 Passed.")

def run_test_2():
    print("Test 2: Prompt engine")
    config = parse_prompt("dark aggressive drill")
    assert config.complexity >= 0.7
    assert config.roll_probability >= 0.45
    print("Test 2 Passed.")

def send_message(conn, data):
    json_str = json.dumps(data)
    json_bytes = json_str.encode('utf-8')
    msglen = struct.pack('>I', len(json_bytes))
    conn.sendall(msglen + json_bytes)

def recvall(conn, n):
    data = bytearray()
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def receive_message(conn):
    raw_msglen = recvall(conn, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    data = recvall(conn, msglen)
    if not data:
        return None
    return json.loads(data.decode('utf-8'))

def run_test_3():
    print("Test 3: Bridge server")
    midi_path = "phase1_prototype/test_beat.mid"
    with open(midi_path, "rb") as f:
        midi_b64 = base64.b64encode(f.read()).decode('utf-8')
        
    payload = {
        "bpm": 140.0,
        "midi_b64": midi_b64,
        "prompt": "dark trap",
        "params": {"complexity": 0.6}
    }
    
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect(("127.0.0.1", 7891))
    send_message(conn, payload)
    
    t0 = time.time()
    response = receive_message(conn)
    t1 = time.time()
    conn.close()
    
    assert response["status"] == "ok"
    assert t1 - t0 < 3.0
    
    out_midi = base64.b64decode(response["midi_b64"])
    out_path = "bridge/output/test3_out.mid"
    os.makedirs("bridge/output", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(out_midi)
        
    m = pretty_midi.PrettyMIDI(out_path)
    assert len(m.instruments) > 0
    print("Test 3 Passed.")

def run_test_4():
    print("Test 4: Style contrast")
    midi_path = "phase1_prototype/test_beat.mid"
    features = extract_features(midi_path)
    
    config_a = parse_prompt("minimal spacey chill", features)
    notes_a = apply_config_to_generator(config_a, features)
    
    config_b = parse_prompt("chaotic dark aggressive", features)
    notes_b = apply_config_to_generator(config_b, features)
    
    density_a = len(notes_a) / 64.0 # 64 16ths in 4 bars
    density_b = len(notes_b) / 64.0
    
    assert density_a < 0.5, f"density_a is {density_a}"
    assert density_b > 0.7, f"density_b is {density_b}"
    print("Test 4 Passed.")

def run_test_5():
    print("Test 5: Humanization")
    midi_path = "phase1_prototype/test_beat.mid"
    features = extract_features(midi_path)
    config = HatConfig(complexity=0.5)
    
    notes1 = apply_config_to_generator(config, features)
    notes2 = apply_config_to_generator(config, features)
    
    vel1 = [n.velocity for n in notes1]
    vel2 = [n.velocity for n in notes2]
    
    assert vel1 != vel2
    print("Test 5 Passed.")

if __name__ == "__main__":
    run_test_1()
    run_test_2()
    
    print("Starting server for Test 3...")
    server_process = subprocess.Popen([sys.executable, "bridge/server.py"])
    time.sleep(2) # wait for server to start
    
    try:
        run_test_3()
    finally:
        server_process.terminate()
        server_process.wait()
        
    run_test_4()
    run_test_5()
    
    print("All E2E tests passed! GREEN!")
