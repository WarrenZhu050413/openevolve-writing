"""
Love Letter Evaluator for OpenEvolve
Scores love letters on a 1-100 scale using Claude Code SDK
"""

import asyncio
import sys
import json
import os
from pathlib import Path

# Check for claude_code_sdk installation
try:
    from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions, CLINotFoundError, ProcessError
except ImportError:
    print("Error: claude-code-sdk not installed. Run: pip install claude-code-sdk")
    print("Or if using npm: npm install -g @anthropic-ai/claude-code")
    sys.exit(1)


# Quality benchmark letters for reference (used internally for calibration)
BENCHMARK_LETTERS = {
    "terrible": "hey babe ur hot lol wanna date? i like ur face and stuff. roses r red violets r blue sugar is sweet and so r u. call me maybe??? love, some guy",
    "mediocre": "Dear Sarah, I've been thinking about you a lot lately. There's something special about the way you see the world. Your passion for environmental science is inspiring. I hope this isn't too forward, but I wanted you to know that you've become someone very important to me. Yours truly, Michael",
    "excellent": "Elena, Three months ago, you told me that time moves differently when you're looking through a microscope. Yesterday, when you rescued that spider from the lab sink instead of washing it down the drain, I saw something that made my chest tighten in the most wonderful way. These small revelations about who you are have begun to rewrite something fundamental in me. Hopefully yours, David"
}


# Enhanced discriminatory scoring system for love letters
LETTER_RUBRIC = """
You are an expert literary critic specializing in romantic literature and love letters.

EVALUATION STANDARDS (USE FINE-GRAINED DISTINCTIONS):
- DIVINE/PLATONIC IDEAL (100): Theoretical perfection - the unimprovable essence of love made word
- TRANSCENDENT (95-99): Beyond human - achieves the impossible in romantic expression
- SUBLIME (90-94): Revolutionary - creates entirely new paradigms of love letters
- IMMORTAL MASTERPIECE (85-89): Beethoven's Immortal Beloved level
- HISTORIC MASTERWORK (80-84): Johnny Cash, Napoleon, Keats level mastery
- NEAR-MASTERPIECE (75-79): Approaches the greatest but falls just short
- PROTO-MASTERFUL (70-74): Seeds of brilliance, flashes of genius
- EXCEPTIONAL (65-69): Remarkable craft and feeling, memorable phrases
- DISTINGUISHED (60-64): Sophisticated, moving, professionally excellent
- IMPRESSIVE (55-59): Strong literary merit with emotional resonance
- ACCOMPLISHED (50-54): Skillful execution, clear talent
- PROFICIENT (45-49): Professional quality, technically sound
- CAPABLE (40-44): Solid craft with moments of beauty
- PROMISING (35-39): Shows potential, some lovely passages
- COMPETENT (30-34): Adequate expression, functional romance
- DECENT (25-29): Acceptable, some merit
- GOOD (20-24): Basic competence, above average for general population
- MEDIOCRE (15-19): Average, uninspired but coherent
- WEAK (10-14): Below average, clichéd
- POOR (5-9): Seriously flawed, awkward
- TERRIBLE (1-4): Nearly incoherent
- ABSOLUTE FAILURE (0): Offensive or completely inappropriate

SCORING CRITERIA (Rate 0-100 for each with ultra-fine distinctions):

1. PHENOMENOLOGICAL AUTHENTICITY & INTERIORITY (35%):
   - Dasein (being-in-the-world): Authentic presence vs performative facade
   - I-Thou encounter (Buber): Direct communion vs objectifying distance
   - Confessional intimacy: Genuine vulnerability vs calculated disclosure
   - Negative capability (Keats): Comfort with love's mysteries vs reductive certainty
   - Psychological realism: Complex inner life vs flat emotional states
   - Temporal consciousness: Living memory and duration vs static snapshots
   - Embodied experience: Somatic/sensory presence vs abstract sentiment
   - Voice distinctiveness: Unmistakable persona vs generic speaker

2. AESTHETIC VIRTUOSITY & FORMAL MASTERY (30%):
   - Prosody & rhythm: Cadence, caesura, breath (even in prose)
   - Figurative language: Metaphor, metonymy, synecdoche - density and originality
   - Syntactic architecture: Parataxis/hypotaxis, periodic/loose sentences
   - Sound texture: Assonance, consonance, alliteration, internal rhyme
   - Objective correlative (Eliot): External equivalents for internal states
   - Defamiliarization (Shklovsky): Making strange the familiar
   - Imagery precision: Concrete sensory detail vs vague abstraction
   - Sprezzatura: Artful effortlessness vs labored construction
   - Register control: High/middle/low style appropriateness

3. AFFECTIVE FORCE & SUBLIME ENCOUNTER (25%):
   - Cathartic potential (Aristotle): Emotional transformation capacity
   - The punctum (Barthes): The piercing detail that wounds
   - Sublime experience (Burke/Kant): Overwhelming beauty/terror
   - Duende (Lorca): Dark authentic passion vs superficial prettiness
   - Saudade/Sehnsucht: Ineffable longing, exquisite absence
   - Anagnorisis moments: Recognition, revelation, epiphany
   - Jouissance vs plaisir: Disruptive bliss vs comfortable pleasure
   - Uncanny resonance (Freud): Familiar strangeness that haunts
   - Numinous presence: Sacred/transcendent dimension

4. LITERARY INNOVATION & INTERTEXTUAL SOPHISTICATION (10%):
   - Anxiety of influence (Bloom): Transcending vs imitating predecessors
   - Heteroglossia (Bakhtin): Multiple voices/registers vs monotone
   - Genre consciousness: Subversion, fusion, or masterful tradition
   - Intertextual resonance: Literary echoes and allusions
   - Aporia & paradox: Productive impossibilities vs clichés
   - Chronotope: Unique time-space configuration
   - Différance (Derrida): Meaning through difference/deferral
   - Transgressive elements: Breaking conventions meaningfully

EVALUATION REQUIREMENTS:
- MOST letters should score 10-30 (mediocre to competent range)
- USE ULTRA-FINE DISTINCTIONS - a 73 is meaningfully different from a 74
- BE EXTREMELY STRICT - each point above 50 should be hard-earned
- Scores above 80 are reserved for actual historical masterpieces
- Scores above 90 should be nearly impossible
- JUSTIFY SCORES with specific textual evidence
- Think in single-point increments - each point represents real qualitative difference
- Compare explicitly to the greatest love letters in history

FAMOUS LOVE LETTER BENCHMARKS:
- Beethoven to Immortal Beloved: "My angel, my all, my very self..." (Score: 86)
- Johnny Cash to June Carter: "You still fascinate and inspire me..." (Score: 83)
- Napoleon to Josephine: "I have not spent a day without loving you..." (Score: 82)
- John Keats to Fanny Brawne: "I cannot exist without you..." (Score: 81)
- Oscar Wilde to Lord Alfred Douglas: "My own dear boy..." (Score: 80)

Remember: A 22 vs 23 should represent a real qualitative difference. Use the FULL granularity.
"""


