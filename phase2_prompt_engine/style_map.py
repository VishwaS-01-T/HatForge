import json
import os

def load_presets() -> dict:
    """Load and parse presets.json."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    presets_path = os.path.join(current_dir, "styles", "presets.json")
    with open(presets_path, "r") as f:
        return json.load(f)

def get_style_names() -> list[str]:
    """Return list of all keys in presets['styles']."""
    presets = load_presets()
    return list(presets.get("styles", {}).keys())

def match_style(prompt: str) -> tuple[str, float]:
    """
    Match prompt to a style.
    Returns (style_name, confidence)
    """
    prompt = prompt.lower()
    style_names = get_style_names()
    
    # Check for exact match first
    for name in style_names:
        # replace underscore with space for comparison
        clean_name = name.replace("_", " ")
        if prompt == clean_name or prompt == name:
            return (name, 1.0)
            
    # Substring match
    for name in style_names:
        clean_name = name.replace("_", " ")
        if clean_name in prompt or name in prompt:
            return (name, 0.7)
            
    return ("trap", 0.0)

def get_keyword_modifiers(prompt: str) -> dict:
    """
    Check prompt for all keyword keys and return dict of parameter deltas.
    """
    prompt = prompt.lower()
    presets = load_presets()
    keywords = presets.get("keywords", {})
    
    modifiers = {}
    for kw, mods in keywords.items():
        if kw in prompt:
            for param, delta in mods.items():
                # some params like subdivision override, others add
                if param == "subdivision":
                    modifiers[param] = delta # Overwrite
                else:
                    modifiers[param] = modifiers.get(param, 0.0) + delta
                    
    return modifiers

if __name__ == "__main__":
    print(match_style("dark rage"))
    print(get_keyword_modifiers("dark aggressive drill"))
