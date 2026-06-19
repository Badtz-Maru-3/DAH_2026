# DAH 2026
## Docker container Architecture


### .env
- ROS_DOMAIN_ID=17 | UGV 컨테이너와 Bridge 컨테이너가 같은 ROS2 DDS 공간을 보게 함
- QGC_IP=127.0.0.1 | QGroundControl이 같은 host network에서 뜬다고 가정
- QGC_PORT=14550 | MAVLink UDP 기본 수신 포트
- LIBGL_ALWAYS_SOFTWARE=1 | GPU 문제 줄이려고 Gazebo/QGC를 소프트웨어 렌더링 우선으로 둠

### compose.ewbui.yml
- web으로 ugv,rviz,gcs 전부 띄우는 docker-compose.yml
- QGC    : http://localhost:6080/vnc.html
- Gazebo : http://localhost:6081/vnc_auto.html
- RViz   : http://localhost:6082/vnc_auto.html
  - Fixed Frame: map ==> odom
  - Add: By display type에서 TF 추가
  - Add: By topic에서 /scan -> LaserScan
  - Add: By topic에서 /odometry -> /filtered -> Odometry
- 실행 방법: docker compose --env-file .env -f compose.webui.yml up -d && docker compose --env-file .env -f compose.webui.yml down

### compose.bridge.yml
