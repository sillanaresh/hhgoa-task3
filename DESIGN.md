---
name: FaceProof
description: A calm evidence workbench for live face search and public verification
colors:
  proof-teal: "oklch(0.45 0.074 200)"
  proof-teal-deep: "oklch(0.39 0.076 200)"
  proof-wash: "oklch(0.925 0.038 195)"
  proof-on-fill: "oklch(0.997 0.003 190)"
  ink-strong: "oklch(0.22 0.02 205)"
  ink: "oklch(0.34 0.025 205)"
  ink-muted: "oklch(0.49 0.022 205)"
  mineral-paper: "oklch(0.982 0.008 190)"
  raised-paper: "oklch(0.997 0.003 190)"
  rule: "oklch(0.875 0.018 190)"
  warning-rust: "oklch(0.51 0.11 55)"
  danger-rust: "oklch(0.49 0.15 27)"
  focus-ink: "oklch(0.22 0.02 205)"
typography:
  display:
    fontFamily: "Bricolage Grotesque, Avenir Next, sans-serif"
    fontSize: "clamp(3rem, 7.5vw, 6.6rem)"
    fontWeight: 650
    lineHeight: 0.91
    letterSpacing: "-0.07em"
  title:
    fontFamily: "Bricolage Grotesque, Avenir Next, sans-serif"
    fontSize: "clamp(1.35rem, 2vw, 1.65rem)"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.035em"
  body:
    fontFamily: "IBM Plex Sans, Helvetica Neue, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "IBM Plex Mono, SFMono-Regular, monospace"
    fontSize: "0.72rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.07em"
rounded:
  sm: "0.45rem"
  md: "0.75rem"
  lg: "1rem"
  pill: "999px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
  section: "4rem"
components:
  button-primary:
    backgroundColor: "{colors.proof-teal}"
    textColor: "{colors.raised-paper}"
    rounded: "{rounded.sm}"
    padding: "0 1.25rem"
    height: "2.75rem"
  button-secondary:
    backgroundColor: "{colors.raised-paper}"
    textColor: "{colors.ink-strong}"
    rounded: "{rounded.sm}"
    padding: "0 1rem"
    height: "2.75rem"
  evidence-surface:
    backgroundColor: "{colors.raised-paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "2rem"
  status-chip:
    backgroundColor: "{colors.proof-wash}"
    textColor: "{colors.proof-teal-deep}"
    rounded: "{rounded.pill}"
    padding: "0.25rem 0.75rem"
---

# Design System: FaceProof

## Overview

**Creative North Star: "The Public Evidence Desk"**

FaceProof feels like a careful review desk built for a judge who has only a few minutes. Large editorial type establishes the claim, while thin rules, quiet paper tones, and a persistent run record expose the supporting work. The interface is calm, information dense where evidence matters, and restrained everywhere else.

The system rejects crypto spectacle and artificial certainty. Status comes from explicit words, source links, scores, timestamps, and public transaction facts. Layout moves from a two column desktop workbench to one ordered mobile document without changing the evidence hierarchy.

**Key Characteristics:**

- Mineral paper instead of pure white or dark dashboard chrome.
- One teal proof signal used for active, matched, and verified states.
- Editorial display type paired with neutral body copy and mono evidence labels.
- Real stage detail instead of decorative progress.
- Thin rules and tonal surfaces instead of stacked card decoration.

## Colors

The palette uses cool mineral neutrals and one restrained teal so public proof reads as a state, not a spectacle.

### Primary

- **Mineral Proof Teal** (`oklch(0.45 0.074 200)`): Primary actions, active status, selected evidence, and verified records.
- **Deep Proof Teal** (`oklch(0.39 0.076 200)`): Hover states and strong text on teal washes.
- **Proof Wash** (`oklch(0.925 0.038 195)`): Low emphasis confirmation backgrounds and active step halos.

### Neutral

- **Carbon Ink** (`oklch(0.22 0.02 205)`): Headlines, decisive labels, and rules that establish structure.
- **Slate Ink** (`oklch(0.34 0.025 205)`): Primary body copy.
- **Quiet Ink** (`oklch(0.49 0.022 205)`): Secondary explanation and metadata.
- **Mineral Paper** (`oklch(0.982 0.008 190)`): Page background.
- **Raised Paper** (`oklch(0.997 0.003 190)`): Work surfaces.
- **Hairline Rule** (`oklch(0.875 0.018 190)`): Dividers and low emphasis boundaries.

