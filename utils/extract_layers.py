#!/usr/bin/env python3
"""
Fixed character layer extraction script
Properly extracts mouth, eyes, and body layers with correct masking
"""

from PIL import Image, ImageDraw
import os
import numpy as np

# Paths
ASSETS_DIR = "assets"
CHAR_CLOSED = os.path.join(ASSETS_DIR, "char_closed.png")
CHAR_OPEN = os.path.join(ASSETS_DIR, "char_open.png")
OUTPUT_DIR = os.path.join(ASSETS_DIR, "character")

# Define regions (coordinates for 1024x1024 image)
# These regions will be extracted and filled in the body layer
MOUTH_REGION = (420, 520, 620, 670)  # (left, top, right, bottom)
LEFT_EYE_CENTER = (380, 475)  # Center of left eye
RIGHT_EYE_CENTER = (660, 475)  # Center of right eye
EYE_RADIUS = 80  # Radius for eye region

def create_transparent_copy(img):
    """Create a transparent copy of the image"""
    return Image.new('RGBA', img.size, (0, 0, 0, 0))

def extract_region_as_layer(img, region):
    """Extract a region and return as transparent layer (same size as original)"""
    left, top, right, bottom = region
    result = create_transparent_copy(img)
    cropped = img.crop(region)
    result.paste(cropped, (left, top))
    return result

def get_background_color_at_region(img, region):
    """Sample pixels around a region to get background color"""
    left, top, right, bottom = region
    # Sample pixels from edges
    img_array = np.array(img)

    # Get pixels from a ring around the region
    samples = []
    # Top edge
    if top > 10:
        samples.extend(img_array[top-10:top, left:right].reshape(-1, 4))
    # Bottom edge
    if bottom < img.height - 10:
        samples.extend(img_array[bottom:bottom+10, left:right].reshape(-1, 4))
    # Left edge
    if left > 10:
        samples.extend(img_array[top:bottom, left-10:left].reshape(-1, 4))
    # Right edge
    if right < img.width - 10:
        samples.extend(img_array[top:bottom, right:right+10].reshape(-1, 4))

    if len(samples) > 0:
        samples = np.array(samples)
        # Filter out transparent pixels
        opaque = samples[samples[:, 3] > 200]
        if len(opaque) > 0:
            # Return median color
            median_color = tuple(np.median(opaque, axis=0).astype(int))
            return median_color

    # Default: green circuit board color
    return (140, 180, 60, 255)

def fill_region(img, region, color):
    """Fill a region with a solid color"""
    result = img.copy()
    draw = ImageDraw.Draw(result)
    draw.rectangle(region, fill=color)
    return result

def fill_circle(img, center, radius, color):
    """Fill a circular region with a solid color"""
    result = img.copy()
    draw = ImageDraw.Draw(result)
    x, y = center
    bbox = (x - radius, y - radius, x + radius, y + radius)
    draw.ellipse(bbox, fill=color)
    return result

def create_intermediate_mouth(closed_mouth, open_mouth, alpha):
    """Create intermediate mouth state by blending"""
    return Image.blend(closed_mouth.convert('RGBA'), open_mouth.convert('RGBA'), alpha)

