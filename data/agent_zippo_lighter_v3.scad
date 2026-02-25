// Simple Zippo Lighter
// Classic windproof lighter in closed position
// Real dimensions: 56mm tall x 38mm wide x 13mm deep
// Iconic rectangular form with visible seam line

$fn = 60;

// Actual Zippo dimensions (mm)
height = 56;
width = 38;
depth = 13;
corner_radius = 2.5;
lid_height = 24; // Lid is about 43% of height
seam_position = height - lid_height; // 32mm from bottom
hinge_width = 6;
hinge_depth = 3;
hinge_pin_diameter = 2;

// Visual details
seam_gap = 0.8;
logo_diameter = 10;
logo_depth = 0.3;

module rounded_box(size, radius, top_radius = 0) {
    // Main body with rounded corners
    // top_radius: use different radius for top edges (0 = same as radius)
    hull() {
        tr = top_radius > 0 ? top_radius : radius;
        for (x = [radius, size[0] - radius])
            for (y = [radius, size[1] - radius]) {
                // Bottom edge
                translate([x, y, radius])
                    sphere(r = radius);
                // Top edge
                translate([x, y, size[2] - tr])
                    sphere(r = tr);
            }
    }
}

// Complete lighter body (closed)
module zippo_closed() {
    // Main body
    color([0.8, 0.8, 0.85]) // Chrome/silver
    difference() {
        // Outer shell with slightly rounded top/bottom edges
        rounded_box([width, depth, height], corner_radius, corner_radius * 1.2);
        
        // Seam line gap
        translate([-1, -1, seam_position - seam_gap/2])
            cube([width + 2, depth + 2, seam_gap]);
        
        // Hinge cutout (more prominent)
        translate([width/2 - hinge_width/2, depth - hinge_depth - 0.5, seam_position - 8])
            cube([hinge_width, hinge_depth + 1, 16]);
            
        // Front logo indent with text simulation
        translate([width/2, -0.1, height * 0.35]) {
            rotate([90, 0, 0])
                cylinder(d = logo_diameter, h = logo_depth);
            // Simulated text lines
            for (i = [-1:1])
                translate([0, 0, i * 2])
                    rotate([90, 0, 0])
                    linear_extrude(height = logo_depth + 0.1)
                        square([logo_diameter * 0.7, 0.5], center = true);
        }
            
        // Back logo indent
        translate([width/2, depth + 0.1, height * 0.65])
            rotate([90, 0, 0])
            cylinder(d = logo_diameter * 0.8, h = logo_depth);
    }
    
    // Visible hinge barrel with pin
    color([0.6, 0.6, 0.65]) { // Darker metal
        translate([width/2, depth - hinge_depth/2, seam_position])
            rotate([0, 90, 0])
            cylinder(d = 3, h = hinge_width - 1, center = true);
        
        // Hinge pin ends
        for (x = [width/2 - hinge_width/2 + 0.5, width/2 + hinge_width/2 - 0.5])
            translate([x, depth - hinge_depth/2, seam_position])
                sphere(d = hinge_pin_diameter);
    }
        
    // Subtle seam line enhancement
    color([0.7, 0.7, 0.75])
    difference() {
        translate([0, 0, seam_position - 0.1])
            cube([width, depth, 0.2]);
        translate([1, 1, seam_position - 0.2])
            cube([width - 2, depth - 2, 0.4]);
    }
}

// Rotate for better viewing angle
rotate([0, 0, 30])
    rotate([20, 0, 0])
        zippo_closed();