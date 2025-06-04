import turtle
import random
import math
import time

# --- 시뮬레이션 설정 ---
NUM_PARTICLES = 10 # 가상 참가자(입자) 수
NUM_FIXED_OBJECTS = 5 # 고정된 개체(자본 축적기) 수
SIMULATION_DURATION_SECONDS = 40 # 시뮬레이션 실행 시간 (초), 가상 40년

# 재능 (입자의 속도) 분포 설정
# 평균적인 재능을 가진 사람이 가장 많고, 재능이 매우 뛰어나거나 낮은 사람은 소수
TALENT_MEAN = 3.0 # 재능의 평균
TALENT_STD_DEV = 1.0 # 재능의 표준 편차

# 운의 벽 두께 분포 설정
# 운의 벽이 두꺼울수록 통과하기 어려움
WALL_THICKNESS_MEAN = 10.0 # 운의 벽 두께 평균
WALL_THICKNESS_STD_DEV = 3.0 # 운의 벽 두께 표준 편차
LUCK_WALL_DISTANCE_THRESHOLD = 40 # 고정된 개체에 얼마나 가까이 접근해야 운의 벽이 생기는가 (픽셀, 2cm 반경)

# 고정된 개체의 시각적 접근 반경 (2cm에 해당)
FIXED_OBJECT_APPROACH_RADIUS = 40

# --- 화면 설정 ---
wn = turtle.Screen()
wn.setup(width=800, height=600) # 화면 크기 설정
wn.bgcolor("black") # 배경색 검정
wn.tracer(0) # 화면 업데이트 비활성화 (애니메이션 속도 향상)

# 참가자에게 할당할 색상 목록 (10개)
PARTICLE_COLORS = [
    "white", "blue", "green", "purple", "orange",
    "cyan", "magenta", "lime", "pink", "brown"
]

