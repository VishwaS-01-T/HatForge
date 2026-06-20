import socket
import json
import struct
import base64
import logging
import threading
from pathlib import Path
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phase1_prototype"))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phase2_prompt_engine"))

from analyze_beat import extract_features
from prompt_parser import parse_prompt
from parameter_engine import apply_config_to_generator
from midi_utils import save_midi

HOST = "127.0.0.1"
PORT = 7891
BUFFER_SIZE = 65536

logger = logging.getLogger(__name__)

def recvall(conn, n):
    data = bytearray()
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def receive_message(conn: socket.socket) -> dict:
    """Read 4-byte length header then JSON body."""
    raw_msglen = recvall(conn, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('<I', raw_msglen)[0]
    data = recvall(conn, msglen)
    if not data:
        return None
    return json.loads(data.decode('utf-8'))

def send_message(conn: socket.socket, data: dict) -> None:
    """Send 4-byte length header then JSON body."""
    json_str = json.dumps(data)
    json_bytes = json_str.encode('utf-8')
    msglen = struct.pack('<I', len(json_bytes))
    conn.sendall(msglen + json_bytes)

def handle_client(conn: socket.socket, addr: tuple) -> None:
    try:
        req = receive_message(conn)
        if not req:
            return
            
        bpm = req.get("bpm", 120.0)
        midi_b64 = req.get("midi_b64", "")
        prompt = req.get("prompt", "")
        params = req.get("params", {})
        
        midi_data = base64.b64decode(midi_b64)
        
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        temp_midi = output_dir / f"temp_{addr[1]}.mid"
        with open(temp_midi, "wb") as f:
            f.write(midi_data)
            
        features = extract_features(str(temp_midi))
        config = parse_prompt(prompt, features)
        
        if "complexity" in params:
            config.complexity = float(params["complexity"])
        if "rolls" in params:
            config.roll_probability = float(params["rolls"])
            
        notes = apply_config_to_generator(config, features)
        
        out_midi_path = output_dir / f"temp_out_{addr[1]}.mid"
        save_midi(notes, bpm, str(out_midi_path))
        
        with open(out_midi_path, "rb") as f:
            out_b64 = base64.b64encode(f.read()).decode('utf-8')
            
        res = {
            "status": "ok",
            "midi_b64": out_b64
        }
        send_message(conn, res)
        
        temp_midi.unlink(missing_ok=True)
        out_midi_path.unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"Error handling client {addr}: {e}")
        send_message(conn, {"status": "error", "message": str(e)})
    finally:
        conn.close()

def start_server() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    logger.info(f"Server listening on {HOST}:{PORT}")
    
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.daemon = True
        t.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_server()
