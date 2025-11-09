#!/usr/bin/env python3
import re
import math
from pathlib import Path
import io

import matplotlib
matplotlib.use("Agg")  # safe for GitHub Actions / headless
import matplotlib.pyplot as plt
import numpy as np
import imageio.v2 as imageio
import textwrap

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
CERTS_FILE = ROOT / "certs.md"
README_FILE = ROOT / "README.md"
OUTPUT_DIR = ROOT / "generated"
OUTPUT_IMG = OUTPUT_DIR / "cyber_radar.gif"

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

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

# ---------------------------------------------------------------------
# Parsing & scoring
# ---------------------------------------------------------------------


def parse_certs():
    """Parse certs.md and count total / completed certs per section."""
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
    """
    For each section:
      score = done / total * 100  (per-track normalization)
    Also compute overall progress across all certs.
    """
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


# ---------------------------------------------------------------------
# Quote logic
# ---------------------------------------------------------------------


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
    fractions = [s / 100.0 for s in section_scores]
    active_indices = [i for i, f in enumerate(fractions) if f > 0]

    if not active_indices:
        spec = "No dominant region yet – radar is empty."
    else:
        ranked = sorted(active_indices, key=lambda i: fractions[i], reverse=True)
        top = ranked[0]
        top_frac = fractions[top]
        top_section = SECTIONS[top]
        top_team = TEAM_LABELS[top_section]

        second_frac = fractions[ranked[1]] if len(ranked) > 1 else 0.0
        balanced_gap = abs(top_frac - second_frac)

        if len(ranked) > 2:
            third_frac = fractions[ranked[2]]
        else:
            third_frac = 0.0

        if balanced_gap < 0.10 and top_frac > 0.15:
            teams = []
            for idx in ranked[:3]:
                if fractions[idx] <= 0:
                    continue
                teams.append(TEAM_LABELS[SECTIONS[idx]])
            teams = list(dict.fromkeys(teams))

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

    lines = [
        f"Overall progress: {pct:.1f}% of the cert list ({done}/{total}).",
        spec,
        vibe,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------

def hex_to_rgb(hex_color: str):
    """Convert #RRGGBB to (r, g, b) in 0–1 range."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def blend_rgb(c1, c2, t=0.5):
    """Blend two RGB tuples."""
    return tuple((1 - t) * a + t * b for a, b in zip(c1, c2))

# ---------------------------------------------------------------------
# Animated radar
# ---------------------------------------------------------------------

def make_radar(scores):
    """
    Radar chart using a single lime-green color for all filled areas.
    Rhombus-like sections form between adjacent active axes.
    No color blending or per-team hues.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    num_vars = len(SECTIONS)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    base_scores = [max(0.0, min(100.0, s)) for s in scores]

    frames = []
    n_frames = 24  # keep for slight glow; set to 1 for static

    for frame in range(n_frames):
        phase = 2 * math.pi * frame / n_frames
        glow_alpha = 0.25 + 0.15 * (0.5 * (1 + math.sin(phase)))  # soft pulse
        lime_rgb = (0.0, 1.0, 0.5)  # lime-green RGB (≈ #00FF80)

        fig, ax = plt.subplots(subplot_kw=dict(polar=True))
        fig.set_size_inches(4.5, 4.5)
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels([])

        ax.set_ylim(0, 100)
        ax.set_rgrids([20, 40, 60, 80, 100], angle=0, fontsize=6)

        fig.patch.set_facecolor("#111111")
        ax.set_facecolor("#111111")

        for g in ax.yaxis.get_gridlines():
            g.set_color("#555555")
        for g in ax.xaxis.get_gridlines():
            g.set_color("#555555")

        # ------------------ LIME GREEN RHOMBUSES ------------------
        for i in range(num_vars):
            j = (i + 1) % num_vars
            r_i, r_j = base_scores[i], base_scores[j]
            if r_i <= 0.0 or r_j <= 0.0:
                continue

            theta_i, theta_j = angles[i], angles[j]
            midpoint_r = (r_i + r_j) / 2
            midpoint_theta = (theta_i + theta_j) / 2

            ax.fill(
                [theta_i, midpoint_theta, theta_j, theta_i],
                [r_i, midpoint_r, r_j, 0],
                color=lime_rgb,
                alpha=glow_alpha,
                edgecolor="none",
            )

        # Outline
        angles_loop = angles + [angles[0]]
        base_scores_loop = base_scores + [base_scores[0]]
        ax.plot(angles_loop, base_scores_loop, color="#00FF80", linewidth=1.8, alpha=0.9)

        # Labels
        label_radius = 110
        for angle, section in zip(angles, SECTIONS):
            text = "\n".join(textwrap.wrap(section, 12))
            if angle == 0:
                ha = "center"
            elif 0 < angle < math.pi:
                ha = "left"
            else:
                ha = "right"
            ax.text(angle, label_radius, text, ha=ha, va="center", color="white", fontsize=6)

        ax.set_title("Cyber Team Spectrum", pad=18, color="white", fontsize=11, fontweight="bold")
        for label in ax.get_yticklabels():
            label.set_color("gray")
            label.set_fontsize(6)

        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", transparent=True)
        buf.seek(0)
        frames.append(imageio.imread(buf))
        plt.close(fig)

    imageio.mimsave(OUTPUT_IMG, frames, duration=0.09, loop=0)


# ---------------------------------------------------------------------
# README update
# ---------------------------------------------------------------------


def update_readme(quote: str):
    readme = README_FILE.read_text(encoding="utf-8")

    pattern = re.compile(
        r"<!-- radar-start -->.*?<!-- radar-end -->",
        re.DOTALL,
    )

    block = "\n".join(f"> {line}" for line in quote.splitlines())

    replacement = (
        "<!-- radar-start -->\n"
        '<p align="center">\n'
        '  <img src="generated/cyber_radar.gif" width="550" alt="Cyber Skill Radar">\n'
        "</p>\n\n"
        f"{block}\n"
        "<!-- radar-end -->"
    )

    new_readme = re.sub(pattern, replacement, readme)
    README_FILE.write_text(new_readme, encoding="utf-8")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


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