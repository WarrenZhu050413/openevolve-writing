"""
Essay Evaluator for OpenEvolve
Scores essays on human-AI relationships on a 1-100 scale using Claude Code SDK
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


# Enhanced discriminatory scoring system for essays on human-AI relationships
RUBRIC = """
You are an expert essayist and philosopher specializing in technology, consciousness, and human-machine relations.

EVALUATION STANDARDS (USE ULTRA-FINE DISTINCTIONS):
- PARADIGM-DEFINING (100): Theoretical perfection - redefines how humanity understands AI relations
- TRANSCENDENT (95-99): Beyond current discourse - creates entirely new frameworks of understanding
- SUBLIME (90-94): Revolutionary insight that fundamentally shifts the conversation
- IMMORTAL MASTERPIECE (85-89): Turing's "Computing Machinery and Intelligence" level
- HISTORIC MASTERWORK (80-84): Haraway's "Cyborg Manifesto", Wiener's "Cybernetics" level
- NEAR-MASTERPIECE (75-79): Approaches seminal works but lacks final transformative element
- PROTO-MASTERFUL (70-74): Contains seeds of paradigm shift, breakthrough moments
- EXCEPTIONAL (65-69): Original synthesis, memorable arguments, field-advancing
- DISTINGUISHED (60-64): Sophisticated analysis, publishable in top journals
- IMPRESSIVE (55-59): Strong intellectual merit with original insights
- ACCOMPLISHED (50-54): Graduate-level thinking, clear expertise
- PROFICIENT (45-49): Professional quality, technically rigorous
- CAPABLE (40-44): Solid analysis with moments of insight
- PROMISING (35-39): Shows potential, some compelling arguments
- COMPETENT (30-34): Adequate analysis, functional argumentation
- DECENT (25-29): Acceptable undergraduate work
- GOOD (20-24): Basic competence, above average for general population
- MEDIOCRE (15-19): Average, predictable arguments
- WEAK (10-14): Below average, surface-level thinking
- POOR (5-9): Seriously flawed logic, misunderstandings
- TERRIBLE (1-4): Incoherent argumentation
- ABSOLUTE FAILURE (0): Factually wrong or dangerously misleading

SCORING CRITERIA (Rate 0-100 for each with ultra-fine distinctions):

1. PHILOSOPHICAL DEPTH & ONTOLOGICAL INSIGHT (35%):
   - Consciousness exploration: Hard problem engagement vs surface assumptions
   - Posthuman/transhuman vision: Radical reimagining vs anthropocentric limits
   - Ethical sophistication: Complex moral landscapes vs simplistic binaries
   - Phenomenology of AI experience: Serious engagement with machine consciousness
   - Temporal analysis: Deep time, singularity, acceleration vs presentism
   - Agency and autonomy: Nuanced treatment of freedom/determinism
   - Embodiment theory: Physical/digital boundaries vs naive dualism
   - Existential implications: Authentic confrontation with human obsolescence

2. ARGUMENTATIVE RIGOR & ANALYTICAL PRECISION (30%):
   - Logical architecture: Syllogistic strength, valid inference chains
   - Evidence synthesis: Technical accuracy meets humanistic insight
   - Conceptual clarity: Precise terminology vs vague generalities
   - Counterargument engagement: Steel-manning opposition vs strawmen
   - Empirical grounding: Data-informed vs purely speculative
   - Theoretical sophistication: Complex frameworks vs simplistic models
   - Interdisciplinary integration: Seamless synthesis vs superficial borrowing
   - Epistemic humility: Acknowledging unknowns vs false certainty
   - Dialectical movement: Thesis-antithesis-synthesis progression

3. ORIGINALITY & PARADIGMATIC FORCE (25%):
   - Novel frameworks: New conceptual tools vs recycled ideas
   - Predictive power: Compelling futures vs obvious extrapolations
   - Metaphorical innovation: Fresh analogies that illuminate
   - Problem reframing: Seeing new questions vs old answers
   - Synthetic breakthroughs: Unexpected connections across domains
   - Imaginative reach: Radical possibilities vs incremental thinking
   - Contrarian insight: Productive challenge to consensus
   - Generative potential: Ideas that spawn further thinking
   - Memetic power: Concepts that stick and spread

