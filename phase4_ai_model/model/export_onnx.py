import torch
import os
from phase4_ai_model.model.transformer import HatForgeTransformer
import onnxruntime as ort

def export_to_onnx(checkpoint_path: str, output_path: str) -> None:
    model = HatForgeTransformer()
    model.load_state_dict(torch.load(checkpoint_path, map_location="cpu"))
    model.eval()
    
    # Dummy inputs for forward pass
    # src: (batch, seq_len), tgt: (batch, seq_len)
    beat_context = torch.randint(0, 39, (1, 16), dtype=torch.long)
    style_token = torch.randint(0, 39, (1, 1), dtype=torch.long) # Represents the initial decoder input
    
    torch.onnx.export(
        model,
        (beat_context, style_token),
        output_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["beat_context", "style_token"],
        output_names=["hat_logits"],
        dynamic_axes={
            "beat_context": {0: "batch_size", 1: "src_seq_len"},
            "style_token": {0: "batch_size", 1: "tgt_seq_len"},
            "hat_logits": {0: "batch_size", 1: "tgt_seq_len"}
        }
    )
    
    print(f"Exported to {output_path}")
    
    # Verify
    session = ort.InferenceSession(output_path)
    for i in session.get_inputs():
        print(f"Input: {i.name}, {i.shape}, {i.type}")
    for o in session.get_outputs():
        print(f"Output: {o.name}, {o.shape}, {o.type}")

if __name__ == "__main__":
    export_to_onnx("checkpoints/best_model.pt", "checkpoints/hatforge.onnx")