def main():
    print("Loading character images...")
    char_closed = Image.open(CHAR_CLOSED).convert('RGBA')
    char_open = Image.open(CHAR_OPEN).convert('RGBA')
    print(f"Image size: {char_closed.size}")

    # Create output directories
    os.makedirs(os.path.join(OUTPUT_DIR, "base"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "mouths"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "eyes"), exist_ok=True)

    print("\n=== Step 1: Extract mouth layers ===")
    # Extract mouths
    mouth_closed = extract_region_as_layer(char_closed, MOUTH_REGION)
    mouth_closed.save(os.path.join(OUTPUT_DIR, "mouths", "closed.png"))
    print("   ✓ mouths/closed.png")

    mouth_open = extract_region_as_layer(char_open, MOUTH_REGION)
    mouth_open.save(os.path.join(OUTPUT_DIR, "mouths", "wide_open.png"))
    print("   ✓ mouths/wide_open.png")

    # Create intermediate mouth states
    mouth_medium = create_intermediate_mouth(mouth_closed, mouth_open, 0.6)
    mouth_medium.save(os.path.join(OUTPUT_DIR, "mouths", "medium_open.png"))
    print("   ✓ mouths/medium_open.png")

    mouth_small = create_intermediate_mouth(mouth_closed, mouth_open, 0.3)
    mouth_small.save(os.path.join(OUTPUT_DIR, "mouths", "small_open.png"))
    print("   ✓ mouths/small_open.png")

    print("\n=== Step 2: Extract eye layers ===")
    # For eyes, we'll create simple variations
    # Extract both eyes as one layer
    left, top = LEFT_EYE_CENTER[0] - EYE_RADIUS, LEFT_EYE_CENTER[1] - EYE_RADIUS
    right, bottom = RIGHT_EYE_CENTER[0] + EYE_RADIUS, RIGHT_EYE_CENTER[1] + EYE_RADIUS
    eyes_region = (left, top, right, bottom)

    eyes_normal = extract_region_as_layer(char_closed, eyes_region)
    eyes_normal.save(os.path.join(OUTPUT_DIR, "eyes", "normal.png"))
    print("   ✓ eyes/normal.png")

    # Create half-closed eyes (simple horizontal crop)
    eyes_half = create_transparent_copy(char_closed)
    # Crop vertically to make eyes look half-closed
    mid_y = (eyes_region[1] + eyes_region[3]) // 2
    half_height = 25
    half_region = (eyes_region[0], mid_y - half_height, eyes_region[2], mid_y + half_height)
    half_cropped = char_closed.crop(half_region)
    eyes_half.paste(half_cropped, (half_region[0], half_region[1]))
    eyes_half.save(os.path.join(OUTPUT_DIR, "eyes", "blink_half.png"))
    print("   ✓ eyes/blink_half.png")

    # Create closed eyes (horizontal lines)
    eyes_closed = create_transparent_copy(char_closed)
    draw = ImageDraw.Draw(eyes_closed)
    eye_y = (eyes_region[1] + eyes_region[3]) // 2
    # Left eye closed line
    draw.line([(LEFT_EYE_CENTER[0] - 50, eye_y), (LEFT_EYE_CENTER[0] + 50, eye_y)],
              fill=(50, 30, 20, 255), width=10)
    # Right eye closed line
    draw.line([(RIGHT_EYE_CENTER[0] - 50, eye_y), (RIGHT_EYE_CENTER[0] + 50, eye_y)],
              fill=(50, 30, 20, 255), width=10)
    eyes_closed.save(os.path.join(OUTPUT_DIR, "eyes", "blink_closed.png"))
    print("   ✓ eyes/blink_closed.png")

    print("\n=== Step 3: Create body layer (with mouth and eyes filled) ===")
    # Start with closed character as base
    body = char_closed.copy()

    # Get background color for mouth region
    mouth_fill_color = get_background_color_at_region(char_closed, MOUTH_REGION)
    print(f"   Mouth fill color: {mouth_fill_color}")

    # Fill mouth region with background color
    body = fill_region(body, MOUTH_REGION, mouth_fill_color)
    print("   ✓ Mouth region filled")

    # Get background color for eye regions
    eye_fill_color = get_background_color_at_region(char_closed, eyes_region)
    print(f"   Eye fill color: {eye_fill_color}")

    # Fill both eye regions with background color
    body = fill_circle(body, LEFT_EYE_CENTER, EYE_RADIUS, eye_fill_color)
    body = fill_circle(body, RIGHT_EYE_CENTER, EYE_RADIUS, eye_fill_color)
    print("   ✓ Eye regions filled")

    body.save(os.path.join(OUTPUT_DIR, "base", "body.png"))
    print("   ✓ base/body.png saved")

    print("\n" + "="*50)
    print("✅ Layer extraction complete!")
    print("="*50)
    print(f"\nGenerated files:")
    print(f"  - 1 body layer (with mouth and eyes filled)")
    print(f"  - 4 mouth states")
    print(f"  - 3 eye states")
    print(f"\nTotal: 8 layer images in {OUTPUT_DIR}/")
    print("\nYou can now run: python3 main.py")

if __name__ == "__main__":
    main()
