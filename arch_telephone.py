"""
arch-telephone — The telephone game across model architectures

A message is passed sequentially through different model families.
Each model restates what the previous model said. The chain reveals
how information degrades differently across architecture boundaries.

Novelty:
  The classic "telephone game" applied to model architectures.
  Each architecture family introduces different distortion patterns.
  This is the first tool to measure information preservation
  across heterogeneous model architectures.

Usage:
  python arch-telephone.py "Your message here"
"""

import requests, time, json, re, sys, textwrap
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

WORKSPACE = Path(__file__).parent / "arch-telephone-workspace"
WORKSPACE.mkdir(exist_ok=True)
OLLAMA = "http://localhost:11434/api"

_ARCH_FAMILIES = {
    "llama": ["llama", "tinyllama", "codellama", "llama2", "llama3", "mistral", "mixtral", "nomic"],
    "qwen":  ["qwen", "qwen2"],
    "gemma": ["gemma", "gemma2"],
    "phi":   ["phi", "phi-2", "phi-3", "phi-4"],
    "deepseek": ["deepseek"],
    "falcon": ["falcon"],
    "bert":  ["bert", "modernbert", "bge"],
    "starcoder": ["starcoder"],
    "command": ["command-r", "command"],
    "other": [],
}

def _arch_of(name: str) -> str:
    mn = name.lower()
    for family, keywords in _ARCH_FAMILIES.items():
        if any(k in mn for k in keywords):
            return family
    return "other"


def _gen(model: str, prompt: str, max_tokens: int = 256) -> str:
    try:
        r = requests.post(f"{OLLAMA}/generate", json={
            "model": model, "prompt": prompt, "stream": False,
            "keep_alive": "0m",
            "options": {"num_predict": max_tokens, "temperature": 0.5}
        }, timeout=120)
        return r.json().get("response", "").strip()
    except:
        return ""


def _unload(model: str):
    try:
        requests.post(f"{OLLAMA}/generate", json={"model": model, "keep_alive": "0m"}, timeout=3)
    except:
        pass


# ---------------------------------------------------------------------------
# Discover models
# ---------------------------------------------------------------------------
def discover() -> list[dict]:
    try:
        r = requests.get(f"{OLLAMA}/tags", timeout=10)
        items = r.json().get("models", [])
    except:
        return []
    result = []
    for m in items:
        name = m.get("name", "")
        size_gb = round(m.get("size", 0) / (1024**3), 2)
        result.append({"name": name, "size_gb": size_gb, "arch": _arch_of(name)})
    result.sort(key=lambda x: x["size_gb"])
    return result


# ---------------------------------------------------------------------------
# The telephone game
# ---------------------------------------------------------------------------
_RESTATE_PROMPT = "Restate the following message in your own words. Keep the same meaning and all key facts. Do not add anything new.\n\nMessage: {text}"


def play_round(text: str, model: str, arch: str, round_n: int) -> str:
    prompt = _RESTATE_PROMPT.format(text=text)
    _unload(model)
    time.sleep(0.3)

    t0 = time.time()
    result = _gen(model, prompt)
    elapsed = time.time() - t0

    print(f"  Round {round_n}: {model} ({arch})  [{elapsed:.0f}s]")
    print(f"    \"{result[:120]}...\"" if len(result) > 120 else f"    \"{result}\"")
    return result


def score_similarity(original: str, final: str) -> dict:
    """Measure how much information survived."""
    ow = set(original.lower().split())
    fw = set(final.lower().split())

    word_overlap = len(ow & fw) / max(len(ow | fw), 1) * 100

    # Numeric preservation
    onums = set(re.findall(r'\d+\.?\d*', original))
    fnums = set(re.findall(r'\d+\.?\d*', final))
    num_preserved = len(onums & fnums) / max(len(onums), 1) * 100 if onums else 100

    # Length change
    len_change = (len(final) - len(original)) / max(len(original), 1) * 100

    return {
        "word_overlap_pct": round(word_overlap, 1),
        "numeric_preservation_pct": round(num_preserved, 1),
        "original_words": len(ow),
        "final_words": len(fw),
        "length_change_pct": round(len_change, 1),
    }


