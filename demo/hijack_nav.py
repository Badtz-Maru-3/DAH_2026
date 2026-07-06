import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


def yaw_from_quaternion(q):
    """쿼터니언에서 yaw(z축 회전각)만 추출"""
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


def normalize_angle(a):
    """각도를 -pi ~ pi 범위로 정규화"""
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


class HijackNavigator(Node):
    def __init__(self):
        super().__init__('hijack_nav')
        # ===== 공격자가 정한 목표 좌표 =====
        self.target_x = 3.0
        self.target_y = 2.0
        self.arrive_threshold = 0.15  # 15cm 이내면 도착 판정

        # 비례 제어 게인
        self.k_linear = 1.5
        self.k_angular = 3.0
        self.max_linear = 2.0
        self.max_angular = 3.0

        # 현재 위치
        self.cur_x = 0.0
        self.cur_y = 0.0
        self.cur_yaw = 0.0
        self.odom_received = False
        self.arrived = False

        # 공격 시간 제한
        self.start_time = time.time()
        self.attack_duration = 10.0  # 10초 동안만 공격

        # 구독 및 발행
        self.create_subscription(
            Odometry, '/odometry/filtered',
            self.odom_callback, qos_profile_sensor_data)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # 속도 명령 주기: 0.1초 (10Hz)
        self.create_timer(0.1, self.control_loop)

        self.count = 0
        self.get_logger().info(
            f'[hijack] target=({self.target_x}, {self.target_y}), '
            f'threshold={self.arrive_threshold}m, duration={self.attack_duration}s')

    def odom_callback(self, msg):
        """로봇의 현재 위치·방향을 갱신"""
        self.cur_x = msg.pose.pose.position.x
        self.cur_y = msg.pose.pose.position.y
        self.cur_yaw = yaw_from_quaternion(msg.pose.pose.orientation)
        self.odom_received = True

    def control_loop(self):
        cmd = Twist()

        # 공격 시간 초과 시 정지
        if time.time() - self.start_time > self.attack_duration:
            self.cmd_pub.publish(cmd)
            return

        if not self.odom_received:
            self.cmd_pub.publish(cmd)
            return

        if self.arrived:
            self.cmd_pub.publish(cmd)
            return

        # 목표까지 거리·방향 계산
        dx = self.target_x - self.cur_x
        dy = self.target_y - self.cur_y
        distance = math.hypot(dx, dy)
        target_yaw = math.atan2(dy, dx)
        yaw_error = normalize_angle(target_yaw - self.cur_yaw)

        # 도착 판정
        if distance < self.arrive_threshold:
            self.arrived = True
            self.cmd_pub.publish(cmd)
            self.get_logger().info(
                f'[hijack] ARRIVED at ({self.cur_x:.2f}, {self.cur_y:.2f}), '
                f'error={distance:.3f}m')
            return

        # 비례 제어
        angular = self.k_angular * yaw_error
        angular = max(-self.max_angular, min(self.max_angular, angular))

        if abs(yaw_error) < 0.3:  # 방향 오차가 작으면 전진
            linear = self.k_linear * distance
            linear = max(0.0, min(self.max_linear, linear))
        else:
            linear = 0.0

        cmd.linear.x = linear
        cmd.angular.z = angular
        self.cmd_pub.publish(cmd)

        self.count += 1
        if self.count % 10 == 0:  # 1초마다 상태 로그 (10Hz 기준)
            self.get_logger().info(
                f'[hijack] pos=({self.cur_x:.2f}, {self.cur_y:.2f}), '
                f'dist={distance:.2f}m, yaw_err={math.degrees(yaw_error):.1f}deg')


def main():
    rclpy.init()
    node = HijackNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
