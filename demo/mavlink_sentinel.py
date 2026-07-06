#!/usr/bin/env python3
import time
import math
from pymavlink import mavutil

# --- 보안 임계값 설정 ---
BASE_LAT = 37.5665
BASE_LON = 126.9780

MAX_GPS_JUMP = 100.0         # GPS가 한 번에 100m 이상 점프하면 스푸핑으로 간주
MAX_GEOFENCE_RADIUS = 500.0  # 미션 목적지가 500m 반경을 벗어나면 악성 미션으로 간주


class MavlinkSentinel:
    def __init__(self, listen_port=14551, target_port=14550):
        # 1. 입력단 (감시 채널): 해커나 사용자가 명령을 보내는 포트 (14551)
        self.proxy_in = mavutil.mavlink_connection(f"udpin:127.0.0.1:{listen_port}")

        # 2. 출력단 (로봇 안전 채널): 실제 로봇(SITL/FCU)이 듣고 있는 포트 (14550)
        self.proxy_out = mavutil.mavlink_connection(f"udpout:127.0.0.1:{target_port}")

        print(f"=== [방화벽] MAVLink 전용 방화벽 가동 ===")
        print(f" - 감시 포트: UDP {listen_port}")
        print(f" - 안전 전달 포트: UDP {target_port}")
        print(f"======================================")

    # 거리 계산 공식
    def calc_distance(self, lat1, lon1, lat2, lon2):
        dx = (lon2 - lon1) * 111000 * math.cos(math.radians((lat1 + lat2) / 2))
        dy = (lat2 - lat1) * 111000
        return math.sqrt(dx ** 2 + dy ** 2)

    def run(self):
        attack_count = 0

        while True:
            # 14551 포트로 들어오는 모든 MAVLink 패킷을 가로챔
            msg = self.proxy_in.recv_match(blocking=True)
            if not msg:
                continue

            msg_type = msg.get_type()

            # ==========================================
            # 방어 1: GPS 순간이동(Jump) 탐지 로직
            # ==========================================
            if msg_type == 'GPS_INPUT':
                # 해커 코드의 int(lat * 1e7) 형식을 다시 소수점으로 복원
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7

                dist = self.calc_distance(BASE_LAT, BASE_LON, lat, lon)

                # 탐지 시 패킷 폐기 (Drop)
                if dist > MAX_GPS_JUMP:
                    attack_count += 1
                    print(f"[GPS 스푸핑 차단] 정상 위치에서 {dist:.1f}m 점프 감지! -> 패킷 폐기 (누적: {attack_count})")
                    continue  # 아래의 proxy_out.write 를 건너뛰어 패킷을 증발시킴

            # ==========================================
            # 방어 2: 악성 목적지(Geofence) 탐지 로직
            # ==========================================
            elif msg_type == 'MISSION_ITEM_INT':
                lat = msg.x / 1e7
                lon = msg.y / 1e7

                dist = self.calc_distance(BASE_LAT, BASE_LON, lat, lon)

                # 탐지 시 패킷 폐기 (Drop)
                if dist > MAX_GEOFENCE_RADIUS:
                    attack_count += 1
                    print(f"[악성 미션 차단] 작업 반경에서 {dist:.1f}m 이탈! -> 패킷 폐기 (누적: {attack_count})")
                    continue

            # ==========================================
            # 정상 패킷 처리
            # ==========================================
            # 공격이 아닌 정상 MAVLink 패킷은 실제 로봇 포트(14550)로 그대로 통과시킴
            self.proxy_out.write(msg.get_msgbuf())


if __name__ == '__main__':
    sentinel = MavlinkSentinel()
    sentinel.run()