# --- 참가자 (입자) 클래스 ---
class Participant:
    def __init__(self, screen, color_index): # color_index 인자 추가
        self.t = turtle.Turtle() # 참가자를 나타내는 터틀 객체
        self.t.speed(0) # 그리기 속도 최대로 설정
        self.t.shape("circle") # 원 모양
        self.t.color(PARTICLE_COLORS[color_index]) # 인덱스를 사용하여 색상 할당
        self.t.penup() # 펜 들기 (이동 시 선을 그리지 않음)
        self.t.shapesize(stretch_wid=0.5, stretch_len=0.5) # 입자 크기 줄임 (기존 20x20 -> 10x10 픽셀)
        self.radius = 5 # 입자의 반지름 (shapesize 0.5x0.5 이므로 10x10의 절반)

        # 초기 위치 랜덤 설정
        self.t.goto(random.randint(-380, 380), random.randint(-280, 280))
        # 초기 방향 랜덤 설정
        self.t.setheading(random.uniform(0, 360))

        # 재능 (속도) 설정: 정규 분포를 따르며, 최소 속도를 보장
        self.talent = random.gauss(TALENT_MEAN, TALENT_STD_DEV)
        self.speed = max(0.5, self.talent) # 속도는 재능에 비례하며, 최소 0.5 유지

        self.collision_points = 0.0 # 충돌 포인트 (부동 소수점 값 가능)
        self.luck_points = 0 # 운 포인트

        # 운의 벽을 그릴 전용 터틀 객체 (각 참가자마다 하나씩)
        self.luck_wall_turtle = turtle.Turtle()
        self.luck_wall_turtle.speed(0)
        self.luck_wall_turtle.shape("square")
        self.luck_wall_turtle.color("yellow") # 운의 벽 색상
        self.luck_wall_turtle.penup()
        self.luck_wall_turtle.hideturtle() # 처음에는 숨김
        self.luck_wall_thickness = 0 # 현재 활성화된 운의 벽의 두께 (초기값 설정)
        # 현재 입자가 벽을 생성한 고정 개체를 추적 (None 또는 CapitalAccumulator 객체)
        self.active_luck_wall_for_fixed_object = None

    def move(self):
        """입자를 현재 속도와 방향으로 이동시킵니다."""
        self.t.forward(self.speed)

    def check_wall_collision(self):
        """화면 경계에 닿았을 때 반사되도록 처리합니다."""
        x_cor = self.t.xcor()
        y_cor = self.t.ycor()

        # x축 경계 충돌
        if x_cor > 390 or x_cor < -390:
            self.t.setx(390 if x_cor > 390 else -390) # 경계 안으로 위치 조정
            self.t.setheading(180 - self.t.heading()) # 방향 반전
        # y축 경계 충돌
        if y_cor > 290 or y_cor < -290:
            self.t.sety(290 if y_cor > 290 else -290) # 경계 안으로 위치 조정
            self.t.setheading(360 - self.t.heading()) # 방향 반전

    def check_fixed_object_interaction(self, fixed_objects):
        """
        고정된 개체와의 상호작용을 처리합니다.
        운의 벽 생성 및 통과 로직을 포함합니다.
        """
        # 이 프레임에서 입자가 어떤 것에든 반사되었는지 추적
        reflected_in_this_frame = False

        # --- 고정된 개체와의 직접 충돌 및 자산 카운팅 로직 ---
        # 모든 고정 개체를 순회하며 직접 충돌을 확인
        for f_obj in fixed_objects:
            if self.t.distance(f_obj.t) < f_obj.radius + self.radius:
                # 충돌 포인트 증가량 결정
                collision_increment = 1.0
                if self.luck_points >= 15:
                    collision_increment = 3.0
                elif self.luck_points >= 10:
                    collision_increment = 2.0
                elif self.luck_points >= 5:
                    collision_increment = 1.5

                self.collision_points += collision_increment # 충돌 포인트 증가
                self.t.setheading(self.t.heading() + 180) # 고정된 개체에서 반사
                reflected_in_this_frame = True
                break # 한 프레임에 하나의 고정 개체 충돌만 처리

        # --- 운의 벽 생성 및 가시성 로직 ---
        # 현재 입자가 어떤 고정 개체의 접근 반경 안에 있는지 확인
        current_fixed_object_in_range = None
        for f_obj in fixed_objects:
            if self.t.distance(f_obj.t) < LUCK_WALL_DISTANCE_THRESHOLD:
                current_fixed_object_in_range = f_obj
                break

        if current_fixed_object_in_range:
            # 입자가 고정 개체 범위 안에 있고,
            # (현재 활성화된 벽이 없거나, 활성화된 벽이 다른 고정 개체에 대한 것일 때)
            if self.active_luck_wall_for_fixed_object != current_fixed_object_in_range:
                # 기존에 활성화된 벽이 있다면 제거
                if self.luck_wall_turtle.isvisible():
                    self.luck_wall_turtle.hideturtle()
                    self.luck_wall_turtle.clear()

                self.active_luck_wall_for_fixed_object = current_fixed_object_in_range # 현재 접근 중인 고정 개체 설정
                self.luck_wall_thickness = max(1, random.gauss(WALL_THICKNESS_MEAN, WALL_THICKNESS_STD_DEV))

                # 운의 벽 위치 설정: 고정된 개체의 접근 반경에서 접선 방향으로 생성
                # 1. 고정된 개체에서 입자로 향하는 각도 계산
                angle_from_fixed_to_particle = current_fixed_object_in_range.t.towards(self.t)

                # 2. 고정된 개체 중심에서 LUCK_WALL_DISTANCE_THRESHOLD만큼 떨어진 지점 계산
                #    이 지점이 벽의 중심이 될 것임
                wall_center_x = current_fixed_object_in_range.t.xcor() + LUCK_WALL_DISTANCE_THRESHOLD * math.cos(math.radians(angle_from_fixed_to_particle))
                wall_center_y = current_fixed_object_in_range.t.ycor() + LUCK_WALL_DISTANCE_THRESHOLD * math.sin(math.radians(angle_from_fixed_to_particle))

                self.luck_wall_turtle.goto(wall_center_x, wall_center_y)

                # 3. 벽의 방향을 해당 지점에서 고정 개체 반경에 접선 방향으로 설정
                #    (고정 개체에서 벽 중심까지의 선에 수직)
                self.luck_wall_turtle.setheading(angle_from_fixed_to_particle + 90) # 또는 -90

                self.luck_wall_turtle.shapesize(stretch_wid=0.05, stretch_len=self.luck_wall_thickness / 10.0)
                self.luck_wall_turtle.showturtle()
                self.luck_wall_turtle.color("yellow")
        else: # 입자가 어떤 고정 개체의 범위 내에도 있지 않은 경우
            if self.luck_wall_turtle.isvisible():
                self.luck_wall_turtle.hideturtle()
                self.luck_wall_turtle.clear()
            self.active_luck_wall_for_fixed_object = None # 모든 범위에서 벗어나면 상태 초기화

        # --- 운의 벽 충돌 로직 (활성화된 경우) ---
        # 이 프레임에서 고정 개체에 의해 반사되지 않았을 때만 운의 벽 충돌을 확인
        if not reflected_in_this_frame and self.luck_wall_turtle.isvisible() and self.active_luck_wall_for_fixed_object is not None:
            # 운의 벽과 충돌했는지 확인
            # 벽의 실제 폭은 20 * 0.05 = 1 픽셀. 절반 폭은 0.5 픽셀.
            if self.t.distance(self.luck_wall_turtle) < self.radius + 0.5:
                # 운의 벽을 통과할 확률 계산 (이 확률은 '기회 활용'의 개념)
                prob_pass = (self.speed + 0.75 * self.luck_wall_thickness) / (self.speed + self.luck_wall_thickness)

                if random.random() < prob_pass: # 운의 벽 통과 성공 (튕겨져 나오지 않음)
                    self.luck_points += 1 # 운 포인트 1 증가
                    pass
                else: # 운의 벽 통과 실패 (벽에 부딪혀 반사)
                    self.t.setheading(self.t.heading() + 180)
                    reflected_in_this_frame = True # 벽에 의해 반사되었음을 표시

                # 운의 벽은 상호작용 후 사라짐
                self.luck_wall_turtle.hideturtle()
                self.luck_wall_turtle.clear()
                # active_luck_wall_for_fixed_object는 그대로 유지하여,
                # 입자가 해당 고정 개체 반경을 벗어나기 전까지는 다시 벽이 생성되지 않도록 함


    def check_particle_collision(self, other_particle):
        """
        다른 참가자(입자)와의 충돌을 확인하고 처리합니다.
        """
        # 두 입자 간의 거리 계산
        distance = self.t.distance(other_particle.t)
        # 충돌 기준: 두 입자의 반지름 합보다 작을 때
        if distance < self.radius + other_particle.radius:
            # 충돌 시 간단한 반사 로직
            # 서로 반대 방향으로 튕겨나가도록 방향을 조정합니다.
            self_heading_to_other = self.t.towards(other_particle.t)
            other_heading_to_self = other_particle.t.towards(self.t)

            self.t.setheading(self_heading_to_other + 180)
            other_particle.t.setheading(other_heading_to_self + 180)

            # 겹침 방지를 위해 약간 밀어냅니다.
            overlap = (self.radius + other_particle.radius) - distance
            self.t.forward(overlap / 2)
            other_particle.t.forward(overlap / 2)


