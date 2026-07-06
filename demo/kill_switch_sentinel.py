import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import threading
import time


class KillSwitchSentinel(Node):
    def __init__(self):
        super().__init__('kill_switch_sentinel')
        self.MAX_LINEAR = 0.5
        self.MAX_ANGULAR = 1.2

        self.is_blocked = False
        self.timeout_timer = None

        # [요구사항 ③] 마지막 공격 패킷 감시용 자동 해제 타임아웃 연장 (5.0초 -> 15.0초)
        self.TIMEOUT_DURATION = 15.0

        # 공용 채널 감시
        self.subscription = self.create_subscription(
            Twist, '/cmd_vel', self.validate_packet, 10)

        # 고속 역주입용 퍼블리셔
        self.override_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.get_logger().info('=== [보안 시스템] 능동형 실시간 제어권 독점 방화벽 가동 ===')

    def validate_packet(self, msg):
        # 위험 명령 수치 검증
        is_attack = abs(msg.linear.x) > self.MAX_LINEAR or abs(msg.angular.z) > self.MAX_ANGULAR

        if is_attack:
            # [요구사항 ②] 이미 차단 중인 상태이더라도, 해커의 추가 공격 패킷을 계속 실시간으로 감지하고 로그를 남김
            if self.is_blocked:
                self.get_logger().warn(
                    f'[차단 중 공격 지속 감지] 해커 가짜 명령 차단 중! '
                    f'유입 수치 -> X: {msg.linear.x:.2f}, Z: {msg.angular.z:.2f}')
                self.reset_timeout_timer()  # 공격이 들어왔으므로 해제 타이머 15초 연장
                return

            # [요구사항 ①] 악성 명령 누적 5회가 아니라, 단 1회 감지 즉시 차단 강력 발동
            self.get_logger().error(
                f'[즉시 차단발동] 악성 명령 포착! 2000Hz 제어권 무한 독점 '
                f'및 {self.TIMEOUT_DURATION}초 타이머 가동.')
            self.is_blocked = True

            # [요구사항 ④] 대량의 난사 패킷을 확실하게 뭉개버리기 위해 타이머가 아닌 '독립 스레드 초고속 루프' 가동
            threading.Thread(target=self.execute_hard_jamming, daemon=True).start()

            # 자동 해제를 위한 타임아웃 타이머 시작
            self.reset_timeout_timer()

    def execute_hard_jamming(self):
        """[요구사항 ④] 해커가 초당 수백 개를 던져도 틈새를 주지 않고 무조건 0.0으로 버퍼를 꽉 채우는 초고속 점유 루프"""
        null_cmd = Twist()
        null_cmd.linear.x = 0.0
        null_cmd.angular.z = 0.0

        # 차단(is_blocked)이 True인 동안 대기시간(sleep)을 0.0005초(2000Hz)로 극단적으로 줄여 무한 난사함
        while self.is_blocked:
            self.override_pub.publish(null_cmd)
            time.sleep(0.0005)

    def reset_timeout_timer(self):
        """공격이 지속되면 기존 해제 타이머를 부수고 새로 15초를 리셋합니다."""
        if self.timeout_timer is not None:
            self.timeout_timer.destroy()

        # 15초 동안 호출(공격)이 없으면 auto_release_firewall 함수를 실행
        self.timeout_timer = self.create_timer(self.TIMEOUT_DURATION, self.auto_release_firewall)

    def auto_release_firewall(self):
        """15초간 추가 공격이 전혀 없을 때만 원상복구합니다."""
        self.get_logger().info(
            f'=== [자동 해제] {self.TIMEOUT_DURATION}초 동안 추가 공격이 없어 방화벽을 안전 개방합니다. ===')

        # 1. 자기 자신(해제 타이머) 중지
        if self.timeout_timer is not None:
            self.timeout_timer.destroy()
            self.timeout_timer = None

        # 2. 방화벽 상태 초기화 (차단 스레드 루프가 자동으로 꺼짐)
        self.is_blocked = False


def main():
    rclpy.init()
    node = KillSwitchSentinel()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
