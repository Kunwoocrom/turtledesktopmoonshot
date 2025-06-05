import turtle
import random
import math
import time

# --- 시뮬레이션 설정 ---
NUM_PARTICLES = 20  # 가상 참가자(입자) 수 (20개로 증가)
NUM_FIXED_OBJECTS = 6  # 고정된 개체(자본 축적기) 수 (6개로 증가)
SIMULATION_DURATION_SECONDS = 300  # 시뮬레이션 실행 시간 (초), 가상 40년 -> 70년으로 변경

# 재능 (입자의 속도) 분포 설정
# 평균적인 재능을 가진 사람이 가장 많고, 재능이 매우 뛰어나거나 낮은 사람은 소수
TALENT_MEAN = 5.0  # 재능의 평균 (3.0 -> 5.0으로 변경)
TALENT_STD_DEV = 2.0  # 재능의 표준 편차 (1.0 -> 2.0으로 변경)

# 운의 벽 두께 분포 설정
# 운의 벽이 두꺼울수록 통과하기 어려움
WALL_THICKNESS_MEAN = 10.0  # 운의 벽 두께 평균
WALL_THICKNESS_STD_DEV = 3.0  # 운의 벽 두께 표준 편차
# 고정된 개체 반지름(20) + 0.3cm(6픽셀) = 26픽셀 (0.1cm 감소)
LUCK_WALL_DISTANCE_THRESHOLD = 26  # 고정된 개체에 얼마나 가까이 접근해야 운의 벽이 생기는가 (픽셀)

# 고정된 개체의 시각적 접근 반경 (고정 개체 반지름 + 0.3cm)
FIXED_OBJECT_APPROACH_RADIUS = 26

# 운의 벽 통과 확률 조절 (값이 낮아질수록 통과하기 어려워짐)
# 이 값은 통과 확률의 최소값에 영향을 줍니다. (예: 0.5면 최소 50%)
LUCK_PASS_FACTOR = 0.5  # 벽 통과 확률을 0.5 (1/2)로 설정

# --- 화면 설정 ---
wn = turtle.Screen()
wn.setup(width=800, height=600)  # 화면 크기 설정
wn.bgcolor("black")  # 배경색 검정
wn.tracer(0)  # 화면 업데이트 비활성화 (애니메이션 속도 향상)

# 참가자에게 할당할 색상 목록 (20개로 늘어난 개체 수에 맞춰 색상 추가)
PARTICLE_COLORS = [
    "white", "blue", "green", "purple", "orange",
    "cyan", "magenta", "lime", "pink", "brown",
    "red", "gold", "silver", "teal", "navy",
    "olive", "maroon", "coral", "indigo", "violet"
]


