/*
 * Simple Game Controller (toy-style)
 * ==================================
 * Symmetric game controller concept with dual grips, D-pad, 4 action buttons,
 * dual analog sticks, center buttons, and simple shoulder bars.
 *
 * Key specs (mm):
 *   - Overall width: 160
 *   - Overall height: 105
 *   - Overall thickness: 36
 *   - Body shell uses hull()-based profile for performance
 *
 * 3D Print Tips:
 *   - Print flat on the back side for easiest support-free print.
 *   - Recommended layer height: 0.2mm
 *   - Increase controller_thickness or grip_radius for a chunkier handheld mockup.
 */

// ============================================================
// Parameters (all in mm)
// ============================================================

// Resolution settings
// 웹 미리보기: num_steps=30, $fn=36
// PNG 미리보기: num_steps=50, $fn=60
// STL 최종 출력: num_steps=100, $fn=90
$fn = 60;           // 원형 해상도 (미리보기: 36~60, 최종 출력: 90)
num_steps = 50;     // 로프트 보간 단계 (미리보기: 30~50, 최종 출력: 100)
wall_thickness = 2; // 벽 두께 (mm) — 장식 디테일 두께 기준

controller_width = 160;      // Overall width (mm)
controller_height = 105;     // Overall height (mm)
controller_thickness = 36;   // Overall thickness (mm)

center_body_width = 88;      // Center bridge width (mm)
center_body_height = 46;     // Center bridge height (mm)
grip_radius = 27;            // Grip outer radius (mm)
grip_spread_x = 58;          // Grip center X offset from middle (mm)
grip_drop_y = 30;            // Grip center Y offset downward from middle (mm)
grip_tip_drop_y = 44;        // Lower handle tip Y offset downward from middle (mm)
grip_tip_inset_x = 8;        // Lower handle tip X inset from grip center (mm)
grip_tip_radius = 18;        // Lower handle tip radius (mm)

top_shoulder_width = 54;     // Shoulder bar length (mm)
top_shoulder_depth = 9;      // Shoulder bar depth (mm)
top_shoulder_height = 6;     // Shoulder bar height (mm)

face_panel_inset = 1.4;      // Top panel recess depth (mm)
face_panel_margin = 7;       // Top panel margin from outer body (mm)

stick_radius = 10;           // Analog stick cap radius (mm)
stick_height = 5;            // Analog stick cap height (mm)
stick_base_radius = 16;      // Analog stick base ring radius (mm)
stick_base_height = 2;       // Analog stick base ring height (mm)
stick_offset_x = 29;         // Stick center X offset from middle (mm)
stick_left_y = -10;          // Left stick center Y offset (mm)
stick_right_y = -10;         // Right stick center Y offset (mm)

dpad_center_x = -49;         // D-pad center X (mm)
dpad_center_y = 13;          // D-pad center Y (mm)
dpad_arm_len = 24;           // D-pad full arm length (mm)
dpad_arm_w = 8;              // D-pad arm width (mm)
dpad_height = 3.2;           // D-pad height (mm)
dpad_center_r = 6;           // D-pad center radius (mm)

button_cluster_x = 49;       // Action button cluster center X (mm)
button_cluster_y = 13;       // Action button cluster center Y (mm)
button_spacing = 11;         // Action button offset from cluster center (mm)
button_radius = 4.8;         // Action button radius (mm)
button_height = 2.8;         // Action button height (mm)

center_button_w = 10;        // Menu button width (mm)
center_button_h = 5.5;       // Menu button height (mm)
center_button_z = 2;         // Menu button height in Z (mm)
center_button_gap = 9;       // Gap from center line to menu buttons (mm)

seam_band_height = 2;        // Decorative seam band height (mm)
bottom_foot_height = 1.2;    // Small feet height (mm)

// ============================================================
// Derived values
// ============================================================

body_half_t = controller_thickness / 2;
body_z0 = -body_half_t;
body_z1 = body_half_t;

outer_profile_offset = 0;
panel_z = body_z1 - face_panel_inset;

stick_left_pos = [-stick_offset_x, stick_left_y];
stick_right_pos = [stick_offset_x, stick_right_y];

button_positions = [
    [button_cluster_x, button_cluster_y + button_spacing],
    [button_cluster_x + button_spacing, button_cluster_y],
    [button_cluster_x, button_cluster_y - button_spacing],
    [button_cluster_x - button_spacing, button_cluster_y]
];

// ============================================================
// Modules
// ============================================================

module controller_profile_2d(shrink = 0) {
    grip_r = max(1, grip_radius - shrink);
    grip_tip_r = max(1, grip_tip_radius - shrink);
    bridge_w = max(2, center_body_width - 2 * shrink);
    bridge_h = max(2, center_body_height - 2 * shrink);
    shoulder_r = max(3, 10 - shrink * 0.4);
    bridge_corner_r = max(2, 6 - shrink * 0.3);
    left_grip_x = -grip_spread_x;
    right_grip_x = grip_spread_x;
    grip_upper_y = -grip_drop_y;
    grip_tip_y = -grip_tip_drop_y;

    union() {
        // Center body
        hull() {
            for (x = [-bridge_w / 2 + 14, bridge_w / 2 - 14])
                for (y = [-bridge_h / 2 + 10, bridge_h / 2 - 10])
                    translate([x, y]) circle(r = bridge_corner_r);
        }

