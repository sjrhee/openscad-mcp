// Simple compact car model for MCP test
// Units: mm

$fn = 36;

// Overall scale
body_l = 90;
body_w = 40;
body_h = 14;

roof_l = 42;
roof_w = 34;
roof_h = 12;
roof_x = 28;

wheel_r = 9;
wheel_w = 7;
front_axle_x = 20;
rear_axle_x = 68;
wheel_y = body_w / 2 + 1;

module chassis() {
    color([0.15, 0.45, 0.85])
    translate([body_l/2, 0, wheel_r + body_h/2])
    cube([body_l, body_w, body_h], center = true);
}

module roof() {
    color([0.12, 0.38, 0.72])
    hull() {
        translate([roof_x + 6, 0, wheel_r + body_h + roof_h/2 - 2])
        cube([16, roof_w, roof_h], center = true);
        translate([roof_x + roof_l - 6, 0, wheel_r + body_h + roof_h/2 - 2])
        cube([16, roof_w, roof_h - 2], center = true);
    }
}

module windshield_and_windows() {
    color([0.65, 0.85, 0.95, 0.7])
    translate([roof_x + roof_l/2, 0, wheel_r + body_h + roof_h/2 + 1])
    cube([roof_l - 8, roof_w - 6, roof_h - 4], center = true);
}

module wheel(x, y_sign) {
    color([0.1, 0.1, 0.1])
    translate([x, y_sign * wheel_y, wheel_r])
    rotate([90, 0, 0])
    cylinder(r = wheel_r, h = wheel_w, center = true);
}

module axle_bar(x) {
    color([0.25, 0.25, 0.25])
    translate([x, 0, wheel_r])
    rotate([90, 0, 0])
    cylinder(r = 1.5, h = body_w + 6, center = true);
}

module lights() {
    color([1.0, 0.95, 0.7])
    for (y = [-body_w/2 + 6, body_w/2 - 6]) {
        translate([1, y, wheel_r + body_h/2 + 1])
        sphere(r = 2);
    }

    color([0.9, 0.1, 0.1])
    for (y = [-body_w/2 + 6, body_w/2 - 6]) {
        translate([body_l - 1, y, wheel_r + body_h/2 + 1])
        sphere(r = 1.8);
    }
}

module bumpers() {
    color([0.2, 0.2, 0.2])
    translate([2, 0, wheel_r + 3]) cube([4, body_w - 4, 4], center = true);
    color([0.2, 0.2, 0.2])
    translate([body_l - 2, 0, wheel_r + 3]) cube([4, body_w - 4, 4], center = true);
}

chassis();
roof();
windshield_and_windows();

wheel(front_axle_x, 1);
wheel(front_axle_x, -1);
wheel(rear_axle_x, 1);
wheel(rear_axle_x, -1);
axle_bar(front_axle_x);
axle_bar(rear_axle_x);

lights();
bumpers();
