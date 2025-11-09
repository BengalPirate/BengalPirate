import re
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CERTS_FILE = ROOT / "certs.md"
README_FILE = ROOT / "README.md"
OUTPUT_DIR = ROOT / "generated"
OUTPUT_IMG = OUTPUT_DIR / "cyber_radar.png"

# Headings MUST match your certs.md exactly
SECTIONS = [
    "Network Security",
    "Architecture and Engineering",
    "Security and Risk Management",
    "Assessment and Testing",
    "Software Security",
    "Forensics and Incident Handling",
    "Penetration Testing and Exploitation",
]

# Team color mapping (hex)
TEAM_COLORS = {
    "Forensics and Incident Handling": "#0000FF",  # Blue Team
    "Penetration Testing and Exploitation": "#FF0000",  # Red Team
    "Software Security": "#FFFF00",  # Yellow Team
    "Security and Risk Management": "#FFFFFF",  # White Team
    "Architecture and Engineering": "#00FF00",  # Green Team
    "Assessment and Testing": "#800080",  # Purple Team
    "Network Security": "#FF7F00",  # Orange Team
}

# Human-readable team names
TEAM_LABELS = {
    "Forensics and Incident Handling": "Blue Team",
    "Penetration Testing and Exploitation": "Red Team",
    "Software Security": "Yellow Team",
    "Security and Risk Management": "White Team",
    "Architecture and Engineering": "Green Team",
    "Assessment and Testing": "Purple Team",
    "Network Security": "Orange Team",
}


def parse_certs():
    stats = {s: {"total": 0, "done": 0} for s in SECTIONS}
    current = None

    lines = CERTS_FILE.read_text(encoding="utf-8").splitlines()

    for line in lines:
        stripped = line.strip()

        # section heading
        if stripped in SECTIONS:
            current = stripped
            continue

        # cert line: "- [ ] ..." or "- [x] ..."
        if stripped.startswith("- [") and current in stats:
            stats[current]["total"] += 1
            if len(stripped) > 3 and stripped[3].lower() == "x":
                stats[current]["done"] += 1

    return stats


def compute_scores(stats):
    scores = []
    total_done = 0
    total_all = 0

    for s in SECTIONS:
        total = stats[s]["total"]
        done = stats[s]["done"]
        total_all += total
        total_done += done

        percent = 0.0 if total == 0 else (done / total) * 100.0
        scores.append(percent)

    overall = 0.0 if total_all == 0 else (total_done / total_all) * 100.0
    return scores, overall


def pick_quote(overall_pct, total_done=0, total_all=0, section_scores=None):
    """
    Build a multi-line quote:
    - Overall % + counts
    - Strongest / balanced team region
    - Fun vibe line based on progress
    """
    pct = overall_pct
    done = total_done
    total = total_all
    section_scores = section_scores or [0.0] * len(SECTIONS)

    # ---------- vibe line based on % ----------
    if done == 0:
        vibe = "“This guy is a noob.” – Robot"
    elif done < 3:
        vibe = "“Has installed Kali... and that's about it.” – Robot"
    elif pct < 5:
        vibe = "“Fresh out the tutorial zone.” – Robot"
    elif pct < 10:
        vibe = "“Promising script kiddie energy.” – Robot"
    elif pct < 15:
        vibe = "“Finally figured out what nmap does.” – Robot"
    elif pct < 20:
        vibe = "“Learning to pivot... literally and figuratively.” – Robot"
    elif pct < 30:
        vibe = "“Up-and-coming cyber warrior.” – Robot"
    elif pct < 40:
        vibe = "“Knows their way around Wireshark and coffee.” – Robot"
    elif pct < 50:
        vibe = "“Getting dangerous with Metasploit.” – Robot"
    elif pct < 60:
        vibe = "“The SOC would call this guy first.” – Robot"
    elif pct < 70:
        vibe = "“Probably runs a home lab that hums like a jet engine.” – Robot"
    elif pct < 80:
        vibe = "“Respected in hacker circles.” – Robot"
    elif pct < 85:
        vibe = "“Too elite to use GUI tools anymore.” – Robot"
    elif pct < 90:
        vibe = "“Lives in tmux. Speaks only in acronyms.” – Robot"
    elif pct < 95:
        vibe = "“Makes APTs nervous.” – Robot"
    elif pct < 99:
        vibe = "“99th percentile cyber demigod.” – Robot"
    elif pct < 100:
        vibe = "“Rewrites firmware for fun.” – Robot"
    else:
        vibe = "“This guy is world class.” – Robot"

    # ---------- specialization / balance line ----------
    # Convert section_scores (0–100) to 0–1 fractions
    fractions = [s / 100.0 for s in section_scores]
    active_indices = [i for i, f in enumerate(fractions) if f > 0]

    if not active_indices:
        spec = "No dominant region yet – radar is empty."
    else:
        # sort indices by completion fraction
        ranked = sorted(active_indices, key=lambda i: fractions[i], reverse=True)
        top = ranked[0]
        top_frac = fractions[top]
        top_section = SECTIONS[top]
        top_team = TEAM_LABELS[top_section]

        second_frac = fractions[ranked[1]] if len(ranked) > 1 else 0.0
        # “balanced” if top and second are within 10 percentage points
        balanced_gap = abs(top_frac - second_frac)

        if len(ranked) > 2:
            third_frac = fractions[ranked[2]]
        else:
            third_frac = 0.0

        if balanced_gap < 0.10 and top_frac > 0.15:
            # balanced build across top 2–3 regions
            teams = []
            for idx in ranked[:3]:
                if fractions[idx] <= 0:
                    continue
                sec = SECTIONS[idx]
                teams.append(TEAM_LABELS[sec])

            teams = list(dict.fromkeys(teams))  # remove duplicates, preserve order

            if len(teams) == 1:
                spec = f"Build is focused on {teams[0]}."
            elif len(teams) == 2:
                spec = f"Build is balanced between {teams[0]} and {teams[1]}."
            else:
                spec = (
                    f"Build is well-balanced across {teams[0]}, {teams[1]}, "
                    f"and {teams[2]}."
                )
        else:
            spec = (
                f"Strongest region: {top_team} "
                f"({top_section}, {top_frac*100:.1f}% of that track complete)."
            )

    # ---------- assemble multi-line quote ----------
    lines = [
        f"Overall progress: {pct:.1f}% of the cert list ({done}/{total}).",
        spec,
        vibe,
    ]
    return "\n".join(lines)


