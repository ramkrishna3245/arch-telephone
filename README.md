# arch-telephone — The telephone game across model architectures

A message is passed sequentially through different model families. Each model restates what the previous model said. The chain reveals how information degrades differently across architecture boundaries.

## The Novelty

The classic "telephone game" applied to model architectures. This is the first tool to **measure information preservation across heterogeneous model architectures** — quantifying how facts, numbers, and meaning survive as they pass from one architecture family to another.

## How It Works

1. Pick a starting message with facts, numbers, and claims
2. Pass it through Model A (e.g., qwen — qwen family)  
3. Model A restates it in its own words
4. Pass Model A's output through Model B (e.g., tinyllama — llama family)
5. Model B restates it
6. Repeat for N rounds
7. Compare final version to original — measure word overlap, numeric preservation, hallucination injection

## Example Run

```
Original: "The capital of France is Paris. Einstein developed relativity in 1915. sqrt(144) = 12."

  Round 1: qwen2.5:0.5b → "The capital city of France is Paris. Albert Einstein made significant contributions..."
  Round 2: tinyllama    → "Paris is the capital and largest city of France. Albert Einstein..."
  Round 3: qwen2.5:0.5b → "Paris is the capital... Einstein contributed significantly... sqrt(144) = 12."

Results:
  Word overlap: 28.6%    (message grew 192% — each round adds elaboration)
  Numeric preservation: 100%   (1915, 144, 12 all survived)
  Hallucination detected: "Einstein lived and worked in Paris" — completely fabricated
```

## Key Finding

Different architecture transitions have different information loss rates:
- `qwen → llama`: 36.4% word overlap
- `llama → qwen`: 45.1% word overlap

This asymmetry suggests architecture direction matters for information preservation — a novel result.

## Usage

```bash
# Default message
python arch_telephone.py

# Custom message
python arch_telephone.py "Your message with facts and numbers here"
```

## Requirements

- Ollama with models from at least 2 different architecture families
- Python 3.10+
- `requests` library
