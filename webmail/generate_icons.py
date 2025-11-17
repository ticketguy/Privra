#!/usr/bin/env python3
"""Generate PWA icons for Privra Mail"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create icons directory
os.makedirs('static/icons', exist_ok=True)

# Icon sizes
sizes = [72, 96, 128, 144, 152, 192, 384, 512]

# Create gradient background with email icon
for size in sizes:
    # Create image
    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)

    # Create gradient (purple)
    for y in range(size):
        r = int(102 + (118 - 102) * y / size)  # 667eea to 764ba2
        g = int(126 + (75 - 126) * y / size)
        b = int(234 + (162 - 234) * y / size)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # Draw envelope icon (simple)
    margin = size // 6
    envelope_width = size - (margin * 2)
    envelope_height = int(envelope_width * 0.6)
    top = (size - envelope_height) // 2
    left = margin
    right = left + envelope_width
    bottom = top + envelope_height

    # Draw envelope rectangle
    draw.rectangle([left, top, right, bottom], outline='white', width=max(2, size//50))

    # Draw envelope flap (V shape)
    mid_x = size // 2
    mid_y = top + envelope_height // 2
    draw.line([left, top, mid_x, mid_y], fill='white', width=max(2, size//50))
    draw.line([mid_x, mid_y, right, top], fill='white', width=max(2, size//50))

    # Save
    img.save(f'static/icons/icon-{size}x{size}.png', 'PNG', quality=95)
    print(f'✓ Created icon-{size}x{size}.png')

print('\n✓ All PWA icons generated successfully!')