# --- 고정된 개체 (자본 축적기) 클래스 ---
class CapitalAccumulator:
    def __init__(self, screen, x, y):
        self.t = turtle.Turtle() # 고정된 개체를 나타내는 터틀 객체
        self.t.speed(0)
        self.t.shape("circle") # 원 모양
        self.t.color("red") # 빨간색
        self.t.shapesize(stretch_wid=0.5, stretch_len=0.5) # 지름 0.5cm에 해당하는 크기 (10x10 픽셀)
        self.radius = 5 # 고정 개체의 반지름 (shapesize 0.5x0.5 이므로 10x10의 절반)
        self.t.penup()
        self.t.goto(x, y) # 지정된 위치로 이동

        # 접근 반경을 표시할 터틀 객체
        self.approach_radius_turtle = turtle.Turtle()
        self.approach_radius_turtle.speed(0)
        self.approach_radius_turtle.color("gray") # 회색으로 표시
        self.approach_radius_turtle.penup()
        self.approach_radius_turtle.hideturtle() # 기본적으로 숨김

        # 접근 반경 원 그리기
        self.approach_radius_turtle.goto(x, y - FIXED_OBJECT_APPROACH_RADIUS) # 원을 그리기 위한 시작점
        self.approach_radius_turtle.pendown()
        self.approach_radius_turtle.circle(FIXED_OBJECT_APPROACH_RADIUS) # 2cm 반경 원 그리기
        self.approach_radius_turtle.penup()
        self.approach_radius_turtle.hideturtle() # 그린 후 숨김

