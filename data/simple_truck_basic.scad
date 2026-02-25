// Simple truck model (cab + cargo bed)
// Units: mm

$fn = 32;

// Dimensions
truck_l = 130;
truck_w = 46;
chassis_h = 8;

cab_l = 36;
cab_w = 42;
cab_h = 24;
cab_x = 18;

bed_l = 62;
bed_w = 44;
bed_h = 14;
bed_x = 78;

wheel_r = 10;
wheel_w = 8;
wheel_y = truck_w / 2 + 1.5;

axle_1 = 22;   // front
axle_2 = 72;   // rear front
axle_3 = 104;  // rear rear (dual rear axle look)

module frame() {
    color([0.2, 0.2, 0.22])
    translate([truck_l/2, 0, wheel_r + chassis_h/2 - 1])
    cube([truck_l - 6, truck_w - 10, chassis_h], center=true);
}

module cab() {
    color([0.9, 0.2, 0.18])
    hull() {
        translate([cab_x, 0, wheel_r + 10]) cube([20, cab_w, 18], center=true);
        translate([cab_x + cab_l - 8, 0, wheel_r + 13]) cube([14, cab_w - 2, 22], center=true);
    }
}

module windshield() {
    color([0.7, 0.9, 1.0, 0.7])
    translate([cab_x + 12, 0, wheel_r + 16])
    rotate([0, 18, 0])
    cube([2, cab_w - 8, 12], center=true);
}

module cargo_bed() {
    color([0.12, 0.35, 0.8])
    difference() {
        translate([bed_x, 0, wheel_r + bed_h/2 + 2])
        cube([bed_l, bed_w, bed_h], center=true);
        translate([bed_x, 0, wheel_r + bed_h/2 + 4])
        cube([bed_l - 6, bed_w - 6, bed_h], center=true);
    }
}

module side_rails() {
    color([0.15, 0.15, 0.16])
    for (y = [-bed_w/2 + 2, bed_w/2 - 2]) {
        translate([bed_x, y, wheel_r + bed_h + 4])
        cube([bed_l - 4, 2, 2], center=true);
    }
}

module wheel(x, y_sign) {
    color([0.08, 0.08, 0.08])
    translate([x, y_sign * wheel_y, wheel_r])
    rotate([90, 0, 0])
    cylinder(r=wheel_r, h=wheel_w, center=true);
}

module axle_bar(x) {
    color([0.3, 0.3, 0.3])
    translate([x, 0, wheel_r])
    rotate([90, 0, 0])
    cylinder(r=1.6, h=truck_w + 8, center=true);
}

module bumpers_and_lights() {
    color([0.2, 0.2, 0.2])
    translate([3, 0, wheel_r + 4]) cube([6, truck_w - 8, 5], center=true);
    color([0.2, 0.2, 0.2])
    translate([truck_l - 3, 0, wheel_r + 4]) cube([6, truck_w - 8, 5], center=true);

    color([1.0, 0.95, 0.7])
    for (y = [-truck_w/2 + 8, truck_w/2 - 8]) {
        translate([1, y, wheel_r + 10]) sphere(r=2.2);
    }

    color([0.9, 0.1, 0.1])
    for (y = [-truck_w/2 + 8, truck_w/2 - 8]) {
        translate([truck_l - 1, y, wheel_r + 8]) sphere(r=2.0);
    }
}

frame();
cab();
windshield();
cargo_bed();
side_rails();
bumpers_and_lights();

wheel(axle_1, 1);
wheel(axle_1, -1);
wheel(axle_2, 1);
wheel(axle_2, -1);
wheel(axle_3, 1);
wheel(axle_3, -1);

axle_bar(axle_1);
axle_bar(axle_2);
axle_bar(axle_3);
