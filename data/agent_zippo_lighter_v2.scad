// Simple Zippo Lighter
// Classic American windproof lighter with flip-top lid
// Real dimensions: 56mm x 38mm x 13mm (height x width x depth)
// Shown in closed position (iconic state)

$fn = 60;
wall_thickness = 1.5;  // Thinner walls for more realistic look

// Correct Zippo dimensions
lighter_height = 56;
lighter_width = 38;
lighter_depth = 13;
corner_radius = 2.5;
lid_height = 22;  // About 40% of height
gap = 0.8;  // Visible gap between lid and body

// Main body (bottom part)
module lighter_body() {
    difference() {
        // Outer shell with rounded corners
        hull() {
            for (x = [corner_radius, lighter_width - corner_radius])
                for (y = [corner_radius, lighter_depth - corner_radius])
                    translate([x, y, 0])
                        cylinder(r = corner_radius, h = lighter_height - lid_height - gap);
        }
        
        // Hollow interior (less aggressive for strength)
        translate([wall_thickness*2, wall_thickness*2, wall_thickness*2])
            hull() {
                for (x = [corner_radius, lighter_width - corner_radius - 4*wall_thickness])
                    for (y = [corner_radius, lighter_depth - corner_radius - 4*wall_thickness])
                        translate([x, y, 0])
                            cylinder(r = corner_radius - wall_thickness, h = lighter_height);
            }
    }
}

// Lid (top part) - closed position with subtle bevel
module lighter_lid() {
    translate([0, 0, lighter_height - lid_height]) {
        difference() {
            // Outer shell with slight taper at top
            hull() {
                // Bottom of lid
                for (x = [corner_radius, lighter_width - corner_radius])
                    for (y = [corner_radius, lighter_depth - corner_radius])
                        translate([x, y, 0])
                            cylinder(r = corner_radius, h = lid_height - 1);
                // Top of lid (slightly smaller for bevel effect)
                for (x = [corner_radius + 0.5, lighter_width - corner_radius - 0.5])
                    for (y = [corner_radius + 0.5, lighter_depth - corner_radius - 0.5])
                        translate([x, y, lid_height - 1])
                            cylinder(r = corner_radius - 0.5, h = 1);
            }
            
            // Hollow interior
            translate([wall_thickness*2, wall_thickness*2, -1])
                hull() {
                    for (x = [corner_radius, lighter_width - corner_radius - 4*wall_thickness])
                        for (y = [corner_radius, lighter_depth - corner_radius - 4*wall_thickness])
                            translate([x, y, 0])
                                cylinder(r = corner_radius - wall_thickness, h = lid_height + 2);
                }
            
            // Thumb indent for opening
            translate([lighter_width/2, -1, lid_height * 0.3])
                rotate([-90, 0, 0])
                    cylinder(r = 12, h = 3);
        }
    }
}

// Integrated hinge detail (flush with back)
module hinge() {
    hinge_pos = lighter_height - lid_height - gap/2;
    
    // Hinge barrels integrated into back edge
    color("DarkGray") {
        // Left hinge barrel
        translate([lighter_width * 0.2, lighter_depth - 2, hinge_pos])
            difference() {
                rotate([0, 90, 0])
                    cylinder(r = 2, h = 6);
                translate([-1, -3, -3])
                    cube([8, 3, 6]);
            }
        
        // Right hinge barrel
        translate([lighter_width * 0.6, lighter_depth - 2, hinge_pos])
            difference() {
                rotate([0, 90, 0])
                    cylinder(r = 2, h = 6);
                translate([-1, -3, -3])
                    cube([8, 3, 6]);
            }
    }
}

// Assembly
color("Silver") {
    lighter_body();
    lighter_lid();
}
hinge();