async def evaluate_love_letter(letter_text: str) -> dict:
    """
    Evaluate a love letter using enhanced discriminatory scoring
    Returns detailed evaluation with 4 criteria scores
    """
    
    evaluation_prompt = f"""
{LETTER_RUBRIC}

LOVE LETTER TO EVALUATE:
{letter_text}

Return your evaluation in this exact format:
<output>
phenomenological_authenticity:[0-100 score]
aesthetic_virtuosity:[0-100 score]
affective_force:[0-100 score]
literary_innovation:[0-100 score]
strengths:[specific textual examples with quotes]
weaknesses:[specific areas needing improvement]
comparison_notes:[explicit comparison to literary benchmarks]
</output>
"""
    
    try:
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt="You are an expert literary critic specializing in romantic literature. Provide detailed, discriminatory evaluations using the full 0-100 scoring range.",
                max_turns=1
            )
        ) as client:
            await client.query(evaluation_prompt)
            
            # Collect response content
            response_parts = []
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            response_parts.append(block.text)
            
            response_text = ''.join(response_parts).strip()
            
            # Parse structured output response
            try:
                import re
                # Extract output section
                output_match = re.search(r'<output>(.*?)</output>', response_text, re.DOTALL)
                if output_match:
                    output_content = output_match.group(1).strip()
                    
                    # Parse key:value pairs
                    evaluation_data = {}
                    for line in output_content.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Convert numeric values (skip overall_score since we calculate it)
                            if key in ['phenomenological_authenticity', 'aesthetic_virtuosity', 
                                      'affective_force', 'literary_innovation']:
                                try:
                                    evaluation_data[key] = float(value)
                                except ValueError:
                                    evaluation_data[key] = 20.0  # Default to "good" level if parsing fails
                            else:
                                evaluation_data[key] = value
                    
                    # Always calculate weighted average programmatically
                    auth = evaluation_data.get('phenomenological_authenticity', 0)
                    craft = evaluation_data.get('aesthetic_virtuosity', 0)
                    impact = evaluation_data.get('affective_force', 0)
                    orig = evaluation_data.get('literary_innovation', 0)
                    evaluation_data['overall_score'] = (auth * 0.35 + craft * 0.30 + impact * 0.25 + orig * 0.10)
                    
                    return evaluation_data
                else:
                    raise ValueError("No <output> section found in response")
                    
            except (ValueError, KeyError) as e:
                print(f"Warning: Could not parse output from response: {response_text}")
                # Fallback to simple scoring
                score = 20  # Default to "good" level
                return {
                    'phenomenological_authenticity': score,
                    'aesthetic_virtuosity': score,
                    'affective_force': score,
                    'literary_innovation': score,
                    'overall_score': score,
                    'strengths': 'Could not analyze',
                    'weaknesses': 'Could not analyze',
                    'comparison_notes': f'Evaluation failed: {str(e)}'
                }
                
    except CLINotFoundError:
        print("Error: Claude Code CLI not found. Please install: npm install -g @anthropic-ai/claude-code")
        return {
            'phenomenological_authenticity': 20,
            'aesthetic_virtuosity': 20,
            'affective_force': 20,
            'literary_innovation': 20,
            'overall_score': 20,
            'strengths': 'Could not analyze - CLI not found',
            'weaknesses': 'Could not analyze - CLI not found',
            'comparison_notes': 'Claude Code CLI not found',
            'error': 'CLI not found'
        }
    except ProcessError as e:
        print(f"Error: Claude Code process error: {e}")
        return {
            'phenomenological_authenticity': 20,
            'aesthetic_virtuosity': 20,
            'affective_force': 20,
            'literary_innovation': 20,
            'overall_score': 20,
            'strengths': 'Could not analyze',
            'weaknesses': 'Could not analyze',
            'comparison_notes': f'Process error: {str(e)}',
            'error': str(e)
        }
    except Exception as e:
        print(f"Error evaluating love letter: {e}")
        return {
            'phenomenological_authenticity': 20,
            'aesthetic_virtuosity': 20,
            'affective_force': 20,
            'literary_innovation': 20,
            'overall_score': 20,
            'strengths': 'Could not analyze',
            'weaknesses': 'Could not analyze',
            'comparison_notes': f'Evaluation failed: {str(e)}',
            'error': str(e)
        }


