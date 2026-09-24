# Custom font — drop file here

**Pixel Code** is the finalized signature font (brand, headings, agent IDs, data).
The theme references it by `@font-face` in `src/index.css`. Drop the file here with
this exact name and it activates automatically:

| Font | Role | Expected filename |
|------|------|-------------------|
| **Pixel Code** | brand + headings + data (`.font-display`, `--font-mono`) | `PixelCode.woff2` (or `.ttf`) |

Other fonts load from Google Fonts (no file needed):
- **Inter** — body / UI text (readability)
- **Instrument Serif** (italic) — elegant accent words (`.font-accent`)

> Until `PixelCode.woff2` is here, headings fall back to a mono stack — nothing breaks.
> Tip: convert .ttf → .woff2 for smaller/faster loads.