# --- 메인 시뮬레이션 함수 ---
def run_simulation():
    particles = []
    # NUM_PARTICLES 수만큼 참가자(입자) 생성
    for i in range(NUM_PARTICLES): # 인덱스를 사용하여 색상 할당
        particles.append(Participant(wn, i))

    fixed_objects = []
    # 고정된 개체 위치 설정
    fixed_positions = [
        (-200, 150), (200, 150),
        (-200, -150), (200, -150),
        (0, 0)
    ]
    # NUM_FIXED_OBJECTS 수만큼 고정된 개체 생성
    for pos in fixed_positions[:NUM_FIXED_OBJECTS]:
        fixed_objects.append(CapitalAccumulator(wn, pos[0], pos[1]))

    # --- 정보 표시 터틀 설정 ---
    info_display_turtle = turtle.Turtle()
    info_display_turtle.speed(0)
    info_display_turtle.penup()
    info_display_turtle.hideturtle()
    info_display_turtle.color("lightgray") # 텍스트 색상

    # --- 초기 정보 표시 ---
    display_info_y = 280 # 정보 표시 시작 Y 좌표
    info_display_turtle.goto(250, display_info_y) # 오른쪽 상단 위치
    info_display_turtle.write("참가자 정보:", align="left", font=("Arial", 10, "bold"))
    display_info_y -= 20 # 다음 줄을 위해 Y 좌표 이동

    for i, particle in enumerate(particles):
        # 색상 표시
        info_display_turtle.goto(250, display_info_y + 4) # 색상 사각형 위치 조정
        info_display_turtle.pendown()
        info_display_turtle.fillcolor(PARTICLE_COLORS[i])
        info_display_turtle.begin_fill()
        for _ in range(4):
            info_display_turtle.forward(10)
            info_display_turtle.right(90)
        info_display_turtle.end_fill()
        info_display_turtle.penup()

        # 속도(재능) 텍스트 표시
        info_display_turtle.goto(265, display_info_y) # 텍스트 위치 조정
        info_display_turtle.write(f"속도(재능): {particle.speed:.2f}", align="left", font=("Arial", 8, "normal"))
        display_info_y -= 15 # 줄 간격 조정

    start_time = time.time() # 시뮬레이션 시작 시간 기록
    frame_count = 0 # 프레임 카운터

    # 시뮬레이션 메인 루프
    while time.time() - start_time < SIMULATION_DURATION_SECONDS:
        for i, particle in enumerate(particles):
            particle.move() # 입자 이동
            particle.check_wall_collision() # 벽 충돌 확인
            particle.check_fixed_object_interaction(fixed_objects) # 고정 개체 및 운의 벽 상호작용 처리

            # 다른 입자들과의 충돌 확인
            for other_particle in particles[i+1:]: # 현재 입자 이후의 입자들만 검사하여 중복 체크 방지
                particle.check_particle_collision(other_particle)

        wn.update() # 화면 업데이트 (tracer(0) 때문에 필요)
        frame_count += 1

    # 시뮬레이션 종료 후 결과 분석
    print("\n--- 시뮬레이션 종료 ---")
    print(f"총 프레임 수: {frame_count}")

    # 충돌 포인트 기준으로 참가자 정렬 (내림차순)
    particles.sort(key=lambda p: p.collision_points, reverse=True)

    print("\n--- 상위 10명의 참가자 ---")
    for i, p in enumerate(particles[:10]):
        print(f"{i+1}. 재능: {p.talent:.2f}, 운 포인트: {p.luck_points}, 충돌 포인트: {p.collision_points:.2f}")

    print("\n--- 하위 10명의 참가자 ---")
    for i, p in enumerate(particles[-10:]):
        print(f"{i+1}. 재능: {p.talent:.2f}, 운 포인트: {p.luck_points}, 충돌 포인트: {p.collision_points:.2f}")

    # 모든 터틀 객체 정리 (화면에서 숨기고 그림 지우기)
    for p in particles:
        p.t.hideturtle()
        p.t.clear()
        p.luck_wall_turtle.hideturtle()
        p.luck_wall_turtle.clear()
    for f_obj in fixed_objects:
        f_obj.t.hideturtle()
        f_obj.t.clear()
        f_obj.approach_radius_turtle.hideturtle() # 접근 반경 터틀도 정리
        f_obj.approach_radius_turtle.clear()

    turtle.done() # 터틀 그래픽 창 유지 (사용자가 닫을 때까지)

# 시뮬레이션 실행
if __name__ == "__main__":
    run_simulation()