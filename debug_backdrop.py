#!/usr/bin/env python3
"""Debug backdrop generation - pure image processing."""
import sys
import random
import io
from pathlib import Path
from PIL import Image, ImageDraw
from mutagen import File as MutagenFile


def extract_album_art(file_path):
    """Extract album art from audio file as PIL Image."""
    try:
        audio = MutagenFile(file_path)
        if not audio or not hasattr(audio, 'tags') or not audio.tags:
            return None
        
        # Try ID3 picture frame
        if 'APIC:' in audio.tags:
            pic_data = audio.tags['APIC:'].data
            pil_img = Image.open(io.BytesIO(pic_data))
            return pil_img.convert('RGBA')
        
        # Try WMA picture
        if 'WM/Picture' in audio.tags:
            pic_data = audio.tags['WM/Picture']
            if hasattr(pic_data, '__iter__') and pic_data:
                pic_data = pic_data[0]
            if hasattr(pic_data, 'data'):
                pic_data = pic_data.data
            if isinstance(pic_data, bytes):
                pil_img = Image.open(io.BytesIO(pic_data))
                return pil_img.convert('RGBA')
    except Exception as e:
        print(f"  Error extracting art from {file_path}: {e}")
    
    return None


def collect_album_art(music_dirs):
    """Collect album artwork from music files."""
    images = []
    for music_dir in music_dirs:
        if not music_dir.exists():
            continue
        
        for file_path in music_dir.rglob('*'):
            if file_path.suffix.lower() not in ['.mp3', '.wma', '.flac', '.m4a']:
                continue
            
            img = extract_album_art(file_path)
            if img:
                images.append(img)
                print(f"  ✓ {file_path.name} ({img.width}x{img.height})")
                if len(images) >= 10:  # Collect up to 10 images
                    return images
    
    return images


def to_partial_monochrome(image, amount):
    """Convert image to pure grayscale."""
    return image.convert('L').convert('RGBA')


