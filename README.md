# piper_description

URDF/xacro and mesh assets for the Agilex Piper arm.
All meshes are vendored under this package (`meshes/`), so it does not depend on external `ref/` paths at runtime.

## Layout

- `urdf/parts/piper_arm.xacro`: 6-DOF arm macro (parameterized with `prefix`, `connected_to`, `xyz`, `rpy`)
- `urdf/parts/piper_gripper.xacro`: official gripper macro
- `urdf/parts/piper_arm.ros2_control.xacro`: `ros2_control` block macro (Franka-style include extension)
- `config/joint_limits.yaml`: joint limit source (loaded by `piper_arm.xacro`)
- `config/kinematics.yaml`: joint origin/axis source (loaded by `piper_arm.xacro`)
- `config/inertials.yaml`: link inertial source (loaded by `piper_arm.xacro`)
- `urdf/piper.urdf.xacro`: base arm + ros2_control entrypoint
- `urdf/piper_with_gripper.urdf.xacro`: arm + official gripper + ros2_control entrypoint

## Xacro examples

Base arm:

```bash
xacro "$(ros2 pkg prefix piper_description)/share/piper_description/urdf/piper.urdf.xacro" \
  can_interface:=can0 init_can:=false
```

With gripper:

```bash
xacro "$(ros2 pkg prefix piper_description)/share/piper_description/urdf/piper_with_gripper.urdf.xacro" \
  can_interface:=can0 init_can:=false load_gripper:=true
```

With prefix (multi-arm ready naming):

```bash
xacro "$(ros2 pkg prefix piper_description)/share/piper_description/urdf/piper.urdf.xacro" \
  prefix:=left_ connected_to:=world xyz:='0 0 0' rpy:='0 0 0'
```

This package is intentionally description-only. The hardware plugin lives in
`piper_hardware_interface`.

Mesh layout is split by purpose:
- `meshes/piper_arm/visual/*.dae`
- `meshes/piper_arm/collision/*.stl`
- `meshes/piper_gripper/visual/*.dae`
- `meshes/piper_gripper/collision/*.stl`

## Visualize in RViz

Start an interactive visualization (joint sliders + robot_state_publisher + RViz):

```bash
ros2 launch piper_description visualize_piper.launch.py
```

With gripper:

```bash
ros2 launch piper_description visualize_piper.launch.py with_gripper:=true
```

`visualize_piper.launch.py` is model-only: it forces `ros2_control:=false` and does not require CAN or hardware access.
For isolated visualization, it publishes/subscribes joint states on `/piper_description/joint_states`
by default so unrelated `/joint_states` publishers do not affect RViz. To use the conventional
global topic, pass:

```bash
ros2 launch piper_description visualize_piper.launch.py joint_states_topic:=/joint_states
```

### RViz launch parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `with_gripper` | `false` | Load `piper_with_gripper.urdf.xacro` instead of the base arm model. |
| `prefix` | `""` | Prefix added to generated link and joint names for multi-arm setups. |
| `connected_to` | `world` | Parent link used by the fixed base mount joint. |
| `xyz` | `0 0 0` | Base mount translation relative to `connected_to`. |
| `rpy` | `0 0 0` | Base mount rotation relative to `connected_to`. |
| `xyz_ee` | `0 0 0` | Gripper mount translation relative to `flange_link`; used only with `with_gripper:=true`. |
| `rpy_ee` | `0 0 0` | Gripper mount rotation relative to `flange_link`; used only with `with_gripper:=true`. |
| `tcp_xyz` | from `config/gripper_tcp.yaml` | Gripper TCP translation relative to `gripper_base`. |
| `tcp_rpy` | from `config/gripper_tcp.yaml` | Gripper TCP rotation relative to `gripper_base`. |
| `use_joint_state_gui` | `false` | Use `joint_state_publisher_gui` instead of headless `joint_state_publisher`. |
| `use_rviz` | `true` | Start RViz with `rviz/visualize_piper.rviz`. |
| `joint_states_topic` | `/piper_description/joint_states` | Joint state topic used by the visualization nodes. |

## Visualize in Foxglove

The Foxglove launch starts `robot_state_publisher`, `joint_state_publisher`, and
`foxglove_bridge`. Install the bridge first if it is not already available:

```bash
pixi add ros-humble-foxglove-bridge
```

Arm only:

```bash
ros2 launch piper_description visualize_piper_foxglove.launch.py
```

With gripper:

```bash
ros2 launch piper_description visualize_piper_foxglove.launch.py with_gripper:=true
```

Then connect Foxglove Studio to:

```text
ws://localhost:8765
```

You can import `config/foxglove/display_robot.json` as a simple 3D layout that reads
the robot model from `/robot_description`.

### Foxglove launch parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `with_gripper` | `false` | Load the gripper model. |
| `prefix` | `""` | Prefix added to generated link and joint names. |
| `connected_to` | `world` | Parent link used by the fixed base mount joint. |
| `xyz` | `0 0 0` | Base mount translation relative to `connected_to`. |
| `rpy` | `0 0 0` | Base mount rotation relative to `connected_to`. |
| `xyz_ee` | `0 0 0` | Gripper mount translation relative to `flange_link`. |
| `rpy_ee` | `0 0 0` | Gripper mount rotation relative to `flange_link`. |
| `tcp_xyz` | from `config/gripper_tcp.yaml` | Gripper TCP translation relative to `gripper_base`. |
| `tcp_rpy` | from `config/gripper_tcp.yaml` | Gripper TCP rotation relative to `gripper_base`. |
| `joint_states_topic` | `/piper_description/joint_states` | Joint state topic used by `robot_state_publisher` and `joint_state_publisher`. |
| `start_bridge` | `true` | Include the `foxglove_bridge` launch file. Set to `false` if a bridge is already running. |
