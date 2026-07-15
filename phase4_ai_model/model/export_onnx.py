import torch
import os
import sys
import math
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from phase4_ai_model.model.transformer import HatForgeTransformer
from phase4_ai_model.model.tokenizer import VOCAB_SIZE
import onnxruntime as ort

def export_to_onnx(checkpoint_path: str, output_path: str) -> None:
    model = HatForgeTransformer(vocab_size=VOCAB_SIZE)
    model.load_state_dict(torch.load(checkpoint_path, map_location="cpu"))
    model.eval()
    
    # --- THE ULTIMATE FIX ---
    # We completely remove the causal mask. Because we are padding the future 
    # with 0s during C++ inference, the model's (tgt == 0) padding mask already 
    # handles ignoring the future! This elegantly bypasses all PyTorch bugs.
    def custom_forward(self, src, tgt):
        src_key_padding_mask = (src == 0)
        tgt_key_padding_mask = (tgt == 0)
        
        src_emb = self.pos_encoder(self.embedding(src) * math.sqrt(self.d_model))
        tgt_emb = self.pos_encoder(self.embedding(tgt) * math.sqrt(self.d_model))
        
        output = self.transformer(
            src_emb, tgt_emb,
            tgt_mask=None,  # <--- COMPLETELY REMOVED!
            src_key_padding_mask=src_key_padding_mask,
            tgt_key_padding_mask=tgt_key_padding_mask,
            memory_key_padding_mask=src_key_padding_mask
        )
        return self.fc_out(output)
        
    HatForgeTransformer.forward = custom_forward
    # ------------------------
    
    # Static shapes for foolproof ONNX export
    beat_context = torch.randint(0, VOCAB_SIZE, (1, 16), dtype=torch.long)
    style_token = torch.randint(0, VOCAB_SIZE, (1, 256), dtype=torch.long)
    
    torch.onnx.export(
        model,
        (beat_context, style_token),
        output_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["beat_context", "style_token"],
        output_names=["hat_logits"]
    )
    
    print(f"✅ Successfully exported to {output_path}")
    
    # Verify the fixed shapes are correct for your C++ plugin
    session = ort.InferenceSession(output_path)
    for i in session.get_inputs():
        print(f"Input: {i.name}, {i.shape}, {i.type}")
    for o in session.get_outputs():
        print(f"Output: {o.name}, {o.shape}, {o.type}")

if __name__ == "__main__":
    export_to_onnx("checkpoints/best_model.pt", "checkpoints/hatforge.onnx")