4. RHETORICAL MASTERY & PROSE EXCELLENCE (10%):
   - Sentence craft: Varied, muscular prose vs monotonous style
   - Structural elegance: Architectural coherence vs rambling
   - Transitional fluidity: Seamless flow vs jarring shifts
   - Opening/closing power: Memorable bookends vs weak frames
   - Analogical precision: Illuminating comparisons vs forced metaphors
   - Rhythm and pacing: Dynamic tempo vs plodding progression
   - Voice authority: Commanding presence vs tentative hedging
   - Clarity without simplification: Accessible depth vs obscurantism

EVALUATION REQUIREMENTS:
- MOST essays should score 10-30 (mediocre to competent range)
- USE ULTRA-FINE DISTINCTIONS - a 73 is meaningfully different from a 74
- BE EXTREMELY STRICT - each point above 50 should be hard-earned
- Scores above 80 are reserved for actual paradigm-shifting works
- Scores above 90 should be nearly impossible
- JUSTIFY SCORES with specific textual evidence
- Think in single-point increments - each point represents real qualitative difference
- Compare explicitly to the greatest essays on technology and consciousness

FAMOUS ESSAY BENCHMARKS:
- Alan Turing's "Computing Machinery and Intelligence" (Score: 87)
- Donna Haraway's "A Cyborg Manifesto" (Score: 84)
- Norbert Wiener's "The Human Use of Human Beings" (Score: 83)
- Nick Bostrom's "Superintelligence" key chapters (Score: 81)
- Sherry Turkle's "Alone Together" key essays (Score: 80)
- Vernor Vinge's "The Coming Technological Singularity" (Score: 79)
- Ray Kurzweil's "The Singularity is Near" best sections (Score: 78)
- Jaron Lanier's "You Are Not a Gadget" key arguments (Score: 77)

Remember: A 22 vs 23 should represent a real qualitative difference. Use the FULL granularity.
"""


async def evaluate_essay(text: str) -> dict:
    """
    Evaluate an essay on human-AI relationships using enhanced discriminatory scoring
    Returns detailed evaluation with 4 criteria scores
    """
    
    evaluation_prompt = f"""
{RUBRIC}

ESSAY TO EVALUATE:
{text}

