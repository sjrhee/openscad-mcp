/*
 * Zippo Lighter Model
 * 
 * Classic windproof lighter with flip-top lid
 * Real-world dimensions: 56mm tall x 38mm wide x 13mm deep (closed)
 * 
 * 3D Printing Tips:
 * - Print with lid in open position for better results
 * - Use 0.2mm layer height for smooth surfaces
 * - Consider printing body, lid, and insert separately
 * - Insert can be printed with supports for overhangs
 */

// Global resolution settings
$fn = 60;                    // Circular resolution (60 for smooth curves)
num_steps = 50;              // Loft interpolation steps
wall_thickness = 1.5;        // Wall thickness (mm)

// Zippo dimensions (based on real measurements)
body_height = 56;            // Height of body (mm)
body_width = 38;             // Width of body (mm)
body_depth = 13;             // Depth of body (mm)
corner_radius = 2;           // Corner radius (mm)
lid_thickness = 1.5;         // Lid shell thickness (mm)
hinge_diameter = 3;          // Hinge pin diameter (mm)
hinge_segments = 5;          // Number of hinge segments
insert_height = 50;          // Height of insert (mm)
insert_width = 34;           // Width of insert (mm)
insert_depth = 11;           // Depth of insert (mm)
chimney_height = 10;         // Windscreen height (mm)
chimney_diameter = 12;       // Windscreen diameter (mm)
wheel_diameter = 14;         // Thumbwheel diameter (mm)
wheel_thickness = 3;         // Thumbwheel thickness (mm)
lid_angle = 110;             // Lid open angle (degrees)
wick_diameter = 4;           // Wick tube diameter (mm)

// Module for rounded rectangular box using hull
module rounded_box(width, depth, height, radius) {
    hull() {
        for (x = [radius, width - radius])
            for (y = [radius, depth - radius]) {
                translate([x, y, 0])
                    cylinder(r = radius, h = height);
            }
    }
}

// Module for the main body case
module lighter_body() {
    color("Silver")
    difference() {
        // Outer shell
        rounded_box(body_width, body_depth, body_height, corner_radius);
        
        // Inner cavity for insert
        translate([(body_width - insert_width) / 2, (body_depth - insert_depth) / 2, 2])
            rounded_box(insert_width, insert_depth, body_height, corner_radius / 2);
        
        // Hinge cutouts
        translate([-1, body_depth - 4, body_height - 6])
            cube([body_width + 2, 5, 7]);
    }
    
    // Body hinge segments
    color("Silver")
    for (i = [0, 2, 4]) {
        translate([8 + i * 7, body_depth - 2, body_height - 3])
            rotate([0, 90, 0])
                cylinder(h = 6, d = hinge_diameter);
    }
}

// Module for the insert (fuel chamber)
module lighter_insert() {
    translate([(body_width - insert_width) / 2, (body_depth - insert_depth) / 2, 2]) {
        color("DarkOrange")
        difference() {
            // Main insert body
            rounded_box(insert_width, insert_depth, insert_height, 1);
            
            // Fuel chamber
            translate([2, 2, 2])
                rounded_box(insert_width - 4, insert_depth - 4, insert_height - 10, 1);
            
            // Wick tube hole
            translate([insert_width / 2, insert_depth / 2, insert_height - 15])
                cylinder(h = 20, d = wick_diameter + 1);
        }
        
        // Wick tube
        color("Brass")
        translate([insert_width / 2, insert_depth / 2, insert_height - 12])
            difference() {
                cylinder(h = 12, d = wick_diameter);
                translate([0, 0, -1])
                    cylinder(h = 14, d = wick_diameter - 1);
            }
        
        // Flint wheel assembly
        color("DarkGray")
        translate([insert_width / 2, insert_depth / 2, insert_height - 5]) {
            // Wheel
            difference() {
                cylinder(h = wheel_thickness, d = wheel_diameter);
                // Knurling
                for (angle = [0:10:350]) {
                    rotate([0, 0, angle])
                        translate([wheel_diameter / 2, 0, -1])
                            cube([2, 1, wheel_thickness + 2], center = true);
                }
            }
            
            // Flint spring housing
            translate([0, -wheel_diameter / 2 - 2, -3])
                cube([6, 4, 6], center = true);
        }
        
        // Chimney/windscreen
        color("DarkGray")
        translate([insert_width / 2, insert_depth / 2, insert_height - chimney_height]) {
            difference() {
                cylinder(h = chimney_height, d = chimney_diameter);
                cylinder(h = chimney_height + 1, d = chimney_diameter - 2);
                
                // Vent holes
                for (angle = [0:45:315]) {
                    rotate([0, 0, angle])
                        translate([chimney_diameter / 2, 0, chimney_height / 2])
                            rotate([0, 90, 0])
                                cylinder(h = 4, d = 2, center = true);
                }
            }
        }
    }
}

// Module for the lid
module lighter_lid() {
    translate([0, body_depth - 1, body_height - 3])
    rotate([lid_angle, 0, 0])
    translate([0, -body_depth + 1, 3]) {
        color("Silver")
        difference() {
            // Outer lid shell
            translate([0, 0, -body_height])
                rounded_box(body_width, body_depth, body_height + 1, corner_radius);
            
            // Inner lid cavity
            translate([lid_thickness, lid_thickness, -body_height + lid_thickness])
                rounded_box(
                    body_width - 2 * lid_thickness, 
                    body_depth - 2 * lid_thickness, 
                    body_height + 2, 
                    corner_radius - lid_thickness
                );
            
            // Bottom opening
            translate([-1, -1, -lid_thickness - 1])
                cube([body_width + 2, body_depth + 2, lid_thickness + 2]);
        }
        
        // Lid hinge segments
        color("Silver")
        for (i = [1, 3]) {
            translate([8 + i * 7, body_depth - 2, -3])
                rotate([0, 90, 0])
                    cylinder(h = 6, d = hinge_diameter);
        }
        
        // Cam spring (simplified)
        color("DarkGray")
        translate([body_width / 2, body_depth - 3, -5])
            rotate([45, 0, 0])
                cube([15, 1, 1], center = true);
    }
}

// Module for engraving/logo
module engraving() {
    color("Black")
    translate([body_width / 2, -0.1, body_height / 2])
        rotate([90, 0, 0])
            linear_extrude(height = 0.2) {
                // Simplified Zippo flame logo
                difference() {
                    scale([1, 1.5, 1])
                        circle(d = 10);
                    translate([0, -2, 0])
                        scale([1, 1.5, 1])
                            circle(d = 8);
                }
                // Text (simplified)
                translate([0, -8, 0])
                    square([15, 1], center = true);
            }
}

// Hinge pin
module hinge_pin() {
    color("DarkGray")
    translate([7, body_depth - 2, body_height - 3])
        rotate([0, 90, 0])
            cylinder(h = body_width - 14, d = hinge_diameter - 0.5);
}

// Main assembly
lighter_body();
lighter_insert();
lighter_lid();
engraving();
hinge_pin();