# --- 참가자 (입자) 클래스 ---
class Participant:
    def __init__(self, screen, color_index):  # color_index 인자 추가
        self.t = turtle.Turtle()  # 참가자를 나타내는 터틀 객체
        self.t.speed(0)  # 그리기 속도 최대로 설정
        self.t.shape("circle")  # 원 모양
        self.t.color(PARTICLE_COLORS[color_index])  # 인덱스를 사용하여 색상 할당
        self.t.penup()  # 펜 들기 (이동 시 선을 그리지 않음)
        self.t.shapesize(stretch_wid=0.5, stretch_len=0.5)  # 입자 크기 줄임 (기존 20x20 -> 10x10 픽셀)
        self.radius = 5  # 입자의 반지름 (shapesize 0.5x0.5 이므로 10x10의 절반)

        # 초기 위치 랜덤 설정
        self.t.goto(random.randint(-380, 380), random.randint(-280, 280))
        # 초기 방향 랜덤 설정
        self.t.setheading(random.uniform(0, 360))

        # 재능 (속도) 설정: 정규 분포를 따르며, 최소 1.0, 최대 10.0을 보장
        # 특정 참가자에게 극단적인 속도 값 부여
        if color_index == 0:  # 첫 번째 참가자 (white)
            self.talent = 7.0
        elif color_index == 1:  # 두 번째 참가자 (blue)
            self.talent = 7.0
        elif color_index == 2:  # 세 번째 참가자 (green)
            self.talent = 3.0
        elif color_index == 3:  # 네 번째 참가자 (purple)
            self.talent = 3.0
        else:  # 나머지 참가자들
            self.talent = random.gauss(TALENT_MEAN, TALENT_STD_DEV)

        self.speed = max(1.0, min(10.0, self.talent))  # 속도는 재능에 비례하며, 최소 1.0, 최대 10.0 유지

        self.collision_points = 0.0  # 충돌 포인트 (부동 소수점 값 가능)
        self.luck_points = 0  # 운 포인트
        self.rejection_points = 0  # 거절 포인트 (운의 벽 통과 실패 횟수)

        # 운의 벽을 그릴 전용 터틀 객체 (각 참가자마다 하나씩)
        self.luck_wall_turtle = turtle.Turtle()
        self.luck_wall_turtle.speed(0)
        self.luck_wall_turtle.shape("square")
        self.luck_wall_turtle.color("yellow")  # 운의 벽 색상
        self.luck_wall_turtle.penup()
        self.luck_wall_turtle.hideturtle()  # 처음에는 숨김
        self.luck_wall_thickness = 0  # 현재 활성화된 운의 벽의 두께 (초기값 설정)

        # 현재 입자가 벽을 생성한 고정 개체를 추적 (None 또는 CapitalAccumulator 객체)
        self.active_luck_wall_for_fixed_object = None
        # 각 고정 개체별로 운의 벽 통과 여부를 기록합니다.
        # {fixed_object_instance: True_if_passed_or_False_if_failed_or_never_passed}
        # False 또는 없으면 벽을 재설정/표시할 수 있습니다.
        self.has_passed_wall_for_fixed_object = {}

    def move(self):
        """입자를 현재 속도와 방향으로 이동시킵니다."""
        self.t.forward(self.speed)

    def check_wall_collision(self):
        """화면 경계에 닿았을 때 반사되도록 처리합니다."""
        x_cor = self.t.xcor()
        y_cor = self.t.ycor()

        # x축 경계 충돌
        if x_cor > 390 or x_cor < -390:
            self.t.setx(390 if x_cor > 390 else -390)  # 경계 안으로 위치 조정
            self.t.setheading(180 - self.t.heading())  # 방향 반전
        # y축 경계 충돌
        if y_cor > 290 or y_cor < -290:
            self.t.sety(290 if y_cor > 290 else -290)  # 경계 안으로 위치 조정
            self.t.setheading(360 - self.t.heading())  # 방향 반전

    def check_fixed_object_interaction(self, fixed_objects):
        """
        고정된 개체와의 상호작용을 처리합니다.
        운의 벽 생성, 통과 로직 및 자산 축적을 포함합니다.
        운의 벽을 통과해야만 고정 개체와 충돌하여 자산을 얻을 수 있습니다.
        """
        reflected_in_this_frame = False

        # 1. 입자가 고정 개체의 접근 반경을 벗어났을 때 '벽 통과' 상태 초기화
        # 이전에 벽을 통과했거나 상호작용했던 고정 개체 중 현재 범위 밖으로 나간 것들을 리셋
        objects_to_reset = []
        for f_obj in self.has_passed_wall_for_fixed_object:
            if self.t.distance(f_obj.t) >= LUCK_WALL_DISTANCE_THRESHOLD:
                objects_to_reset.append(f_obj)
        for f_obj in objects_to_reset:
            del self.has_passed_wall_for_fixed_object[f_obj]

        # 2. 현재 입자가 상호작용할 고정 개체 탐색 (가장 가까운 하나만 처리)
        current_interacting_obj = None
        for f_obj in fixed_objects:
            if self.t.distance(f_obj.t) < LUCK_WALL_DISTANCE_THRESHOLD:
                current_interacting_obj = f_obj
                break  # 한 프레임에 하나의 고정 개체와만 상호작용

        # 3. 운의 벽 및 고정 개체와의 상호작용 처리
        if current_interacting_obj:  # 어떤 고정 개체의 접근 반경 안에 있다면
            # 해당 고정 개체에 대한 운의 벽을 이미 통과했는지 확인
            already_passed_wall = self.has_passed_wall_for_fixed_object.get(current_interacting_obj, False)

            if not already_passed_wall:  # 운의 벽을 아직 통과하지 않았다면, 벽 상호작용이 우선
                # 현재 활성화된 벽이 이 고정 개체에 대한 벽이 아니거나, 벽이 숨겨져 있다면 새로 생성/표시
                if self.active_luck_wall_for_fixed_object != current_interacting_obj or not self.luck_wall_turtle.isvisible():
                    self.luck_wall_turtle.hideturtle()
                    self.luck_wall_turtle.clear()

                    self.active_luck_wall_for_fixed_object = current_interacting_obj
                    self.luck_wall_thickness = max(1, random.gauss(WALL_THICKNESS_MEAN, WALL_THICKNESS_STD_DEV))

                    # 운의 벽 위치 및 방향 설정 (고정 개체 접근 반경의 접선 방향)
                    angle_from_fixed_to_particle = current_interacting_obj.t.towards(self.t)
                    wall_center_x = current_interacting_obj.t.xcor() + LUCK_WALL_DISTANCE_THRESHOLD * math.cos(
                        math.radians(angle_from_fixed_to_particle))
                    wall_center_y = current_interacting_obj.t.ycor() + LUCK_WALL_DISTANCE_THRESHOLD * math.sin(
                        math.radians(angle_from_fixed_to_particle))

                    self.luck_wall_turtle.goto(wall_center_x, wall_center_y)
                    self.luck_wall_turtle.setheading(angle_from_fixed_to_particle + 90)
                    self.luck_wall_turtle.shapesize(stretch_wid=0.25, stretch_len=self.luck_wall_thickness / 10.0)
                    self.luck_wall_turtle.showturtle()
                    self.luck_wall_turtle.color("yellow")

                # 활성화된 운의 벽과 충돌했는지 확인
                if self.luck_wall_turtle.isvisible() and self.t.distance(self.luck_wall_turtle) < self.radius + 2.5:
                    prob_pass = (self.speed + LUCK_PASS_FACTOR * self.luck_wall_thickness) / (
                                self.speed + self.luck_wall_thickness)

                    if random.random() < prob_pass:  # 통과 성공
                        self.luck_points += 1  # 운 포인트 1 증가
                        self.has_passed_wall_for_fixed_object[current_interacting_obj] = True  # 벽 통과 기록
                    else:  # 통과 실패 (벽에 부딪혀 반사)
                        self.rejection_points += 1  # 거절 포인트 1 증가
                        self.t.setheading(self.t.heading() + 180)  # 방향 반전
                        reflected_in_this_frame = True  # 반사되었음을 표시
                        self.has_passed_wall_for_fixed_object[current_interacting_obj] = False  # 명시적으로 실패 기록 (재시도 가능)

                    # 벽은 상호작용 후 사라짐
                    self.luck_wall_turtle.hideturtle()
                    self.luck_wall_turtle.clear()
                    # active_luck_wall_for_fixed_object는 그대로 유지하여,
                    # 입자가 이 고정 개체 범위 내에 있는 동안은 벽이 다시 생성되지 않도록 함 (통과/실패 여부와 관계없이)

            else:  # 운의 벽을 이미 통과한 경우 (already_passed_wall == True)
                # 벽을 통과했으므로 더 이상 운의 벽이 표시되지 않도록 함
                if self.luck_wall_turtle.isvisible() and self.active_luck_wall_for_fixed_object == current_interacting_obj:
                    self.luck_wall_turtle.hideturtle()
                    self.luck_wall_turtle.clear()

                # 벽을 통과했으므로 이제 고정 개체와 직접 충돌 가능
                if not reflected_in_this_frame and self.t.distance(
                        current_interacting_obj.t) < current_interacting_obj.radius + self.radius:
                    # 충돌이 발생했을 때 겹침을 해소하고 반사
                    distance_to_obj = self.t.distance(current_interacting_obj.t)
                    overlap = (current_interacting_obj.radius + self.radius) - distance_to_obj

                    # 겹침 해소: 입자를 고정 개체 중심에서 멀리 떨어진 방향으로 이동
                    angle_from_obj_to_particle = current_interacting_obj.t.towards(self.t)
                    self.t.setx(self.t.xcor() + overlap * math.cos(math.radians(angle_from_obj_to_particle)))
                    self.t.sety(self.t.ycor() + overlap * math.sin(math.radians(angle_from_obj_to_particle)))

                    # 방향 반전 (원래 로직 유지)
                    self.t.setheading(self.t.heading() + 180)

                    # 충돌 포인트 증가량은 항상 1.0으로 고정
                    collision_increment = 1.0

                    self.collision_points += collision_increment  # 충돌 포인트 증가
                    reflected_in_this_frame = True  # 반사되었음을 표시

        else:  # 어떤 고정 개체의 범위 내에도 있지 않은 경우
            # 현재 활성화된 운의 벽이 있다면 숨김
            if self.luck_wall_turtle.isvisible():
                self.luck_wall_turtle.hideturtle()
                self.luck_wall_turtle.clear()
            self.active_luck_wall_for_fixed_object = None  # 활성 벽 상태 초기화

    def check_particle_collision(self, other_particle):
        """
        다른 참가자(입자)와의 충돌을 확인하고 처리합니다.
        """
        # 두 입자 간의 거리 계산
        distance = self.t.distance(other_particle.t)
        # 충돌 기준: 두 입자의 반지름 합보다 작을 때
        if distance < self.radius + other_particle.radius:
            # 겹침 해소
            overlap = (self.radius + other_particle.radius) - distance + 0.1  # 작은 여유를 주어 확실히 분리

            # 두 입자 중심을 잇는 각도 계산
            angle_self_to_other = self.t.towards(other_particle.t)

            # 두 입자를 서로 반대 방향으로 밀어냄 (겹침의 절반씩)
            self.t.setx(self.t.xcor() - overlap / 2 * math.cos(math.radians(angle_self_to_other)))
            self.t.sety(self.t.ycor() - overlap / 2 * math.sin(math.radians(angle_self_to_other)))

            other_particle.t.setx(other_particle.t.xcor() + overlap / 2 * math.cos(math.radians(angle_self_to_other)))
            other_particle.t.sety(other_particle.t.ycor() + overlap / 2 * math.sin(math.radians(angle_self_to_other)))

            # 방향 반전 (원래 로직 유지, 간결한 처리를 위해)
            # 입자 A가 입자 B를 향한다면, 충돌 후에는 입자 A는 B의 반대 방향으로, 입자 B는 A의 반대 방향으로
            # 이는 서로의 중심을 잇는 선을 따라 반사하는 것과 유사한 효과를 냄
            self.t.setheading(self.t.towards(other_particle.t) + 180)
            other_particle.t.setheading(other_particle.t.towards(self.t) + 180)


