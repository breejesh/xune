"""
Backdrop generation using pure image processing (PIL).
Thread-safe - generates static backdrop images saved to disk.
"""
from __future__ import annotations

import random
from pathlib import Path
from PIL import Image, ImageDraw

from app.common import get_logger

logger = get_logger(__name__)


def _to_partial_monochrome(image: Image.Image) -> Image.Image:
    """Convert image to grayscale."""
    return image.convert('L').convert('RGBA')


def compose_backdrop_image(
    width: int,
    height: int,
    image_pool: list[Image.Image],
    seed: int,
    theme_name: str,
    phase: int,
) -> Image.Image:
    """
    Generate backdrop image using pure PIL (thread-safe).
    Returns PIL Image, caller is responsible for saving.
    
    Args:
        width: Output width
        height: Output height
        image_pool: List of PIL Image objects (album art)
        seed: Random seed for reproducibility
        theme_name: 'dark' or 'light'
        phase: Phase for palette selection (0-4)
    
    Returns:
        PIL Image backdrop
    """
    # If no album images provided, return plain gradient without tiles
    if not image_pool:
        logger.error("No album images provided for backdrop generation.")
        # Create base image with gradient overlay
        image = Image.new('RGBA', (width, height), (9, 2, 10, 255))
        
        # Define palettes
        if theme_name == "dark":
            palettes = [
                [(255, 25, 82), (255, 170, 20), (100, 200, 255)],
                [(138, 43, 226), (255, 105, 180), (50, 205, 50)],
                [(255, 69, 0), (255, 215, 0), (30, 144, 255)],
                [(0, 206, 209), (147, 51, 234), (255, 20, 147)],
                [(34, 139, 34), (255, 140, 0), (220, 20, 60)],
            ]
        else:
            palettes = [
                [(255, 105, 180), (135, 206, 255), (144, 238, 144)],
                [(255, 165, 0), (138, 43, 226), (64, 224, 208)],
                [(220, 20, 60), (255, 215, 0), (50, 205, 50)],
                [(30, 144, 255), (255, 105, 180), (255, 215, 0)],
                [(75, 0, 130), (255, 69, 0), (144, 238, 144)],
            ]
        
        c0, c1, c2 = palettes[phase % len(palettes)]
        draw = ImageDraw.Draw(image)
        
        # Draw gradient overlay
        for y in range(height):
            ratio = y / height if height > 0 else 0
            if ratio < 0.5:
                t = ratio / 0.5
                r = int(c0[0] * (1 - t) + c1[0] * t)
                g = int(c0[1] * (1 - t) + c1[1] * t)
                b = int(c0[2] * (1 - t) + c1[2] * t)
            else:
                t = (ratio - 0.5) / 0.5
                r = int(c1[0] * (1 - t) + c2[0] * t)
                g = int(c1[1] * (1 - t) + c2[1] * t)
                b = int(c1[2] * (1 - t) + c2[2] * t)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b, 128))
        
        return image

    logger.info("Album images provided for backdrop generation.")

    rng = random.Random(seed)
    
    # Create base image
    image = Image.new('RGBA', (width, height), (9, 2, 10, 255))
    
    # Grid setup
    unit = rng.choice([64, 72, 80])
    cols = max(1, (width + unit - 1) // unit)
    rows = max(1, (height + unit - 1) // unit)
    occupied = [[False for _ in range(cols)] for _ in range(rows)]
    
    def can_place(r: int, c: int, h_units: int, w_units: int) -> bool:
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
            tile_mono = _to_partial_monochrome(tile)
            
            # Paste tile
            image.paste(tile_mono, (x, y))
            
            # Draw border
            draw = ImageDraw.Draw(image)
            draw.rectangle([x, y, x + w - 1, y + h - 1], outline=(0, 0, 0, 168), width=1)
    
    # Apply dark overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 70))
    image = Image.alpha_composite(image, overlay)
    
    # Define color palettes
    if theme_name == "dark":
        palettes = [
            [(255, 25, 82), (255, 170, 20), (100, 200, 255)],
            [(138, 43, 226), (255, 105, 180), (50, 205, 50)],
            [(255, 69, 0), (255, 215, 0), (30, 144, 255)],
            [(0, 206, 209), (147, 51, 234), (255, 20, 147)],
            [(34, 139, 34), (255, 140, 0), (220, 20, 60)],
        ]
    else:
        palettes = [
            [(255, 105, 180), (135, 206, 255), (144, 238, 144)],
            [(255, 165, 0), (138, 43, 226), (64, 224, 208)],
            [(220, 20, 60), (255, 215, 0), (50, 205, 50)],
            [(30, 144, 255), (255, 105, 180), (255, 215, 0)],
            [(75, 0, 130), (255, 69, 0), (144, 238, 144)],
        ]
    
    c0, c1, c2 = palettes[phase % len(palettes)]
    
    # Random gradient direction
    direction = rng.choice(['vertical', 'horizontal', 'diagonal_tlbr', 'diagonal_trbl', 'radial'])
    
    # Convert to RGB for pixel manipulation
    image_rgb = image.convert('RGB')
    pixels = image_rgb.load()
    
    # Apply gradient coloring with brightness-based tinting
    for y in range(height):
        for x in range(width):
            # Calculate gradient ratio based on direction
            if direction == 'vertical':
                ratio = y / height if height > 0 else 0
            elif direction == 'horizontal':
                ratio = x / width if width > 0 else 0
            elif direction == 'diagonal_tlbr':
                ratio = (x + y) / (width + height) if (width + height) > 0 else 0
            elif direction == 'diagonal_trbl':
                ratio = (x + (height - y)) / (width + height) if (width + height) > 0 else 0
            else:  # radial
                cx, cy = width / 2, height / 2
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                max_dist = ((cx ** 2 + cy ** 2) ** 0.5)
                ratio = dist / max_dist if max_dist > 0 else 0
            
            ratio = min(1.0, max(0.0, ratio))
            
            # Interpolate between three colors
            if ratio < 0.5:
                t = ratio / 0.5
                gradient_color = tuple(int(c0[i] * (1 - t) + c1[i] * t) for i in range(3))
            else:
                t = (ratio - 0.5) / 0.5
                gradient_color = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
            
            # Get current pixel and calculate brightness
            current = pixels[x, y]
            r, g, b = current if isinstance(current, tuple) else (current, current, current)
            brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255.0
            
            # Tint by gradient (multiply brightness)
            new_r = max(0, min(255, int(gradient_color[0] * brightness)))
            new_g = max(0, min(255, int(gradient_color[1] * brightness)))
            new_b = max(0, min(255, int(gradient_color[2] * brightness)))
            
            pixels[x, y] = (new_r, new_g, new_b)
    
    # Convert back to RGBA
    image = image_rgb.convert('RGBA')
    
    # Edge vignettes
    edge = max(220, min(width, height) // 3)
    
    def add_edge_vignette(img: Image.Image, edge_size: int, direction: str) -> Image.Image:
        """Add edge vignette."""
        vignette = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        vignette_draw = ImageDraw.Draw(vignette)
        
        if direction == 'left':
            for x in range(edge_size):
                alpha = int(144 * (1 - x / edge_size))
                vignette_draw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))
        elif direction == 'right':
            for x in range(edge_size):
                alpha = int(144 * (x / edge_size))
                vignette_draw.line([(width - edge_size + x, 0), (width - edge_size + x, height)], fill=(0, 0, 0, alpha))
        elif direction == 'top':
            for y in range(edge_size):
                alpha = int(136 * (1 - y / edge_size))
                vignette_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        elif direction == 'bottom':
            for y in range(edge_size):
                alpha = int(152 * (y / edge_size))
                vignette_draw.line([(0, height - edge_size + y), (width, height - edge_size + y)], fill=(0, 0, 0, alpha))
        
        return Image.alpha_composite(img, vignette)
    
    image = add_edge_vignette(image, edge, 'left')
    image = add_edge_vignette(image, edge, 'right')
    image = add_edge_vignette(image, edge, 'top')
    image = add_edge_vignette(image, edge, 'bottom')
    
    # Final dark veil
    final_veil = Image.new('RGBA', (width, height), (0, 0, 0, 24))
    image = Image.alpha_composite(image, final_veil)
    
    return image
