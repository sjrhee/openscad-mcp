/*
Simple laptop model (open position)
Specifications (mm):
- Overall footprint (base): 320 x 220
- Base thickness: 12
- Screen panel size: 320 x 220 x 6
- Open angle: 110 degrees (between keyboard deck and screen)
- Includes simple keyboard area, trackpad, hinge bar, and display bezel

3D printing tips:
- Print base and screen separately if you want stronger hinge detail.
- Increase wall_thickness for a chunkier toy-like model.
- Use lower $fn (36-48) for faster preview; keep 60 for nicer rounded hinge.
*/

// Parameters
$fn = 60;           // Circular resolution
num_steps = 50;     // Loft interpolation steps (reserved for project convention)
wall_thickness = 2; // Wall thickness (mm)

// Overall dimensions (mm)
laptop_width = 320;       // X direction
laptop_depth = 220;       // Y direction
base_thickness = 12;      // Z thickness of bottom body
screen_thickness = 6;     // Z thickness of screen body
open_angle_deg = 90;      // Angle between base top plane and screen panel

// Detail dimensions (mm)
corner_radius = 8;        // Rounded corner radius for base/screen
screen_bezel = 20;        // Front bezel width (mm)
screen_inset_depth = 1.2; // Screen glass recess depth
keyboard_margin_x = 18;
keyboard_margin_y_front = 18;
keyboard_margin_y_back = 20;
keyboard_recess = 1.2;
trackpad_w = 110;
trackpad_h = 75;
trackpad_recess = 0.8;
trackpad_offset_from_front = 24;
hinge_radius = 5;
hinge_length = laptop_width - 40;
hinge_gap = 1.2;          // Visual gap between base and screen near hinge

// Derived values
screen_tilt_back_deg = open_angle_deg - 90; // 90deg = vertical screen, >90 tilts backward
screen_frame_w = laptop_width;
screen_frame_h = laptop_depth;
screen_body_x = laptop_width;
screen_body_y = screen_thickness;
screen_body_z = laptop_depth;

base_center_z = base_thickness / 2;
base_top_z = base_thickness;

screen_pivot_x = laptop_width / 2;
hinge_center_y = laptop_depth - hinge_radius - 1.5;
hinge_center_z = base_thickness + hinge_radius;
screen_pivot_y = hinge_center_y + hinge_gap;
screen_pivot_z = hinge_center_z;

screen_center_local = [screen_body_x / 2, screen_body_y / 2, screen_body_z / 2];

keyboard_area_w = laptop_width - 2 * keyboard_margin_x;
keyboard_area_d = laptop_depth - keyboard_margin_y_front - keyboard_margin_y_back;

trackpad_x = laptop_width / 2 - trackpad_w / 2;
trackpad_y = trackpad_offset_from_front;

display_open_w = screen_frame_w - 2 * screen_bezel;
display_open_h = screen_frame_h - 2 * screen_bezel;

// Modules
module rounded_rect_plate(size = [10, 10, 2], r = 2) {
    sx = size[0];
    sy = size[1];
    sz = size[2];

    hull() {
        for (x = [-sx / 2 + r, sx / 2 - r])
            for (y = [-sy / 2 + r, sy / 2 - r])
                translate([x, y, 0])
                    cylinder(r = r, h = sz);
    }
}

module laptop_base() {
    color([0.72, 0.74, 0.78])
    difference() {
        translate([laptop_width / 2, laptop_depth / 2, 0])
            rounded_rect_plate([laptop_width, laptop_depth, base_thickness], corner_radius);

        // Keyboard deck recess
        translate([keyboard_margin_x, keyboard_margin_y_front, base_thickness - keyboard_recess])
            cube([keyboard_area_w, keyboard_area_d, keyboard_recess + 0.2]);

        // Trackpad recess
        translate([trackpad_x, trackpad_y, base_thickness - trackpad_recess])
            cube([trackpad_w, trackpad_h, trackpad_recess + 0.2]);
    }
}

