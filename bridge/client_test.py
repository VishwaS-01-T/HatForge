import socket
import json
import struct
import base64
import os
import pretty_midi

HOST = "127.0.0.1"
PORT = 7891

def send_message(conn: socket.socket, data: dict) -> None:
    json_str = json.dumps(data)
    json_bytes = json_str.encode('utf-8')
    msglen = struct.pack('<I', len(json_bytes))
    conn.sendall(msglen + json_bytes)

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
    msglen = struct.unpack('<I', raw_msglen)[0]
    data = recvall(conn, msglen)
    if not data:
        return None
    return json.loads(data.decode('utf-8'))

def test_client():
    midi_path = "../phase1_prototype/test_beat.mid"
    with open(midi_path, "rb") as f:
        midi_b64 = base64.b64encode(f.read()).decode('utf-8')
        
    payload = {
        "bpm": 140.0,
        "midi_b64": midi_b64,
        "prompt": "dark trap",
        "params": {"complexity": 0.6}
    }
    
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((HOST, PORT))
    
    send_message(conn, payload)
    
    response = receive_message(conn)
    conn.close()
    
    assert response is not None
    assert response["status"] == "ok", f"Error: {response.get('message')}"
    
    out_b64 = response["midi_b64"]
    out_midi = base64.b64decode(out_b64)
    
    os.makedirs("output", exist_ok=True)
    out_path = "output/bridge_test_output.mid"
    with open(out_path, "wb") as f:
        f.write(out_midi)
        
    assert os.path.exists(out_path)
    
    m = pretty_midi.PrettyMIDI(out_path)
    assert len(m.instruments) > 0
    assert len(m.instruments[0].notes) > 0
    
    print("Bridge client test passed!")

if __name__ == "__main__":
    test_client()