# --- 고정된 개체 (자본 축적기) 클래스 ---
class CapitalAccumulator:
    def __init__(self, screen, x, y):
        self.t = turtle.Turtle()  # 고정된 개체를 나타내는 터틀 객체
        self.t.speed(0)
        self.t.shape("circle")  # 원 모양
        self.t.color("red")  # 빨간색
        self.t.shapesize(stretch_wid=2.0, stretch_len=2.0)  # 지름 2cm에 해당하는 크기 (40x40 픽셀)
        self.radius = 20  # 고정 개체의 반지름 (shapesize 2.0x2.0 이므로 40x40의 절반)
        self.t.penup()
        self.t.goto(x, y)  # 지정된 위치로 이동

        # 접근 반경을 표시할 터틀 객체
        self.approach_radius_turtle = turtle.Turtle()
        self.approach_radius_turtle.speed(0)
        self.approach_radius_turtle.color("gray")  # 회색으로 표시
        self.approach_radius_turtle.penup()
        self.approach_radius_turtle.hideturtle()  # 기본적으로 숨김

        # 접근 반경 원 그리기
        self.approach_radius_turtle.goto(x, y - FIXED_OBJECT_APPROACH_RADIUS)  # 원을 그리기 위한 시작점
        self.approach_radius_turtle.pendown()
        self.approach_radius_turtle.circle(FIXED_OBJECT_APPROACH_RADIUS)  # 2cm 반경 원 그리기
        self.approach_radius_turtle.penup()
        self.approach_radius_turtle.hideturtle()  # 그린 후 숨김


