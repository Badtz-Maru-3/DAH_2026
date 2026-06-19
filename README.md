```markdown
# DAH_2026

```text
DAH_2026
└── Docker Container
    ├── UGV simulation
    │   └── husarion/rosbot-gazebo:humble
    │       └── Gazebo + ROSbot + ROS2 topic (cmd_vel, odom, battery) [ROS2 (DDS, same Network)]
    │
    ├── Bridge
    │   └── ros:humble + pymavlink
    │       └── husarion_qgc_bridge Node
    │           ├── Up_link: odom/battery -> MAVLink(heartbeat/pos/status)
    │           └── Down_link: MANUAL_CONTROL -> cmd_vel [MAVLink over UDP 14550]
    │
    └── GCS
        └── QGroundControl
            └── 기체 인식·지도 표시·조이스틱 명령