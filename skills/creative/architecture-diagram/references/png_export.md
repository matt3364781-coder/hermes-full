# PNG Export for Architecture Diagrams

When the user needs a shareable image (Telegram, docs, PRs), render the HTML diagram to PNG using Python + Pillow.

## Environment

- **System Python lacks PIL.** Use the project venv at `/opt/onebot3.0/.venv/` which has Pillow installed.
- If that venv is unavailable, install with: `pip install Pillow --break-system-packages` (Ubuntu 24.04 PEP 668 workaround)

## Rendering Script

```python
from PIL import Image, ImageDraw, ImageFont

W, H = 1400, 2000  # Adjust to diagram size
img = Image.new('RGB', (W, H), '#020617')
draw = ImageDraw.Draw(img)

# Load JetBrains Mono or fallback to DejaVu
try:
    font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', 28)
    font_sub = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 16)
    font_text = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 14)
    font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 11)
except:
    font_title = font_sub = font_text = font_small = ImageFont.load_default()

# Semantic color palette (matches architecture-diagram skill)
COLORS = {
    'cyan':     '#22d3ee',
    'emerald':  '#34d399',
    'violet':   '#a78bfa',
    'amber':    '#fbbf24',
    'rose':     '#fb7185',
    'orange':   '#fb923c',
    'slate':    '#94a3b8',
    'white':    '#ffffff',
}

# Dark fill variants for components
FILLS = {
    'amber':   '#2d1a00',
    'emerald': '#0f3d22',
    'violet':  '#241447',
    'rose':    '#3d0f1a',
    'orange':  '#3d2600',
    'cyan':    '#0f2d3d',
    'slate':   '#1e293b',
}

# Helper: rounded rectangle
def round_rect(x, y, w, h, r, fill, stroke, width=2):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=stroke, width=width)

# Helper: centered text
def ctext(x, y, w, text, font, fill):
    bbox = draw.textbbox((0,0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x + (w - tw) // 2, y), text, fill=fill, font=font)

# Helper: arrow with polygon head
def arrow(x1, y1, x2, y2, color, width=2):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # Simple arrowhead (pointing down/right)
    if y2 > y1:
        draw.polygon([(x2-5, y2-8), (x2+5, y2-8), (x2, y2)], fill=color)
    elif x2 > x1:
        draw.polygon([(x2-8, y2-5), (x2-8, y2+5), (x2, y2)], fill=color)

# Build diagram programmatically...
# (see /tmp/onebot_architecture_skill.png for full ONEBOT 3.0 example)

img.save('/tmp/output.png')
```

## Key Lessons from ONEBOT 3.0 Session

1. **Always use the project venv** (`/opt/onebot3.0/.venv/`) for Pillow — system Python lacks it
2. **Render both formats** — user expects HTML (browser) + PNG (shareable) as concrete evidence
3. **Match the skill color palette exactly** — semantic mapping is the value proposition
4. **Summary cards at bottom** — three-column grid with colored dots, matching the HTML output
