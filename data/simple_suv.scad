// Simple SUV / Jeep style car
// Overall length: ~100mm

$fn = 40;

// Body dimensions
body_l = 100;   // length (X)
body_w = 45;    // width (Y)
body_h = 20;    // lower body height (Z)

// Cabin
cab_l = 55;     // cabin length
cab_w = 43;     // cabin width
cab_h = 22;     // cabin height
cab_offset = 20; // from front

// Wheel
wheel_r = 11;
wheel_w = 8;
axle_front = 18;
axle_rear = body_l - 18;
axle_y = body_w / 2 + 2;

// Colors
module colored_body() {
    color([0.2, 0.4, 0.2]) children();
}
module colored_cabin() {
    color([0.15, 0.35, 0.18]) children();
}
module colored_wheel() {
    color([0.15, 0.15, 0.15]) children();
}
module colored_bumper() {
    color([0.3, 0.3, 0.3]) children();
}

// Lower body - rounded box
module body() {
    colored_body()
    translate([body_l/2, 0, body_h/2 + wheel_r])
    minkowski() {
        cube([body_l - 6, body_w - 6, body_h - 4], center=true);
        sphere(r=2);
    }
}

// Cabin / roof
module cabin() {
    colored_cabin()
    translate([cab_offset + cab_l/2, 0, body_h + cab_h/2 + wheel_r - 2])
    minkowski() {
        cube([cab_l - 8, cab_w - 8, cab_h - 6], center=true);
        sphere(r=3);
    }
}

// Wheel
module wheel(x, y_sign) {
    colored_wheel()
    translate([x, y_sign * axle_y, wheel_r])
    rotate([90, 0, 0])
    cylinder(r=wheel_r, h=wheel_w, center=true);
}

// Front bumper
module bumper_front() {
    colored_bumper()
    translate([1, 0, wheel_r + 4])
    cube([4, body_w - 4, 8], center=true);
}

// Rear bumper
module bumper_rear() {
    colored_bumper()
    translate([body_l - 1, 0, wheel_r + 4])
    cube([4, body_w - 4, 8], center=true);
}

// Headlights
module headlights() {
    color([1, 1, 0.7])
    for (y = [-body_w/2 + 8, body_w/2 - 8]) {
        translate([-0.5, y, wheel_r + body_h/2 + 2])
        sphere(r=3);
    }
}

// Taillights
module taillights() {
    color([0.8, 0, 0])
    for (y = [-body_w/2 + 8, body_w/2 - 8]) {
        translate([body_l + 0.5, y, wheel_r + body_h/2 + 2])
        sphere(r=2.5);
    }
}

// Assemble
body();
cabin();

// 4 wheels
wheel(axle_front, 1);
wheel(axle_front, -1);
wheel(axle_rear, 1);
wheel(axle_rear, -1);

bumper_front();
bumper_rear();
headlights();
taillights();