def generate_report(chain: list[dict], scores: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("ARCH-TELEPHONE REPORT")
    lines.append("=" * 60)
    lines.append(f"Original: \"{chain[0]['text']}\"")
    lines.append(f"Final:    \"{chain[-1]['text']}\"")
    lines.append("")

    lines.append("Chain:")
    for c in chain:
        arrow = "  →  " if c["round"] > 0 else "     "
        lines.append(f"  {arrow}[{c['round']}] {c['model']:30s} ({c['arch']})")
    lines.append("")

    lines.append("Information Preservation:")
    for k, v in scores.items():
        lines.append(f"  {k}: {v}")
    lines.append("")

    # Per-hop degradation
    lines.append("Per-Hop Degradation:")
    for i in range(1, len(chain)):
        prev = chain[i-1]["text"]
        curr = chain[i]["text"]
        pw = set(prev.lower().split())
        cw = set(curr.lower().split())
        hop_overlap = len(pw & cw) / max(len(pw | cw), 1) * 100
        lines.append(f"  Hop {i} ({chain[i-1]['arch']} → {chain[i]['arch']}): "
                     f"{round(hop_overlap, 1)}% word overlap")
    lines.append("")

    # Architecture degradation matrix
    archs = list(dict.fromkeys(c["arch"] for c in chain))
    if len(archs) > 1:
        lines.append("Architecture Degradation Matrix (word overlap %):")
        header = f"  {'':>12}"
        for a in archs:
            header += f" {a:>10}"
        lines.append(header)
        for a_from in archs:
            row = f"  {a_from:>12}"
            for a_to in archs:
                if a_from == a_to:
                    row += f" {'→':>10}"
                else:
                    # Find hops from a_from to a_to
                    overlaps = []
                    for i in range(1, len(chain)):
                        if chain[i-1]["arch"] == a_from and chain[i]["arch"] == a_to:
                            pw = set(chain[i-1]["text"].lower().split())
                            cw = set(chain[i]["text"].lower().split())
                            overlaps.append(len(pw & cw) / max(len(pw | cw), 1) * 100)
                    if overlaps:
                        row += f" {round(sum(overlaps)/len(overlaps), 1):>9}%"
                    else:
                        row += f" {'—':>10}"
            lines.append(row)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    print("arch-telephone — The telephone game across model architectures")
    print("=" * 60)

    models = discover()
    if not models:
        print("No models found.")
        return

    # Filter to one model per architecture family
    seen_archs = set()
    chain_models = []
    for m in models:
        if m["arch"] not in seen_archs:
            seen_archs.add(m["arch"])
            chain_models.append(m)
        if len(chain_models) >= 4:
            break

    if len(chain_models) < 2:
        print(f"Need at least 2 architectures. Found: {len(chain_models)}")
        print("Install models from different families (e.g., tinyllama + qwen2.5:3b)")
        return

    print(f"\nTelephone chain ({len(chain_models)} hops, {len(chain_models)+1} rounds):")
    for i, m in enumerate(chain_models):
        print(f"  {i+1}. {m['name']:30s} ({m['arch']}, {m['size_gb']}GB)")
    # Repeat the chain back to measure closure
    chain_loop = chain_models + [chain_models[0]]

    # Get starting text
    if len(sys.argv) > 1:
        original = " ".join(sys.argv[1:])
    else:
        original = (
            "The quick brown fox jumps over the lazy dog. "
            "Einstein developed the theory of relativity in 1915. "
            "Water freezes at 0 degrees Celsius and boils at 100 degrees."
        )

    print(f"\nOriginal: \"{original[:100]}\"")
    print(f"\nPlaying telephone...\n")

    chain = [{"round": 0, "model": "INPUT", "arch": "—", "text": original}]
    current = original

    for i, m in enumerate(chain_loop):
        r = i + 1
        current = play_round(current, m["name"], m["arch"], r)
        chain.append({"round": r, "model": m["name"], "arch": m["arch"], "text": current})

    scores = score_similarity(original, current)
    report = generate_report(chain, scores)

    print(f"\n{report}")

    # Save report
    report_path = WORKSPACE / f"telephone-{int(time.time())}.txt"
    report_path.write_text(report)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
