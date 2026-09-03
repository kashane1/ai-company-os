# POD artwork generation run

- Run ID: `20260903T221800Z`
- Concept: isolated seductive red lips with the exact supplied statement
- Exact text: `Technically, our mouths are the beginning of a hole that goes through our entire body.`
- Intended use: vertical print-on-demand artwork concept for shirts, mugs, and compatible Printify products
- Cleared directions: `style-1`, `style-2`, `style-3`, `style-4`
- Generation provider: built-in image generation
- Initial generation calls: 4
- Corrective generation calls: 3
- Total generation calls: 7
- Printify API calls: 0
- Etsy API calls: 0

## Direction results

| Direction | Final candidate | Source | Transparency | Copy | Cross-background review | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `style-1` | `style-1.png` | correction 1 after the initial request was blocked by image moderation | RGBA; transparent pixels present | Exact wording confirmed with macOS Vision OCR | Readable on light, dark, and neutral composites | Candidate passed |
| `style-2` | `style-2.png` | initial generation | RGBA; transparent pixels present | Exact wording confirmed visually; decorative type reduced OCR reliability | Readable on light, dark, and neutral composites | Candidate passed |
| `style-3` | `style-3.png` | initial generation | RGBA; transparent pixels present | Exact wording confirmed visually | Two dark text lines lose contrast on dark products | Candidate retained with limitation |
| `style-4` | `style-4.png` | initial generation | RGBA; transparent pixels present | Exact wording confirmed visually; ornate type reduced OCR reliability | Readable on light, dark, and neutral composites | Candidate passed |

All four candidates are 1024 x 1536 PNG concepts. They are suitable for direction selection, but they have not been upscaled or prepared as final production-resolution Printify masters.

## Corrective attempts

- `style-1`: the initial prompt was blocked by image moderation. A safer fashion-beauty restatement produced the retained transparent candidate with the requested lower-left lip bite.
- `style-3`, correction 1: changed the dark lettering to ivory with a black keyline, but the result returned as RGB with a baked checkerboard instead of transparency.
- `style-3`, correction 2: explicitly requested restoration of transparent RGBA output, but the result again returned as RGB without alpha.
- Per the skill's retry limit, no third correction was attempted for the same `style-3` transparency defect.

## Prompt summaries

- `style-1`: photoreal editorial beauty close-up consisting only of isolated glossy crimson lips; playful bite at the viewer-left side of the lower lip; bold high-contrast statement typography; transparent background.
- `style-2`: retro pop-art red lips with energetic halftone texture and curving display lettering; playful seductive mood; transparent background.
- `style-3`: luxury minimalist lacquer-red lips with elegant editorial typography and generous negative space; transparent background.
- `style-4`: dark-glam high-shine red lacquer lips with ornate gold-and-crimson statement typography; transparent background.

## Operation trace

1. Founder cleared all four style directions.
2. One initial image-generation call was made per direction.
3. Only failed requirements received corrective calls.
4. Transparent candidates and light/dark/neutral validation composites were saved locally.
5. No commerce upload, listing mutation, or publishing action was performed.
6. Final production preparation is waiting for founder direction selection.
