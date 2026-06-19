# DAH 2026
## Docker container Architecture


### .env
- ROS_DOMAIN_ID=17 | UGV 컨테이너와 Bridge 컨테이너가 같은 ROS2 DDS 공간을 보게 함
- QGC_IP=127.0.0.1 | QGroundControl이 같은 host network에서 뜬다고 가정
- QGC_PORT=14550 | MAVLink UDP 기본 수신 포트
- LIBGL_ALWAYS_SOFTWARE=1 | GPU 문제 줄이려고 Gazebo/QGC를 소프트웨어 렌더링 우선으로 둠

### 