def compose_backdrop_image(width, height, image_pool, seed, theme_name, phase):
    """Generate backdrop image using pure PIL."""
    rng = random.Random(seed)
    
    # Create base image
    image = Image.new('RGBA', (width, height), (9, 2, 10, 255))
    
    # Grid setup
    unit = rng.choice([64, 72, 80])
    cols = max(1, (width + unit - 1) // unit)
    rows = max(1, (height + unit - 1) // unit)
    occupied = [[False for _ in range(cols)] for _ in range(rows)]
    
    def can_place(r, c, h_units, w_units):
        if r + h_units > rows or c + w_units > cols:
            return False
        for rr in range(r, r + h_units):
            for cc in range(c, c + w_units):
                if occupied[rr][cc]:
                    return False
        return True
    
    # Place tiles
    for r in range(rows):
        for c in range(cols):
            if occupied[r][c]:
                continue
            
            sizes = [3, 2, 1]
            valid = [s for s in sizes if can_place(r, c, s, s)]
            if not valid:
                chosen_h = chosen_w = 1
            else:
                chosen = valid[0]
                if len(valid) > 1 and rng.random() < 0.35:
                    chosen = rng.choice(valid)
                chosen_h = chosen_w = chosen
            
            # Mark occupied
            for rr in range(r, r + chosen_h):
                for cc in range(c, c + chosen_w):
                    occupied[rr][cc] = True
            
            # Calculate tile position and size
            x = c * unit
            y = r * unit
            w = width - x if c + chosen_w >= cols else chosen_w * unit
            h = height - y if r + chosen_h >= rows else chosen_h * unit
            
            if w <= 0 or h <= 0:
                continue
            
            # Scale and process tile
            sample = rng.choice(image_pool)
            tile = sample.resize((w, h), Image.Resampling.LANCZOS)
            tile_mono = to_partial_monochrome(tile, 1)
            
            # Paste tile
            image.paste(tile_mono, (x, y))
            
            # Draw border
            draw = ImageDraw.Draw(image)
            draw.rectangle([x, y, x + w - 1, y + h - 1], outline=(0, 0, 0, 168), width=4)
    
    # Diverse color palettes for gradient
    if theme_name == "dark":
        palettes = [
            [(255, 25, 82), (255, 170, 20), (100, 200, 255)],      # Red -> Orange -> Cyan
            [(138, 43, 226), (255, 105, 180), (50, 205, 50)],      # Purple -> Pink -> Green
            [(255, 69, 0), (255, 215, 0), (30, 144, 255)],         # Red -> Gold -> Blue
            [(0, 206, 209), (147, 51, 234), (255, 20, 147)],       # Teal -> Purple -> DeepPink
            [(34, 139, 34), (255, 140, 0), (220, 20, 60)],         # DarkGreen -> Orange -> Crimson
        ]
    else:
        palettes = [
            [(255, 105, 180), (135, 206, 255), (144, 238, 144)],   # Pink -> SkyBlue -> LightGreen
            [(255, 165, 0), (138, 43, 226), (64, 224, 208)],       # Orange -> Purple -> Turquoise
            [(220, 20, 60), (255, 215, 0), (50, 205, 50)],         # Crimson -> Gold -> Green
            [(30, 144, 255), (255, 105, 180), (255, 215, 0)],      # DodgerBlue -> Pink -> Gold
            [(75, 0, 130), (255, 69, 0), (144, 238, 144)],         # Indigo -> OrangeRed -> LightGreen
        ]
    
    c0, c1, c2 = palettes[phase % len(palettes)]
    
    # Random gradient direction
    direction = rng.choice(['vertical', 'horizontal', 'diagonal_tlbr', 'diagonal_trbl', 'radial'])
    
    # Recolorize the greyscale image with gradient colors
    # Convert to RGB first for pixel manipulation
    image_rgb = image.convert('RGB')
    pixels = image_rgb.load()
    
    width_actual, height_actual = image_rgb.size
    
    # For each pixel, get its position and map to gradient color
    for y in range(height_actual):
        for x in range(width_actual):
            # Calculate ratio based on direction
            if direction == 'vertical':
                ratio = y / height_actual
            elif direction == 'horizontal':
                ratio = x / width_actual
            elif direction == 'diagonal_tlbr':
                ratio = (x + y) / (width_actual + height_actual)
            elif direction == 'diagonal_trbl':
                ratio = (x + (height_actual - y)) / (width_actual + height_actual)
            else:  # radial
                cx, cy = width_actual / 2, height_actual / 2
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                ratio = dist / ((cx ** 2 + cy ** 2) ** 0.5)
            
            ratio = min(1.0, max(0.0, ratio))  # Clamp to 0-1
            
            # Interpolate between three colors
            if ratio < 0.5:
                t = ratio / 0.5
                gradient_color = tuple(int(c0[i] * (1 - t) + c1[i] * t) for i in range(3))
            else:
                t = (ratio - 0.5) / 0.5
                gradient_color = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
            
            r, g, b = pixels[x, y]
            # Use brightness to blend with gradient color
            brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255.0
            
            # Tint the color: shift towards gradient color based on brightness
            new_r = int(gradient_color[0] * brightness)
            new_g = int(gradient_color[1] * brightness)
            new_b = int(gradient_color[2] * brightness)
            
            pixels[x, y] = (new_r, new_g, new_b)
    
    image = image_rgb.convert('RGBA')
    
    # Edge gradients
    edge = max(220, min(width, height) // 3)
    
    def add_edge_vignette(img, edge_size, x_start, y_start, direction):
        """Add edge vignette (left/right/top/bottom)."""
        vignette = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        vignette_draw = ImageDraw.Draw(vignette)
        
        if direction == 'left':
            for x in range(edge_size):
                alpha = int(144 * (1 - x / edge_size))
                color = (0, 0, 0, alpha)
                vignette_draw.line([(x, 0), (x, height)], fill=color)
        elif direction == 'right':
            for x in range(edge_size):
                alpha = int(144 * (x / edge_size))
                color = (0, 0, 0, alpha)
                vignette_draw.line([(width - edge_size + x, 0), (width - edge_size + x, height)], fill=color)
        elif direction == 'top':
            for y in range(edge_size):
                alpha = int(136 * (1 - y / edge_size))
                color = (0, 0, 0, alpha)
                vignette_draw.line([(0, y), (width, y)], fill=color)
        elif direction == 'bottom':
            for y in range(edge_size):
                alpha = int(152 * (y / edge_size))
                color = (0, 0, 0, alpha)
                vignette_draw.line([(0, height - edge_size + y), (width, height - edge_size + y)], fill=color)
        
        return Image.alpha_composite(img, vignette)
    
    image = add_edge_vignette(image, edge, 0, 0, 'left')
    image = add_edge_vignette(image, edge, width - edge, 0, 'right')
    image = add_edge_vignette(image, edge, 0, 0, 'top')
    image = add_edge_vignette(image, edge, 0, height - edge, 'bottom')
    
    # Final dark veil
    final_veil = Image.new('RGBA', (width, height), (0, 0, 0, 24))
    image = Image.alpha_composite(image, final_veil)
    
    return image


# Configuration - tweak these values
CONFIG = {
    'width': 1920,
    'height': 1080,
    'seed': 42,
    'theme_name': 'dark',  # 'dark' or 'light'
    'phase': 0,  # 0-4 (color palette)
    'output_path': Path('backdrop_debug.png'),
}


print("=== Backdrop Generation Debug (Pure PIL) ===\n")

# Collect album art
print("Collecting album artwork...")
music_dirs = [Path.home() / 'Music', Path.home() / 'Desktop']
image_pool = collect_album_art(music_dirs)

if not image_pool:
    print("ERROR: No album artwork found!")
    sys.exit(1)

print(f"\nCollected {len(image_pool)} images\n")

# Generate 5 backdrops with different gradients
print("Generating 5 backdrops with different gradients...")
print(f"  Size: {CONFIG['width']}x{CONFIG['height']}")
print(f"  Seed: {CONFIG['seed']}")
print(f"  Theme: {CONFIG['theme_name']}")

try:
    for phase in range(5):
        print(f"\nGenerating backdrop {phase + 1}/5 (palette: {phase})...")
        
        image = compose_backdrop_image(
            width=CONFIG['width'],
            height=CONFIG['height'],
            image_pool=image_pool,
            seed=CONFIG['seed'],
            theme_name=CONFIG['theme_name'],
            phase=phase,
        )
        
        # Save to file with phase in filename
        output_path = CONFIG['output_path'].parent / f"backdrop_phase_{phase}.png"
        image.save(output_path)
        
        print(f"  ✓ Saved to: {output_path.absolute()}")
    
    print(f"\n✓ Generated 5 backdrops!")
    print(f"  Location: {CONFIG['output_path'].parent.absolute()}")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== To tweak the backdrop, modify the CONFIG dict ===")
print("Re-run this script after making changes.")