        // Left upper wing into grip
        hull() {
            translate([-bridge_w / 2 + 6, bridge_h / 2 - 8]) circle(r = 8);
            translate([-bridge_w / 2 + 8, -bridge_h / 2 + 8]) circle(r = 10);
            translate([left_grip_x + 2, grip_upper_y + 8]) circle(r = grip_r - 4);
            translate([-controller_width / 2 + 20 + shrink, controller_height / 2 - 17 - shrink]) circle(r = shoulder_r);
        }

        // Right upper wing into grip
        hull() {
            translate([bridge_w / 2 - 6, bridge_h / 2 - 8]) circle(r = 8);
            translate([bridge_w / 2 - 8, -bridge_h / 2 + 8]) circle(r = 10);
            translate([right_grip_x - 2, grip_upper_y + 8]) circle(r = grip_r - 4);
            translate([controller_width / 2 - 20 - shrink, controller_height / 2 - 17 - shrink]) circle(r = shoulder_r);
        }

        // Left grip handle lobe (clear handle silhouette)
        hull() {
            translate([left_grip_x, grip_upper_y]) circle(r = grip_r);
            translate([left_grip_x + grip_tip_inset_x, grip_tip_y]) circle(r = grip_tip_r);
            translate([left_grip_x - 7, grip_upper_y - 8]) circle(r = grip_r - 6);
        }

        // Right grip handle lobe (clear handle silhouette)
        hull() {
            translate([right_grip_x, grip_upper_y]) circle(r = grip_r);
            translate([right_grip_x - grip_tip_inset_x, grip_tip_y]) circle(r = grip_tip_r);
            translate([right_grip_x + 7, grip_upper_y - 8]) circle(r = grip_r - 6);
        }
    }
}

module controller_body() {
    color([0.72, 0.74, 0.78])
    difference() {
        linear_extrude(height = controller_thickness, center = true)
            controller_profile_2d(outer_profile_offset);

        // Top face panel recess
        translate([0, 0, panel_z])
            linear_extrude(height = face_panel_inset + 0.2)
                offset(delta = -face_panel_margin)
                    controller_profile_2d(0);
    }
}

module face_seam_band() {
    color([0.62, 0.64, 0.68])
    translate([0, 0, body_z1 - seam_band_height])
        linear_extrude(height = seam_band_height)
            difference() {
                offset(delta = -3) controller_profile_2d(0);
                offset(delta = -5.2) controller_profile_2d(0);
            }
}

module analog_stick(pos = [0, 0]) {
    color([0.16, 0.17, 0.19])
    translate([pos[0], pos[1], body_z1 - face_panel_inset + 0.1]) {
        cylinder(r = stick_base_radius, h = stick_base_height);
        translate([0, 0, stick_base_height])
            cylinder(r1 = stick_radius + 1.2, r2 = stick_radius, h = stick_height);
    }
}

module dpad(pos = [0, 0]) {
    color([0.14, 0.15, 0.17])
    translate([pos[0], pos[1], body_z1 - face_panel_inset + 0.1]) {
        union() {
            translate([-dpad_arm_len / 2, -dpad_arm_w / 2, 0])
                cube([dpad_arm_len, dpad_arm_w, dpad_height]);
            translate([-dpad_arm_w / 2, -dpad_arm_len / 2, 0])
                cube([dpad_arm_w, dpad_arm_len, dpad_height]);
            cylinder(r = dpad_center_r, h = dpad_height);
        }
    }
}

module action_buttons() {
    button_colors = [
        [0.85, 0.25, 0.23],
        [0.20, 0.52, 0.92],
        [0.24, 0.73, 0.33],
        [0.95, 0.80, 0.22]
    ];

    for (i = [0 : 3]) {
        color(button_colors[i])
        translate([button_positions[i][0], button_positions[i][1], body_z1 - face_panel_inset + 0.1])
            cylinder(r = button_radius, h = button_height);
    }
}

module center_buttons() {
    color([0.18, 0.19, 0.21])
    for (x = [-center_button_gap, center_button_gap]) {
        translate([x, 20, body_z1 - face_panel_inset + 0.1])
            linear_extrude(height = center_button_z)
                offset(r = 1.3)
                    square([center_button_w - 2.6, center_button_h - 2.6], center = true);
    }

    color([0.22, 0.24, 0.27])
    translate([0, 8, body_z1 - face_panel_inset + 0.1])
        cylinder(r = 5, h = 1.6);
}

module shoulder_bars() {
    color([0.28, 0.29, 0.32])
    for (sx = [-1, 1]) {
        translate([
            sx * (controller_width / 2 - top_shoulder_width / 2 - 10),
            controller_height / 2 - top_shoulder_depth - 4,
            body_z1 - top_shoulder_height + 1
        ])
            linear_extrude(height = top_shoulder_height)
                offset(r = 2)
                    square([top_shoulder_width - 4, top_shoulder_depth - 4], center = false);
    }
}

module bottom_feet() {
    color([0.10, 0.10, 0.11])
    for (sx = [-1, 1]) {
        translate([sx * 36, -36, body_z0 - bottom_foot_height])
            cylinder(r = 8, h = bottom_foot_height);
    }
}

// ============================================================
// Main Geometry
// ============================================================

controller_body();
face_seam_band();
shoulder_bars();
dpad([dpad_center_x, dpad_center_y]);
action_buttons();
analog_stick(stick_left_pos);
analog_stick(stick_right_pos);
center_buttons();
bottom_feet();
