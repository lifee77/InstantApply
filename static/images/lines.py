#!/usr/bin/env python3

import math
import random
from PIL import Image, ImageDraw

def generate_wavy_lines(
    width=2000,
    height=2000,
    line_count=50,
    amplitude=100,
    frequency=0.005,
    phase_shift=0.0,
    line_thickness=2
):
    """
    Generate a black-and-white image with wavy lines that resemble contour lines.

    :param width: Image width in pixels
    :param height: Image height in pixels
    :param line_count: How many horizontal lines to draw
    :param amplitude: Vertical amplitude of each wave
    :param frequency: Controls the wave's horizontal frequency
    :param phase_shift: Shift wave horizontally for each line
    :param line_thickness: Thickness (in pixels) of each drawn line
    :return: A PIL Image object with wavy lines
    """

    # Create a new white image
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Vertical space between lines
    spacing = height // (line_count + 1)

    for i in range(line_count):
        # y_base is the 'center' y for this line
        y_base = (i + 1) * spacing

        # Optional: vary the phase shift slightly per line for more organic feel
        local_phase = phase_shift + random.uniform(-0.2, 0.2)

        # Build a list of points along this wave
        points = []
        for x in range(width):
            # Basic wave formula: y = y_base + amplitude * sin(frequency*x + local_phase)
            y_offset = amplitude * math.sin(frequency * x + local_phase)
            y = y_base + y_offset
            points.append((x, y))

        # Draw the wave as a polyline
        draw.line(points, fill="black", width=line_thickness)

    return img

if __name__ == "__main__":
    # Customize these parameters as desired:
    WIDTH = 2000
    HEIGHT = 2000
    LINE_COUNT = 60      # Number of horizontal lines
    AMPLITUDE = 120      # Wave amplitude
    FREQUENCY = 0.008    # Horizontal frequency
    PHASE_SHIFT = 0.0    # Starting phase
    LINE_THICKNESS = 2   # Stroke thickness

    image = generate_wavy_lines(
        width=WIDTH,
        height=HEIGHT,
        line_count=LINE_COUNT,
        amplitude=AMPLITUDE,
        frequency=FREQUENCY,
        phase_shift=PHASE_SHIFT,
        line_thickness=LINE_THICKNESS
    )

    output_filename = "wavy_lines_output.png"
    image.save(output_filename, "PNG")
    print(f"Image saved as {output_filename}")