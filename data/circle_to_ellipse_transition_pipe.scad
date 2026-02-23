/*
 * Transition Pipe: Circle to Flat Ellipse
 * =========================================
 * Start : Circular pipe, inner diameter 50mm (5cm)
 * End   : Flat ellipse, inner 80mm width x 10mm height (8cm x 1cm)
 * Length: 150mm (15cm)
 * Wall  : 2mm
 *
 * Usage: Open in OpenSCAD -> Render (F6) -> Export as STL
 *
 * 3D Print Tips:
 *   - Print standing up (circle end on bed) for best surface quality
 *   - Use supports if printing ellipse-end-down
 *   - Recommended layer height: 0.2mm
 *   - Infill: not needed (it's hollow), but 2-3 wall lines recommended
 */

// ============================================================
// Parameters (all in mm) - Adjust these to your needs
// ============================================================

wall_thickness = 2;          // Wall thickness (mm)

// Start cross-section (circle)
start_inner_diameter = 50;   // 5cm inner diameter

// End cross-section (flat ellipse)
end_inner_width  = 80;       // 8cm width
end_inner_height = 10;       // 1cm height

// Pipe length
pipe_length = 150;           // 15cm

// Straight extension lengths
start_straight = 10;         // Flat straight section at circle end (mm)
end_straight   = 5;          // Flat straight section at ellipse end (mm)

// Resolution settings
// For final STL export, use num_steps=100, $fn=90
num_steps = 50;              // Loft interpolation steps (50=fast preview, 100=smooth export)
$fn = 60;                    // Circle facet count (60=fast preview, 90=smooth export)

// ============================================================
// Derived values
// ============================================================

start_rx = start_inner_diameter / 2;   // 25mm
start_ry = start_inner_diameter / 2;   // 25mm (circle)
end_rx   = end_inner_width / 2;        // 40mm
end_ry   = end_inner_height / 2;       // 5mm

// ============================================================
// Modules
// ============================================================

/*
 * Creates a solid lofted shape by hulling consecutive
 * elliptical cross-section slices along the Z axis.
 *
 * Parameters:
 *   rx0, ry0 - start ellipse semi-axes
 *   rx1, ry1 - end ellipse semi-axes
 *   len      - total length along Z
 *   steps    - number of interpolation slices
 */
module lofted_solid(rx0, ry0, rx1, ry1, len, steps) {
    for (i = [0 : steps - 1]) {
        t0 = i / steps;
        t1 = (i + 1) / steps;

        // Interpolated semi-axes at each slice
        a0 = rx0 + (rx1 - rx0) * t0;
        b0 = ry0 + (ry1 - ry0) * t0;
        a1 = rx0 + (rx1 - rx0) * t1;
        b1 = ry0 + (ry1 - ry0) * t1;

        hull() {
            translate([0, 0, t0 * len])
                scale([a0, b0, 1])
                    cylinder(r = 1, h = 0.01);
            translate([0, 0, t1 * len])
                scale([a1, b1, 1])
                    cylinder(r = 1, h = 0.01);
        }
    }
}

// ============================================================
// Main Geometry
// ============================================================

difference() {
    union() {
        // Straight section at circle end
        scale([start_rx + wall_thickness, start_ry + wall_thickness, 1])
            cylinder(r = 1, h = start_straight);

        // Transition loft
        translate([0, 0, start_straight])
            lofted_solid(
                start_rx + wall_thickness,
                start_ry + wall_thickness,
                end_rx   + wall_thickness,
                end_ry   + wall_thickness,
                pipe_length,
                num_steps
            );

        // Straight section at ellipse end
        translate([0, 0, start_straight + pipe_length])
            scale([end_rx + wall_thickness, end_ry + wall_thickness, 1])
                cylinder(r = 1, h = end_straight);
    }

    // Inner bore (subtract to make it hollow)
    // Extended overlaps (1mm) at each junction to guarantee
    // a continuous airflow path with no blockage.
    union() {
        // Straight bore at circle end (extends 1mm into transition)
        translate([0, 0, -0.5])
            scale([start_rx, start_ry, 1])
                cylinder(r = 1, h = start_straight + 1.5);

        // Transition bore (extends 1mm into both straight sections)
        translate([0, 0, start_straight - 1])
            lofted_solid(
                start_rx,
                start_ry,
                end_rx,
                end_ry,
                pipe_length + 2,
                num_steps
            );

        // Straight bore at ellipse end (extends 1mm into transition)
        translate([0, 0, start_straight + pipe_length - 1])
            scale([end_rx, end_ry, 1])
                cylinder(r = 1, h = end_straight + 1.5);
    }
}
