// Simple Zippo Lighter
// Dimensions based on classic Zippo: ~56mm tall, 36mm wide, 12mm deep

wall_thickness = 1.2;
num_steps = 50;
$fn = 60;

body_w = 36;
body_d = 12;
body_h = 56;
corner_r = 2.5;

// Lid/body split: lid is top ~60%
split_h = 22;          // height from bottom where lid starts
lid_h = body_h - split_h;
lid_gap = 0.4;         // visible seam between lid and body

// Hinge
hinge_r = 2.5;
hinge_len = body_w * 0.7;

// --- Modules ---

module rounded_box(w, d, h, r) {
    // Rounded rectangle extruded vertically
    hull() {
        for (x = [r, w - r])
            for (y = [r, d - r])
                translate([x, y, 0])
                    cylinder(r = r, h = h);
    }
}

module shell(w, d, h, r, t) {
    difference() {
        rounded_box(w, d, h, r);
        translate([t, t, t])
            rounded_box(w - 2*t, d - 2*t, h, r);
    }
}

// --- Bottom case ---
module bottom_case() {
    shell(body_w, body_d, split_h, corner_r, wall_thickness);
    // Solid bottom
    translate([0, 0, 0])
        rounded_box(body_w, body_d, wall_thickness, corner_r);
}

// --- Lid ---
module lid() {
    translate([0, 0, split_h + lid_gap]) {
        // Lid shell (open at bottom)
        shell(body_w, body_d, lid_h, corner_r, wall_thickness);
        // Lid top cap
        translate([0, 0, lid_h - wall_thickness])
            rounded_box(body_w, body_d, wall_thickness, corner_r);
    }
}

// --- Hinge ---
module hinge() {
    hinge_x = (body_w - hinge_len) / 2;
    translate([hinge_x, body_d - 1, split_h + lid_gap])
        rotate([0, 90, 0])
            cylinder(r = hinge_r, h = hinge_len);
    // Hinge pin knobs on each side
    for (dx = [-1.5, hinge_len + 1.5])
        translate([hinge_x + dx, body_d - 1, split_h + lid_gap])
            rotate([0, 90, 0])
                cylinder(r = hinge_r * 0.6, h = 1.5);
}

// --- Insert top details (visible when closed) ---
module insert_top() {
    // Chimney opening outline at top of lid
    chimney_w = body_w * 0.55;
    chimney_d = body_d * 0.5;
    chimney_h = 2;
    translate([(body_w - chimney_w)/2, (body_d - chimney_d)/2, body_h - wall_thickness - 0.01]) {
        difference() {
            rounded_box(chimney_w, chimney_d, chimney_h, 1.5);
            translate([wall_thickness, wall_thickness, -0.1])
                rounded_box(chimney_w - 2*wall_thickness, chimney_d - 2*wall_thickness, chimney_h + 0.2, 1);
        }
    }
}

// --- Thumb wheel (barely visible at top seam) ---
module thumb_wheel() {
    wheel_r = 3;
    wheel_w = body_w * 0.25;
    translate([body_w/2, body_d * 0.35, body_h - wall_thickness + 0.5])
        rotate([0, 90, 0])
            cylinder(r = wheel_r, h = wheel_w, center = true);
}

// --- Assembly ---
color("#C0C0C0") {
    bottom_case();
    lid();
    hinge();
}

color("#A0A0A0")
    insert_top();

color("#555555")
    thumb_wheel();