def make_radar(scores):
    OUTPUT_DIR.mkdir(exist_ok=True)

    labels = SECTIONS
    num_vars = len(labels)

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    scores_loop = scores + scores[:1]
    angles_loop = angles + angles[:1]

    # colors in the same order as SECTIONS
    colors = [TEAM_COLORS[s] for s in SECTIONS]

    fig, ax = plt.subplots(subplot_kw=dict(polar=True))
    # slightly smaller figure; GitHub will still render it nicely
    fig.set_size_inches(4, 4)

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    # smaller theta labels
    ax.set_thetagrids(np.degrees(angles), labels, fontsize=7)

    ax.set_ylim(0, 100)
    # smaller radial labels
    ax.set_rgrids([20, 40, 60, 80, 100], angle=0, fontsize=6)

    # background
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#111111")

    # colored wedges per axis
    for i, score in enumerate(scores):
        color = colors[i]
        ax.fill(
            [angles[i], angles[i]],
            [0, score],
            color=color,
            alpha=0.35,
            edgecolor="none",
        )

    # polygon outline
    ax.plot(angles_loop, scores_loop, color="#FFFFFF", linewidth=1.5)
    ax.fill(angles_loop, scores_loop, color="#888888", alpha=0.15)

    ax.set_title("Cyber Team Spectrum", pad=15, color="white", fontsize=10)

    # fine-tune tick label sizes/colors
    for label in ax.get_xticklabels():
        label.set_color("white")
        label.set_fontsize(7)
    for label in ax.get_yticklabels():
        label.set_color("gray")
        label.set_fontsize(6)

    plt.tight_layout()
    fig.savefig(OUTPUT_IMG, dpi=150, bbox_inches="tight", transparent=True)
    plt.close(fig)



def update_readme(quote):
    readme = README_FILE.read_text(encoding="utf-8")

    pattern = re.compile(
        r"<!-- radar-start -->.*?<!-- radar-end -->",
        re.DOTALL,
    )

    # Turn each line of the quote into a Markdown blockquote line
    block = "\n".join(f"> {line}" for line in quote.splitlines())

    replacement = (
        "<!-- radar-start -->\n"
        "![Cyber Skill Radar](generated/cyber_radar.png)\n\n"
        f"{block}\n"
        "<!-- radar-end -->"
    )

    new_readme = re.sub(pattern, replacement, readme)
    README_FILE.write_text(new_readme, encoding="utf-8")



def main():
    stats = parse_certs()
    scores, overall = compute_scores(stats)
    total_done = sum(v["done"] for v in stats.values())
    total_all = sum(v["total"] for v in stats.values())

    quote = pick_quote(overall, total_done, total_all, scores)
    make_radar(scores)
    update_readme(quote)


if __name__ == "__main__":
    main()
