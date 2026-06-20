import sys
import os
import json
import dataclasses

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phase1_prototype"))

from generate_hats import HatConfig
from analyze_beat import BeatFeatures
from style_map import match_style, load_presets, get_keyword_modifiers

def parse_prompt(prompt: str, base_features: BeatFeatures = None) -> HatConfig:
    # Step 1: Match style from prompt
    style_name, confidence = match_style(prompt)
    
    # Step 2: Load base parameters
    presets = load_presets()
    base_params = presets["styles"].get(style_name, presets["styles"]["trap"])
    
    config = HatConfig()
    config.style = style_name
    config.complexity = base_params.get("complexity", 0.5)
    config.roll_probability = base_params.get("roll_probability", 0.3)
    config.open_hat_probability = base_params.get("open_hat_probability", 0.15)
    config.subdivision = base_params.get("subdivision", 16)
    
    # Step 3: Apply keyword modifiers
    modifiers = get_keyword_modifiers(prompt)
    for k, v in modifiers.items():
        if k == "subdivision":
            config.subdivision = v
        elif hasattr(config, k):
            setattr(config, k, getattr(config, k) + v)
            
    # Step 5: Bias based on base_features
    if base_features:
        if base_features.estimated_genre == "trap":
            config.roll_probability += 0.05
        elif base_features.estimated_genre == "drill":
            config.subdivision = max(16, config.subdivision)
            
    # Step 4: Clamp values
    config.complexity = max(0.0, min(1.0, config.complexity))
    config.roll_probability = max(0.0, min(1.0, config.roll_probability))
    config.open_hat_probability = max(0.0, min(0.5, config.open_hat_probability))
    if config.subdivision not in [8, 16, 32]:
        # Snap to nearest valid
        valid = [8, 16, 32]
        config.subdivision = min(valid, key=lambda x: abs(x - config.subdivision))
        
    return config

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "fast drill minimal"
    config = parse_prompt(prompt)
    print(json.dumps(dataclasses.asdict(config), indent=2))
