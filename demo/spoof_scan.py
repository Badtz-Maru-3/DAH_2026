import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanSpoof(Node):
    def __init__(self):
        super().__init__('scan_spoof')
        self.pub = self.create_publisher(LaserScan, '/scan', qos_profile_sensor_data)
        self.count = 0
        self.create_timer(0.02, self.tick)  # 50Hz (정상 publisher보다 우세하게)

    def tick(self):
        n = 360
        m = LaserScan()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = 'laser'  # 확인된 실제 frame_id
        m.angle_min = -math.pi
        m.angle_max = math.pi
        m.angle_increment = (m.angle_max - m.angle_min) / n
        m.range_min = 0.1
        m.range_max = 10.0
        m.ranges = [0.5] * n  # 0.5m 가짜 장애물 링 (은폐하려면 [9.99]*n)
        self.pub.publish(m)

        self.count += 1
        if self.count % 50 == 0:  # 1초마다 한 번 로그
            self.get_logger().info(f'spoof scan published: {self.count}')


def main():
    rclpy.init()
    node = ScanSpoof()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