# --- 메인 시뮬레이션 함수 ---
def run_simulation():
    particles = []
    # NUM_PARTICLES 수만큼 참가자(입자) 생성
    for i in range(NUM_PARTICLES):  # 인덱스를 사용하여 색상 할당
        particles.append(Participant(wn, i))

    fixed_objects = []
    # 고정된 개체 위치 설정 (6개로 증가)
    fixed_positions = [
        (-200, 150), (200, 150),
        (-200, -150), (200, -150),
        (0, 0),
        (0, -250)  # 추가된 6번째 고정 개체 위치
    ]
    # NUM_FIXED_OBJECTS 수만큼 고정된 개체 생성
    for pos in fixed_positions[:NUM_FIXED_OBJECTS]:
        fixed_objects.append(CapitalAccumulator(wn, pos[0], pos[1]))

    # --- 정보 표시 터틀 설정 ---
    info_display_turtle = turtle.Turtle()
    info_display_turtle.speed(0)
    info_display_turtle.penup()
    info_display_turtle.hideturtle()
    info_display_turtle.color("lightgray")  # 텍스트 색상

    # --- 초기 정보 표시 ---
    display_info_y = 280  # 정보 표시 시작 Y 좌표
    info_display_turtle.goto(250, display_info_y)  # 오른쪽 상단 위치
    info_display_turtle.write("참가자 정보:", align="left", font=("Arial", 10, "bold"))
    display_info_y -= 20  # 다음 줄을 위해 Y 좌표 이동

    for i, particle in enumerate(particles):
        # 색상 표시
        info_display_turtle.goto(250, display_info_y + 4)  # 색상 사각형 위치 조정
        info_display_turtle.pendown()
        info_display_turtle.fillcolor(PARTICLE_COLORS[i])
        info_display_turtle.begin_fill()
        for _ in range(4):
            info_display_turtle.forward(10)
            info_display_turtle.right(90)
        info_display_turtle.end_fill()
        info_display_turtle.penup()

        # 속도(재능) 텍스트 표시
        info_display_turtle.goto(265, display_info_y)  # 텍스트 위치 조정
        info_display_turtle.write(f"속도(재능): {particle.speed:.2f}", align="left", font=("Arial", 8, "normal"))
        display_info_y -= 15  # 줄 간격 조정

    start_time = time.time()  # 시뮬레이션 시작 시간 기록
    frame_count = 0  # 프레임 카운터

    # 시뮬레이션 메인 루프
    while time.time() - start_time < SIMULATION_DURATION_SECONDS:
        for i, particle in enumerate(particles):
            particle.move()  # 입자 이동
            particle.check_wall_collision()  # 벽 충돌 확인
            particle.check_fixed_object_interaction(fixed_objects)  # 고정 개체 및 운의 벽 상호작용 처리

            # 다른 입자들과의 충돌 확인
            for other_particle in particles[i + 1:]:  # 현재 입자 이후의 입자들만 검사하여 중복 체크 방지
                particle.check_particle_collision(other_particle)

        wn.update()  # 화면 업데이트 (tracer(0) 때문에 필요)
        frame_count += 1

    # 시뮬레이션 종료 후 결과 분석
    print("\n--- 시뮬레이션 종료 ---")
    print(f"총 프레임 수: {frame_count}")

    # 충돌 포인트 기준으로 참가자 정렬 (내림차순)
    particles.sort(key=lambda p: p.collision_points, reverse=True)

    print("\n--- 모든 참가자 결과 ---")
    for i, p in enumerate(particles):  # 모든 참가자 결과 출력
        print(
            f"{i + 1}. 색상: {PARTICLE_COLORS[particles.index(p)]}, 재능: {p.talent:.2f}, 운 포인트: {p.luck_points}, 거절 포인트: {p.rejection_points}, 충돌 포인트: {p.collision_points:.2f}")

    # 모든 터틀 객체 정리 (화면에서 숨기고 그림 지우기)
    for p in particles:
        p.t.hideturtle()
        p.t.clear()
        p.luck_wall_turtle.hideturtle()
        p.luck_wall_turtle.clear()
    for f_obj in fixed_objects:
        f_obj.t.hideturtle()
        f_obj.t.clear()
        f_obj.approach_radius_turtle.hideturtle()  # 접근 반경 터틀도 정리
        f_obj.approach_radius_turtle.clear()

    turtle.done()  # 터틀 그래픽 창 유지 (사용자가 닫을 때까지)


# 시뮬레이션 실행
if __name__ == "__main__":
    run_simulation()





