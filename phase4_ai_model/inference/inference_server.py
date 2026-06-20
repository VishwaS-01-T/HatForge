import socket
import json
import struct
import base64
import logging
import threading
from pathlib import Path
import sys
import os
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

from phase1_prototype.analyze_beat import extract_features
from phase2_prompt_engine.prompt_parser import parse_prompt
from phase2_prompt_engine.parameter_engine import apply_config_to_generator
from phase1_prototype.midi_utils import save_midi
from phase4_ai_model.model.tokenizer import encode_beat_context, tokens_to_midi, VOCAB

HOST = "127.0.0.1"
PORT = 7891
logger = logging.getLogger(__name__)

class ONNXRunner:
    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(model_path)
    
    def run(self, beat_context: np.ndarray, style_token: int, temperature: float = 1.0) -> list[int]:
        tgt = np.array([[1, style_token]], dtype=np.int64) 
        
        for _ in range(256): # Max len for 4 bars
            inputs = {
                "beat_context": beat_context,
                "style_token": tgt
            }
            # Depending on export_onnx.py, inputs might just be src and tgt
            # Usually src is beat_context, tgt is tgt. Let's assume standard names or dynamic ones.
            # Assuming the ONNX model takes 'src' and 'tgt' as exported
            input_names = [i.name for i in self.session.get_inputs()]
            
            onnx_inputs = {}
            if "src" in input_names and "tgt" in input_names:
                onnx_inputs["src"] = beat_context
                onnx_inputs["tgt"] = tgt
            else:
                onnx_inputs[input_names[0]] = beat_context
                onnx_inputs[input_names[1]] = tgt

            logits = self.session.run(None, onnx_inputs)[0]
            
            next_token_logits = logits[0, -1, :] / max(temperature, 1e-5)
            # Subtract max for numerical stability
            probs = np.exp(next_token_logits - np.max(next_token_logits)) 
            probs = probs / np.sum(probs)
            next_token = np.random.choice(len(probs), p=probs)
            
            tgt = np.concatenate([tgt, np.array([[next_token]], dtype=np.int64)], axis=1)
            
            if next_token == VOCAB["EOS"]:
                break
                
        return tgt[0].tolist()

def recvall(conn, n):
    data = bytearray()
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def receive_message(conn: socket.socket) -> dict:
    raw_msglen = recvall(conn, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    data = recvall(conn, msglen)
    if not data:
        return None
    return json.loads(data.decode('utf-8'))

def send_message(conn: socket.socket, data: dict) -> None:
    json_str = json.dumps(data)
    json_bytes = json_str.encode('utf-8')
    msglen = struct.pack('>I', len(json_bytes))
    conn.sendall(msglen + json_bytes)

def handle_client(conn: socket.socket, addr: tuple, runner: ONNXRunner) -> None:
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
        
        # Apply params to config just like bridge/server.py
        if "complexity" in params:
            config.complexity = float(params["complexity"])
        if "rolls" in params:
            config.roll_probability = float(params["rolls"])
            
        out_midi_path = output_dir / f"temp_out_{addr[1]}.mid"
        
        if runner:
            ctx_tokens = encode_beat_context(features)
            ctx_np = np.array([ctx_tokens], dtype=np.int64)
            style_tok = VOCAB.get(f"STYLE_{features.estimated_genre.upper()}", VOCAB["STYLE_UNKNOWN"])
            
            # Map complexity to temperature roughly (e.g. 0.5 -> 1.0, 1.0 -> 1.5, 0.0 -> 0.5)
            temp = 0.5 + config.complexity
            
            hat_tokens = runner.run(ctx_np, style_tok, temperature=temp)
            midi = tokens_to_midi(hat_tokens, bpm)
            midi.write(str(out_midi_path))
        else:
            notes = apply_config_to_generator(config, features)
            save_midi(notes, bpm, str(out_midi_path))
            
        with open(out_midi_path, "rb") as f:
            out_b64 = base64.b64encode(f.read()).decode('utf-8')
            
        res = {"status": "ok", "midi_b64": out_b64}
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
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    logger.info(f"Server listening on {HOST}:{PORT}")
    
    # Path to hatforge.onnx
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model", "checkpoints", "hatforge.onnx")
    runner = None
    if ort and os.path.exists(model_path):
        logger.info("Loading ONNX model...")
        runner = ONNXRunner(model_path)
    else:
        logger.warning("ONNX model not found or onnxruntime not installed, falling back to rule-based generation.")
    
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr, runner))
        t.daemon = True
        t.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_server()
