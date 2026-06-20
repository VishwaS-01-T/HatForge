import sys
import os
import json
import dataclasses

from phase1_prototype.generate_hats import HatConfig
from phase1_prototype.analyze_beat import BeatFeatures
from phase2_prompt_engine.style_map import match_style, load_presets, get_keyword_modifiers

def parse_prompt(prompt: str, base_features: BeatFeatures = None) -> HatConfig:
    """Parse a text prompt into a HatConfig.

    Loads the matching style preset, applies keyword modifiers, biases based
    on detected features, and clamps all values to valid ranges.
    """
    # Step 1: Match style from prompt
    style_name, confidence = match_style(prompt)
    
    # Step 2: Load base parameters from preset
    presets = load_presets()
    base_params = presets["styles"].get(style_name, presets["styles"]["trap"])
    
    config = HatConfig()
    config.style = style_name
    config.complexity = base_params.get("complexity", 0.5)
    config.roll_probability = base_params.get("roll_probability", 0.3)
    config.open_hat_probability = base_params.get("open_hat_probability", 0.15)
    config.subdivision = base_params.get("subdivision", 16)
    config.swing_ratio = base_params.get("swing_ratio", 0.0)
    config.velocity_base = base_params.get("velocity_base", 80)
    
    # Step 3: Apply keyword modifiers
    modifiers = get_keyword_modifiers(prompt)
    for k, v in modifiers.items():
        if k == "subdivision":
            config.subdivision = v
        elif k == "velocity_base":
            # velocity_base is additive from keywords (e.g. "dark" → +10)
            config.velocity_base = config.velocity_base + int(v)
        elif hasattr(config, k):
            setattr(config, k, getattr(config, k) + v)
            
    # Step 4: Bias based on base_features
    if base_features:
        if base_features.estimated_genre == "trap":
            config.roll_probability += 0.05
        elif base_features.estimated_genre == "drill":
            config.subdivision = max(16, config.subdivision)
            
    # Step 5: Clamp values
    config.complexity = max(0.0, min(1.0, config.complexity))
    config.roll_probability = max(0.0, min(1.0, config.roll_probability))
    config.open_hat_probability = max(0.0, min(0.5, config.open_hat_probability))
    config.swing_ratio = max(0.0, min(1.0, config.swing_ratio))
    config.velocity_base = max(30, min(127, config.velocity_base))
    if config.subdivision not in [8, 16, 32]:
        # Snap to nearest valid
        valid = [8, 16, 32]
        config.subdivision = min(valid, key=lambda x: abs(x - config.subdivision))
        
    return config

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "fast drill minimal"
    config = parse_prompt(prompt)
    print(json.dumps(dataclasses.asdict(config), indent=2))
