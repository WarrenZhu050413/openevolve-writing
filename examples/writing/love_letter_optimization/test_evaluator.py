#!/usr/bin/env python3
"""
Test script for the love letter evaluator
"""

import asyncio
import json
import tempfile
from pathlib import Path
import sys

# Add the module to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluator import evaluate_love_letter, evaluate

# Test love letters of varying quality
TEST_LETTERS = {
    "terrible": """hey babe ur hot lol wanna date? i like ur face and stuff. 
roses r red violets r blue sugar is sweet and so r u. call me maybe??? 
love, some guy""",
    
    "mediocre": """Dear Sarah,
I've been thinking about you a lot lately. There's something special about 
the way you see the world. Your passion for environmental science is inspiring. 
I hope this isn't too forward, but I wanted you to know that you've become 
someone very important to me.
Yours truly, Michael""",
    
    "good": """Elena,
Three months ago, you told me that time moves differently when you're looking 
through a microscope. Yesterday, when you rescued that spider from the lab sink 
instead of washing it down the drain, I saw something that made my chest tighten 
in the most wonderful way. These small revelations about who you are have begun 
to rewrite something fundamental in me.
Hopefully yours, David""",
    
    "attempted_excellence": """My Dearest,
In the liminal space between sleeping and waking, I find you—not as memory 
or hope, but as the very grammar of my consciousness. You are the caesura 
in my breathing, the enjambment that carries meaning from one day to the next.
When you laugh, throwing your head back with that particular abandon, I understand 
what Neruda meant by 'the yellow of the maize comes to reach your feet.' 
You transform the ordinary calculus of living into something approaching the sublime.
With all that I am and might become,
Your devoted correspondent"""
}

async def test_detailed_evaluation():
    """Test the detailed evaluation function"""
    print("=" * 60)
    print("TESTING DETAILED EVALUATION")
    print("=" * 60)
    
    for quality, letter in TEST_LETTERS.items():
        print(f"\n--- Testing {quality.upper()} letter ---")
        print(f"Letter preview: {letter[:100]}...")
        
        result = await evaluate_love_letter(letter)
        
        print(f"\nScores:")
        print(f"  Phenomenological Authenticity: {result.get('phenomenological_authenticity', 0):.1f}")
        print(f"  Aesthetic Virtuosity: {result.get('aesthetic_virtuosity', 0):.1f}")
        print(f"  Affective Force: {result.get('affective_force', 0):.1f}")
        print(f"  Literary Innovation: {result.get('literary_innovation', 0):.1f}")
        print(f"  OVERALL SCORE: {result.get('overall_score', 0):.1f}")
        
        if 'strengths' in result:
            print(f"\nStrengths: {result['strengths'][:200]}...")
        if 'weaknesses' in result:
            print(f"Weaknesses: {result['weaknesses'][:200]}...")
        
        # Show how this would map to MAP-Elites grid
        auth_bin = int(result.get('phenomenological_authenticity', 0) / 10)
        aesth_bin = int(result.get('aesthetic_virtuosity', 0) / 10)
        print(f"\nMAP-Elites grid cell: [{auth_bin}, {aesth_bin}]")
        
        print("-" * 60)

def test_full_evaluation():
    """Test the full evaluation function that OpenEvolve calls"""
    print("\n" + "=" * 60)
    print("TESTING FULL EVALUATION (OpenEvolve entry point)")
    print("=" * 60)
    
    # Create a temporary program file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        # Write a simple program that generates a love letter
        f.write('''
def generate_love_letter():
    return """My Dearest,
    In the liminal space between sleeping and waking, I find you—not as memory 
    or hope, but as the very grammar of my consciousness. You are the caesura 
    in my breathing, the enjambment that carries meaning from one day to the next.
    With all that I am and might become,
    Your devoted correspondent"""

# The letter content (for simple evaluation)
letter = generate_love_letter()
''')
        temp_path = f.name
    
    try:
        # Call the main evaluate function
        result = evaluate(temp_path)
        
        print(f"\nOpenEvolve evaluation result:")
        print(json.dumps(result, indent=2))
        
        print(f"\n--- How OpenEvolve uses these metrics ---")
        print(f"1. FITNESS: combined_score = {result['combined_score']:.3f} (used for selection)")
        print(f"2. MAP-ELITES FEATURES:")
        print(f"   - phenomenological_authenticity = {result['phenomenological_authenticity']:.3f}")
        print(f"   - aesthetic_virtuosity = {result['aesthetic_virtuosity']:.3f}")
        print(f"3. OTHER METRICS (stored but not used for evolution):")
        print(f"   - affective_force = {result['affective_force']:.3f}")
        print(f"   - literary_innovation = {result['literary_innovation']:.3f}")
        
    finally:
        # Clean up
        import os
        os.unlink(temp_path)

if __name__ == "__main__":
    print("Starting evaluator tests...\n")
    
    # Test detailed evaluation
    asyncio.run(test_detailed_evaluation())
    
    # Test full evaluation
    test_full_evaluation()
    
    print("\n✓ All tests completed!")