/*
 * Transition Pipe: 50mm Circle to 100mm Circle
 * =============================================
 * Start : Circular pipe, inner diameter 50mm
 * End   : Circular pipe, inner diameter 100mm
 * Ends  : 10mm straight (flat) sections at both ends
 * Total : 150mm
 * Wall  : 2mm
 *
 * Usage: Open in OpenSCAD -> Render (F6) -> Export as STL
 *
 * 3D Print Tips:
 *   - Print standing up (small end on bed) for best surface quality
 *   - Use supports if printing large-end-down
 *   - Recommended layer height: 0.2mm
 *   - Infill: not needed (hollow), 2-3 wall lines recommended
 */

// ============================================================
// Parameters (all in mm)
// ============================================================

wall_thickness = 2;          // Wall thickness (mm)

// Start cross-section (small circle)
start_inner_diameter = 55;   // 55mm inner diameter

// End cross-section (large circle)
end_inner_diameter = 100;    // 100mm inner diameter

// Straight extension lengths
start_straight = 10;         // Flat straight section at small end (mm)
end_straight   = 10;         // Flat straight section at large end (mm)

// Total pipe length
total_length = 150;          // 150mm total

// Transition loft length (derived)
loft_length = total_length - start_straight - end_straight;  // 130mm

// Resolution settings
// For final STL export, use num_steps=100, $fn=90
num_steps = 50;              // Loft interpolation steps
$fn = 60;                    // Circle facet count

// ============================================================
// Derived values
// ============================================================

start_r = start_inner_diameter / 2;   // 25mm
end_r   = end_inner_diameter / 2;     // 50mm

// ============================================================
// Modules
// ============================================================

/*
 * Creates a solid lofted shape by hulling consecutive
 * circular cross-section slices along the Z axis.
 *
 * Parameters:
 *   r0    - start radius
 *   r1    - end radius
 *   len   - total length along Z
 *   steps - number of interpolation slices
 */
module lofted_solid(r0, r1, len, steps) {
    for (i = [0 : steps - 1]) {
        t0 = i / steps;
        t1 = (i + 1) / steps;

        // Interpolated radius at each slice
        a0 = r0 + (r1 - r0) * t0;
        a1 = r0 + (r1 - r0) * t1;

        hull() {
            translate([0, 0, t0 * len])
                cylinder(r = a0, h = 0.01);
            translate([0, 0, t1 * len])
                cylinder(r = a1, h = 0.01);
        }
    }
}

// ============================================================
// Main Geometry
// ============================================================

difference() {
    // --- Outer shell ---
    union() {
        // Straight section at small end (50mm)
        cylinder(r = start_r + wall_thickness, h = start_straight);

        // Transition loft (outer)
        translate([0, 0, start_straight])
            lofted_solid(
                start_r + wall_thickness,
                end_r   + wall_thickness,
                loft_length,
                num_steps
            );

        // Straight section at large end (100mm)
        translate([0, 0, start_straight + loft_length])
            cylinder(r = end_r + wall_thickness, h = end_straight);
    }

    // --- Inner bore (subtract to make it hollow) ---
    // Overlaps by 1mm at each junction to guarantee continuous airflow path
    union() {
        // Bore at small end (extends 1mm into transition)
        translate([0, 0, -0.5])
            cylinder(r = start_r, h = start_straight + 1.5);

        // Transition bore (extends 1mm into both straight sections)
        translate([0, 0, start_straight - 1])
            lofted_solid(
                start_r,
                end_r,
                loft_length + 2,
                num_steps
            );

        // Bore at large end (extends 1mm into transition)
        translate([0, 0, start_straight + loft_length - 1])
            cylinder(r = end_r, h = end_straight + 1.5);
    }
}