module keyboard_grid() {
    key_cols = 14;
    key_rows = 5;
    key_gap = 3;
    key_h = 0.8;
    area_x = keyboard_margin_x + 6;
    area_y = keyboard_margin_y_front + 80;
    area_w = keyboard_area_w - 12;
    area_d = keyboard_area_d - 95;
    key_w = (area_w - (key_cols - 1) * key_gap) / key_cols;
    key_d = (area_d - (key_rows - 1) * key_gap) / key_rows;

    color([0.16, 0.17, 0.19])
    for (r = [0 : key_rows - 1]) {
        for (c = [0 : key_cols - 1]) {
            translate([
                area_x + c * (key_w + key_gap),
                area_y + r * (key_d + key_gap),
                base_thickness - keyboard_recess + 0.1
            ])
                cube([key_w, key_d, key_h]);
        }
    }
}

module trackpad_outline() {
    color([0.55, 0.57, 0.61])
    translate([trackpad_x, trackpad_y, base_thickness - trackpad_recess + 0.05])
        difference() {
            cube([trackpad_w, trackpad_h, 0.35]);
            translate([1.2, 1.2, -0.05])
                cube([trackpad_w - 2.4, trackpad_h - 2.4, 0.5]);
        }
}

module hinge_bar() {
    color([0.30, 0.31, 0.34])
    translate([laptop_width / 2, hinge_center_y, hinge_center_z])
        rotate([0, 90, 0])
            cylinder(r = hinge_radius, h = hinge_length, center = true);
}

module screen_panel() {
    color([0.68, 0.70, 0.74])
    difference() {
        // Screen body (local coordinates: X 0..width, Y -thickness..0, Z 0..height)
        translate([screen_frame_w / 2, 0, screen_frame_h / 2])
            rotate([90, 0, 0])
                rounded_rect_plate([screen_frame_w, screen_frame_h, screen_thickness], corner_radius - 1);

        // Front display recess cut (extend slightly through front face)
        translate([screen_bezel, -screen_inset_depth - 0.1, screen_bezel])
            cube([display_open_w, screen_inset_depth + 0.2, display_open_h]);
    }

    // Front bezel lip in same color as body for a more realistic frame appearance
    color([0.68, 0.70, 0.74])
    translate([0, -0.35, 0])
        difference() {
            cube([screen_frame_w, 0.35, screen_frame_h]);
            translate([screen_bezel, -0.05, screen_bezel])
                cube([display_open_w, 0.45, display_open_h]);
        }

    // Display cavity background (dark gray so bezel edge remains readable)
    color([0.08, 0.09, 0.10])
    translate([screen_bezel, -0.95, screen_bezel])
        cube([display_open_w, 0.85, display_open_h]);

    // Main visible screen surface (black, slightly proud for reliable preview visibility)
    color([0.01, 0.01, 0.01])
    translate([screen_bezel + 2, -0.10, screen_bezel + 2])
        cube([display_open_w - 4, 0.10, display_open_h - 4]);

    // Small soft reflection strip so "black screen" still reads in flat lighting
    color([0.18, 0.18, 0.19])
    translate([screen_bezel + 10, -0.09, screen_frame_h - screen_bezel - 16])
        cube([display_open_w * 0.45, 0.03, 4]);

    // Simple webcam bump
    color([0.08, 0.09, 0.11])
    translate([screen_frame_w / 2, -0.25, screen_frame_h - screen_bezel / 2])
        rotate([90, 0, 0])
            cylinder(r = 1.2, h = 0.8);
}

module laptop_screen_assembly() {
    // Place local screen so bottom-back edge sits near hinge axis, then rotate open.
    translate([screen_pivot_x, screen_pivot_y - hinge_gap, screen_pivot_z])
        rotate([-screen_tilt_back_deg, 0, 0])
            translate([-screen_frame_w / 2, 0, 0])
                screen_panel();
}

// Main Geometry
laptop_base();
keyboard_grid();
trackpad_outline();
hinge_bar();
laptop_screen_assembly();
