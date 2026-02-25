// 90도 휘어진 원통형 파이프
// 전체 경로 길이: 200mm
// 외경: 30mm, 벽 두께: 3mm, 곡률 반경: 60mm

$fn = 60;

outer_d = 30;
wall_t = 3;
inner_d = outer_d - 2 * wall_t;
bend_r = 60;
total_length = 200;

arc_length = PI / 2 * bend_r;
straight = (total_length - arc_length) / 2;

difference() {
    pipe_path(outer_d / 2);
    pipe_path(inner_d / 2);
}

module pipe_path(r) {
    // 아래 직선 구간
    cylinder(r = r, h = straight);

    // 90도 곡선 구간
    bend_steps = 40;
    for (i = [0 : bend_steps - 1]) {
        a0 = i * 90 / bend_steps;
        a1 = (i + 1) * 90 / bend_steps;
        hull() {
            translate(curve_pt(a0)) sphere(r = r);
            translate(curve_pt(a1)) sphere(r = r);
        }
    }

    // 윗 직선 구간 (X 방향)
    translate([bend_r, 0, straight + bend_r])
    rotate([0, 90, 0])
    cylinder(r = r, h = straight);
}

function curve_pt(a) = [
    bend_r * (1 - cos(a)),
    0,
    straight + bend_r * sin(a)
];
