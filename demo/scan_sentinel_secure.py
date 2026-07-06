import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import copy


class ScanSentinelSecure(Node):
    def __init__(self):
        super().__init__('scan_sentinel_secure')

        self.is_blocked = False
        self.last_attack_timestamp = 0.0
        self.BLOCK_DURATION = 15.0
        self.attack_count = 0  # 추가된 기능: 차단 중 추가 공격 횟수를 세는 카운터

        custom_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE
        )

        # 1. 감시: 원본 채널인 /scan 을 철저히 감시합니다.
        self.sub = self.create_subscription(LaserScan, '/scan', self.verify_and_filter, custom_qos)

        # 2. 새로운 로봇 대피소: 해커가 오염시킨 verified 대신, 깨끗한 '/scan_secure' 채널 생성
        self.pub_secure = self.create_publisher(LaserScan, '/scan_secure', custom_qos)

        # 3. 쓰레기장: 공격 패킷을 100% 쏟아버릴 '/scan_fake' 채널
        self.pub_fake = self.create_publisher(LaserScan, '/scan_fake', custom_qos)

        self.create_timer(1.0, self.check_auto_recovery)

        self.get_logger().info('=== [방화벽] 철벽 방화벽 가동: 공격은 fake로, 로봇은 secure로 분리 ===')

    def verify_and_filter(self, msg):
        now_sec = self.get_clock().now().nanoseconds / 1e9

        valid_ranges = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
        if not valid_ranges:
            if not self.is_blocked:
                self.pub_secure.publish(msg)
            return

        # 0.5m 고정 링 공격 감지 (오차 1mm 미만)
        is_attack = (max(valid_ranges) - min(valid_ranges) < 0.001)

        if is_attack:
            self.last_attack_timestamp = now_sec

            # 공격 패킷 원본을 fake 로 "전부 다" 넘깁니다.
            self.pub_fake.publish(msg)

            # 로봇에게는 inf(장애물 없음)로 정화된 안전 패킷만 secure 로 보냅니다.
            safe_msg = copy.deepcopy(msg)
            safe_msg.ranges = [float('inf')] * len(safe_msg.ranges)

            # =========================================================
            # [추가된 지속 감시 로직] 차단 상태일 때도 공격을 카운트하고 로그 출력
            # =========================================================
            if self.is_blocked:
                self.attack_count += 1
                # 터미널 과부하 방지: 10패킷(약 1초) 단위로 경고 로그 출력
                if self.attack_count % 10 == 0:
                    self.get_logger().warn(
                        f"[차단 유지 중] 추가 공격 지속 격리 중... (누적 격리: {self.attack_count}회)")
                self.pub_secure.publish(safe_msg)
                return

            # =========================================================
            # 최초 공격 탐지 시 1회만 실행되는 차단 발동 로직
            # =========================================================
            self.is_blocked = True
            self.attack_count = 1
            self.get_logger().error(
                f"\n===============================================================\n"
                f"[최초 차단 발동] 1회 공격 감지로 즉시 방화벽 발동!\n"
                f" - 공격 패킷 100% 격리 완료 경로: /scan_fake\n"
                f" - 로봇 100% 안전 대피 경로: /scan_secure\n"
                f"===============================================================\n"
            )
            self.pub_secure.publish(safe_msg)
            return

        # 정상 데이터일 때는 secure로 안전하게 보냄
        if not self.is_blocked:
            self.pub_secure.publish(msg)

    def check_auto_recovery(self):
        if self.is_blocked:
            current_time = self.get_clock().now().nanoseconds / 1e9
            if current_time - self.last_attack_timestamp >= self.BLOCK_DURATION:
                self.is_blocked = False
                self.attack_count = 0  # 해제 시 카운터도 초기화
                self.get_logger().info("[방화벽 개방] 15초간 추가 공격이 없어 정상 상태로 복구합니다.")


def main():
    rclpy.init()
    node = ScanSentinelSecure()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
