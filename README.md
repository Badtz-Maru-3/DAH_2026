# DAH_2026

'''ㅁ Docker Container
ㅏ UGV simulation
ㅣ ㅏ husarion/rosbot-gazebo:humble
ㅣ ㅣ ㅏ Gazebo + ROSbot + ROS2 topic (cmd_vel, odom, battery) | ROS2 (DDS, same Network)
ㅣ
ㅏ Bridge
ㅣ ㅏ ros:hunle + pymavlink
ㅣ ㅣ ㅏ husarion_qgc_bridge Nood
ㅣ ㅣ ㅣ ㅏ Up_link: odom/battery -> MAVLink(heartbeat/pos/status)
ㅣ ㅣ ㅣ ㅏ Down_link: MANUAL_CONTROL -> cmd_vel | MAVLink over UDP 14550
ㅣ
ㅏ GCS
ㅣ ㅏ QGroundControl
ㅣ ㅣ ㅏ 기체 인식·지도 표시·조이스틱 명령'''