Return your evaluation in this exact format:
<output>
philosophical_depth:[0-100 score]
argumentative_rigor:[0-100 score]
originality_force:[0-100 score]
rhetorical_mastery:[0-100 score]
strengths:[specific textual examples with quotes]
weaknesses:[specific areas needing improvement]
comparison_notes:[explicit comparison to essay benchmarks]
</output>
"""
    
    try:
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt="You are an expert essayist and philosopher specializing in technology, consciousness, and human-AI relations. Provide detailed, discriminatory evaluations using the full 0-100 scoring range.",
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
                            if key in ['philosophical_depth', 'argumentative_rigor', 
                                      'originality_force', 'rhetorical_mastery']:
                                try:
                                    evaluation_data[key] = float(value)
                                except ValueError:
                                    evaluation_data[key] = 20.0  # Default to "good" level if parsing fails
                            else:
                                evaluation_data[key] = value
                    
                    # Always calculate weighted average programmatically
                    phil = evaluation_data.get('philosophical_depth', 0)
                    arg = evaluation_data.get('argumentative_rigor', 0)
                    orig = evaluation_data.get('originality_force', 0)
                    rhet = evaluation_data.get('rhetorical_mastery', 0)
                    evaluation_data['overall_score'] = (phil * 0.35 + arg * 0.30 + orig * 0.25 + rhet * 0.10)
                    
                    return evaluation_data
                else:
                    raise ValueError("No <output> section found in response")
                    
            except (ValueError, KeyError) as e:
                print(f"Warning: Could not parse output from response: {response_text}")
                # Fallback to simple scoring
                score = 20  # Default to "good" level
                return {
                    'philosophical_depth': score,
                    'argumentative_rigor': score,
                    'originality_force': score,
                    'rhetorical_mastery': score,
                    'overall_score': score,
                    'strengths': 'Could not analyze',
                    'weaknesses': 'Could not analyze',
                    'comparison_notes': f'Evaluation failed: {str(e)}'
                }
                
    except CLINotFoundError:
        print("Error: Claude Code CLI not found. Please install: npm install -g @anthropic-ai/claude-code")
        return {
            'philosophical_depth': 20,
            'argumentative_rigor': 20,
            'originality_force': 20,
            'rhetorical_mastery': 20,
            'overall_score': 20,
            'strengths': 'Could not analyze - CLI not found',
            'weaknesses': 'Could not analyze - CLI not found',
            'comparison_notes': 'Claude Code CLI not found',
            'error': 'CLI not found'
        }
    except ProcessError as e:
        print(f"Error: Claude Code process error: {e}")
        return {
            'philosophical_depth': 20,
            'argumentative_rigor': 20,
            'originality_force': 20,
            'rhetorical_mastery': 20,
            'overall_score': 20,
            'strengths': 'Could not analyze',
            'weaknesses': 'Could not analyze',
            'comparison_notes': f'Process error: {str(e)}',
            'error': str(e)
        }
    except Exception as e:
        print(f"Error evaluating essay: {e}")
        return {
            'philosophical_depth': 20,
            'argumentative_rigor': 20,
            'originality_force': 20,
            'rhetorical_mastery': 20,
            'overall_score': 20,
            'strengths': 'Could not analyze',
            'weaknesses': 'Could not analyze',
            'comparison_notes': f'Evaluation failed: {str(e)}',
            'error': str(e)
        }


async def evaluate_essay_multiple(text: str, num_evaluations: int = 3) -> dict:
    """
    Evaluate an essay multiple times and average the results
    """
    evaluations = []
    
    for i in range(num_evaluations):
        print(f"Running evaluation {i+1}/{num_evaluations}...")
        evaluation = await evaluate_essay(text)
        evaluations.append(evaluation)
        
        # Small delay between evaluations
        await asyncio.sleep(1)
    
    # Calculate averages using the actual metric names
    avg_evaluation = {
        'philosophical_depth': sum(e.get('philosophical_depth', 0) for e in evaluations) / len(evaluations),
        'argumentative_rigor': sum(e.get('argumentative_rigor', 0) for e in evaluations) / len(evaluations),
        'originality_force': sum(e.get('originality_force', 0) for e in evaluations) / len(evaluations),
        'rhetorical_mastery': sum(e.get('rhetorical_mastery', 0) for e in evaluations) / len(evaluations),
        'overall_score': sum(e.get('overall_score', 0) for e in evaluations) / len(evaluations),
        'individual_evaluations': evaluations,
        'score_variance': max(e.get('overall_score', 0) for e in evaluations) - min(e.get('overall_score', 0) for e in evaluations)
    }
    
    return avg_evaluation

def execute_essay_program(program_path: str) -> str:
    """
    Execute the essay program and extract the generated essay
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
            spec = importlib.util.spec_from_file_location("essay_module", temp_file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Try to call generate_essay function if it exists
            if hasattr(module, 'generate_essay'):
                essay = module.generate_essay()
                return essay
            else:
                # If no function, return the content as-is
                return program_content
                
        finally:
            # Clean up temporary file
            import os
            os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"Error executing essay program: {e}")
        # Fall back to treating the program content as the letter
        with open(program_path, 'r') as f:
            return f.read()


def evaluate(program_path: str) -> dict:
    """
    OpenEvolve evaluation function
    Reads the evolved essay program, executes it, and scores the result
    """
    try:
        # Execute the program to generate the essay
        text = execute_essay_program(program_path)
        
        # Run detailed evaluation to get all metrics
        detailed_eval = asyncio.run(evaluate_essay(text))
        
        return {
            'combined_score': detailed_eval.get('overall_score', 50) / 100.0,  # OpenEvolve expects 0-1 range
            'philosophical_depth': detailed_eval.get('philosophical_depth', 50) / 100.0,
            'argumentative_rigor': detailed_eval.get('argumentative_rigor', 50) / 100.0,
            'originality_force': detailed_eval.get('originality_force', 50) / 100.0,
            'rhetorical_mastery': detailed_eval.get('rhetorical_mastery', 50) / 100.0,
            'text': text,  # Truncate for storage
            'evaluation_notes': detailed_eval.get('comparison_notes', 'No notes')
        }
        
    except Exception as e:
        print(f"Error in evaluation: {e}")
        return {
            'combined_score': 0.0,
            'philosophical_depth': 0.0,
            'argumentative_rigor': 0.0,
            'originality_force': 0.0,
            'rhetorical_mastery': 0.0,
            'text': '',
            'evaluation_notes': f"Evaluation failed: {str(e)}"
        }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python essay_evaluator.py <program_path>")
        sys.exit(1)
    
    program_path = sys.argv[1]
    result = evaluate(program_path)
    print(json.dumps(result, indent=2))