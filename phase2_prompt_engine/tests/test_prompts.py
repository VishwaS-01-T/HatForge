import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompt_parser import parse_prompt

def test_prompts():
    config1 = parse_prompt("dark rage")
    assert config1.complexity >= 0.7, f"Got {config1.complexity}"
    assert config1.roll_probability >= 0.5, f"Got {config1.roll_probability}"
    
    config2 = parse_prompt("minimal spacey")
    assert config2.complexity <= 0.3, f"Got {config2.complexity}"
    
    config3 = parse_prompt("this is gibberish")
    assert config3.style == "trap", f"Got {config3.style}"
    assert config3.complexity == 0.45, f"Got {config3.complexity}"
    assert config3.roll_probability == 0.5, f"Got {config3.roll_probability}"
    
    for prompt in ["dark rage", "minimal spacey", "this is gibberish"]:
        c = parse_prompt(prompt)
        assert 0.0 <= c.complexity <= 1.0
        assert 0.0 <= c.roll_probability <= 1.0
        assert 0.0 <= c.open_hat_probability <= 0.5
        assert c.subdivision in [8, 16, 32]
        
    print("All prompt parsing tests passed!")

if __name__ == "__main__":
    test_prompts()