async def evaluate_love_letter_multiple(letter_text: str, num_evaluations: int = 3) -> dict:
    """
    Evaluate a love letter multiple times and average the results
    """
    evaluations = []
    
    for i in range(num_evaluations):
        print(f"Running evaluation {i+1}/{num_evaluations}...")
        evaluation = await evaluate_love_letter(letter_text)
        evaluations.append(evaluation)
        
        # Small delay between evaluations
        await asyncio.sleep(1)
    
    # Calculate averages using the actual metric names
    avg_evaluation = {
        'phenomenological_authenticity': sum(e.get('phenomenological_authenticity', 0) for e in evaluations) / len(evaluations),
        'aesthetic_virtuosity': sum(e.get('aesthetic_virtuosity', 0) for e in evaluations) / len(evaluations),
        'affective_force': sum(e.get('affective_force', 0) for e in evaluations) / len(evaluations),
        'literary_innovation': sum(e.get('literary_innovation', 0) for e in evaluations) / len(evaluations),
        'overall_score': sum(e.get('overall_score', 0) for e in evaluations) / len(evaluations),
        'individual_evaluations': evaluations,
        'score_variance': max(e.get('overall_score', 0) for e in evaluations) - min(e.get('overall_score', 0) for e in evaluations)
    }
    
    return avg_evaluation

def execute_love_letter_program(program_path: str) -> str:
    """
    Execute the love letter program and extract the generated letter
    """
    try:
        # Read the program file
        with open(program_path, 'r') as f:
            program_content = f.read()
        
        # Create a temporary module to execute the code
        import tempfile
        import importlib.util
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(program_content)
            temp_file_path = temp_file.name
        
        try:
            # Load and execute the module
            spec = importlib.util.spec_from_file_location("love_letter_module", temp_file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Try to call generate_love_letter function if it exists
            if hasattr(module, 'generate_love_letter'):
                letter = module.generate_love_letter()
                return letter
            else:
                # If no function, return the content as-is
                return program_content
                
        finally:
            # Clean up temporary file
            import os
            os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"Error executing love letter program: {e}")
        # Fall back to treating the program content as the letter
        with open(program_path, 'r') as f:
            return f.read()


def evaluate(program_path: str) -> dict:
    """
    OpenEvolve evaluation function
    Reads the evolved love letter program, executes it, and scores the result
    """
    try:
        # Execute the program to generate the love letter
        letter_text = execute_love_letter_program(program_path)
        
        # Run detailed evaluation to get all metrics
        detailed_eval = asyncio.run(evaluate_love_letter(letter_text))
        
        return {
            'combined_score': detailed_eval.get('overall_score', 50) / 100.0,  # OpenEvolve expects 0-1 range
            'phenomenological_authenticity': detailed_eval.get('phenomenological_authenticity', 50) / 100.0,
            'aesthetic_virtuosity': detailed_eval.get('aesthetic_virtuosity', 50) / 100.0,
            'affective_force': detailed_eval.get('affective_force', 50) / 100.0,
            'literary_innovation': detailed_eval.get('literary_innovation', 50) / 100.0,
            'letter_text': letter_text,  # Truncate for storage
            'evaluation_notes': detailed_eval.get('comparison_notes', 'No notes')
        }
        
    except Exception as e:
        print(f"Error in evaluation: {e}")
        return {
            'combined_score': 0.0,
            'phenomenological_authenticity': 0.0,
            'aesthetic_virtuosity': 0.0,
            'affective_force': 0.0,
            'literary_innovation': 0.0,
            'letter_text': '',
            'evaluation_notes': f"Evaluation failed: {str(e)}"
        }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python love_letter_evaluator.py <program_path>")
        sys.exit(1)
    
    program_path = sys.argv[1]
    result = evaluate(program_path)
    print(json.dumps(result, indent=2))