### Tertiary

- **Warning Rust** (`oklch(0.51 0.11 55)`): Irreversible publication approval.
- **Failure Rust** (`oklch(0.49 0.15 27)`): Failed stages and recovery surfaces.

### Named Rules

**The One Proof Signal Rule.** Teal means that work is active, selected, matched, or verified. It is not a general decorative accent.

**The Public Write Rule.** The irreversible blockchain approval uses rust until confirmation. It must not look identical to an ordinary local action.

## Typography

**Display Font:** Bricolage Grotesque with Avenir Next and sans-serif fallback

**Body Font:** IBM Plex Sans with Helvetica Neue and sans-serif fallback

**Label/Mono Font:** IBM Plex Mono with SFMono-Regular and monospace fallback

**Character:** Bricolage gives the product an authored editorial identity. IBM Plex keeps explanations and technical evidence direct, readable, and credible.

### Hierarchy

- **Display** (650, `clamp(3rem, 7.5vw, 6.6rem)`, 0.91): The home claim only. Use tight tracking and deliberate line breaks.
- **Title** (650, `clamp(1.35rem, 2vw, 1.65rem)`, 1.2): Workbench section titles and final verification state.
- **Body** (400, `1rem`, 1.55): Explanations, consent text, and recovery guidance. Keep long copy below 70 characters per line where practical.
- **Label** (500, `0.72rem`, 0.07em, uppercase): Evidence categories, context, and small immutable facts.
- **Evidence value** (500, responsive): Hashes, run IDs, scores, and transaction values.

### Named Rules

**The Claim and Evidence Rule.** Display type makes the claim once. Everything after it uses restrained title, body, and mono roles so evidence stays primary.

## Elevation

The system is mostly flat. Paper tone and hairline rules establish hierarchy. The work surface uses a one pixel light edge, not a floating shadow. Strong ambient shadow is reserved for the temporary toast because it must remain visible above the current task.

Motion is limited to state change. Buttons move one pixel only when pressed, active stages use a static halo, and result bars animate to their measured value. Reduced motion removes these effects.

**The Desk Surface Rule.** Evidence panels sit on the page like organized documents. Do not make every section float.

## Components

### Navigation

Use an edge aligned wordmark, a semantic proof mark, and one quiet network indicator. No full navigation menu is needed for a single purpose local workbench.

### Work surface

Use one raised paper surface for each major step. Internal evidence groups use rules, left accents, or tonal backgrounds. Avoid another rounded shell unless the content represents a distinct state such as approval or verified receipt.

### Stage rail

Keep all six real stages visible. Pair every marker with a title and current detail. On mobile, place the rail before the active work so the complete sequence remains understandable.

### Upload field

The complete drop area is the input label. Show a local preview without removing the file name or choose affordance. Put consent after the field and before the primary action.

### Match comparison

Show the input and retrieved candidate at equal visual weight. Keep the original source link and cosine score directly below them. The threshold marker must be visible and labeled.

### Evidence and approval

Display the complete fingerprint with copy and download actions. Explain the exact public payload before the publication button. A verified receipt must include network, block, transaction, confirmation count, public link, and repeat verification.

### Buttons and status

Controls are at least 44 pixels high. Primary actions use proof teal. Secondary actions use raised paper with a strong rule. Text actions do not imitate buttons. Status chips include words and never rely on color alone.

## Do's and Don'ts

### Do

- **Do** keep the source, score, threshold, and evidence fingerprint close to the selected result.
- **Do** preserve useful partial results when a later stage fails.
- **Do** use the exact six stage titles in the workbench and recording.
- **Do** keep line lengths, tap targets, focus rings, reduced motion, and 320 pixel layouts accessible.
- **Do** use one clear recovery action for every stopped state.

### Don't

- **Don't** make the product resemble a "cryptocurrency trading screen."
- **Don't** use a "neon cyber security dashboard."
- **Don't** create a "generic grid of statistic cards."
- **Don't** turn a similarity score into a confidence percentage or identity claim.
- **Don't** use decorative blockchain imagery, fake metrics, or simulated live search results.
- **Don't** add huge radii, glass effects, gradients without information meaning, or nested cards for ordinary grouping.
