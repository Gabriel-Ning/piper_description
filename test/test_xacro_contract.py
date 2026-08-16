from pathlib import Path
import importlib.util
import re
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument
import xacro


SHARE = Path(get_package_share_directory("piper_description"))


def _render(filename, **mappings):
    document = xacro.process_file(
        SHARE / "urdf" / filename,
        mappings={name: str(value).lower() for name, value in mappings.items()},
    )
    return ET.fromstring(document.toxml())


def _components(root):
    return {element.attrib["name"]: element for element in root.findall("ros2_control")}


def _plugin(component):
    return component.findtext("./hardware/plugin")


def _parameters(component):
    return {
        parameter.attrib["name"]: parameter.text
        for parameter in component.findall("./hardware/param")
    }


def _joints(component):
    return [joint.attrib["name"] for joint in component.findall("joint")]


def _xacro_arg_defaults(filename):
    text = (SHARE / "urdf" / filename).read_text(encoding="utf-8")
    return dict(
        re.findall(r'<xacro:arg name="([^"]+)" default="([^"]*)"', text)
    )


def test_arm_component_keeps_strict_six_joint_contract():
    components = _components(_render("piper.urdf.xacro"))
    assert set(components) == {"PiperHardware"}
    arm = components["PiperHardware"]
    assert _plugin(arm) == "piper_hardware_interface/PiperHardwareInterface"
    assert _joints(arm) == [f"joint{index}" for index in range(1, 7)]
    assert "init_can" not in _parameters(arm)


def test_single_gripper_is_an_independent_real_component():
    root = _render(
        "piper_with_gripper.urdf.xacro",
        prefix="left_",
        can_interface="piper0",
    )
    components = _components(root)
    assert set(components) == {"PiperHardware", "PiperGripperHardware"}
    assert _joints(components["PiperHardware"]) == [
        f"left_joint{index}" for index in range(1, 7)
    ]

    gripper = components["PiperGripperHardware"]
    assert _plugin(gripper) == "piper_hardware_interface/PiperGripperInterface"
    assert _joints(gripper) == ["left_gripper_joint1"]
    assert _parameters(gripper) == {
        "can_interface": "piper0",
        "home_on_activate": "true",
    }

    physical_joints = {joint.attrib["name"]: joint for joint in root.findall("joint")}
    assert (
        physical_joints["left_gripper_joint1"].find("limit").attrib["upper"] == "0.04"
    )
    assert physical_joints["left_gripper_joint2"].find("mimic").attrib == {
        "joint": "left_gripper_joint1",
        "multiplier": "-1",
        "offset": "0",
    }


def test_fake_arm_and_gripper_remain_separate_components():
    components = _components(
        _render("piper_with_gripper.urdf.xacro", use_fake_hardware="true")
    )
    assert len(components) == 2
    assert {_plugin(component) for component in components.values()} == {
        "mock_components/GenericSystem"
    }


def test_dual_arm_defaults_to_table_and_piper_grippers():
    root = _render(
        "piper_bimanual_manipulation.urdf.xacro",
        use_fake_hardware="false",
        left_can_interface="piper0",
        right_can_interface="piper1",
    )
    components = _components(root)
    assert set(components) == {
        "left_piper_hardware",
        "left_piper_gripper_hardware",
        "right_piper_hardware",
        "right_piper_gripper_hardware",
    }
    for side, can_interface in (("left", "piper0"), ("right", "piper1")):
        gripper = components[f"{side}_piper_gripper_hardware"]
        assert _plugin(gripper) == "piper_hardware_interface/PiperGripperInterface"
        assert _parameters(gripper)["can_interface"] == can_interface

    assert all(
        "init_can" not in _parameters(component) for component in components.values()
    )

    links = {link.attrib["name"] for link in root.findall("link")}
    assert {
        "table_base_link",
        "table_table_link",
        "left_mounting_plate_link",
        "right_mounting_plate_link",
    }.issubset(links)

    physical_joints = {joint.attrib["name"]: joint for joint in root.findall("joint")}
    args = _xacro_arg_defaults("piper_bimanual_manipulation.urdf.xacro")
    assert physical_joints["world_to_left_mount"].find("origin").attrib == {
        "rpy": args["left_rpy"],
        "xyz": args["left_xyz"],
    }
    assert physical_joints["world_to_right_mount"].find("origin").attrib == {
        "rpy": args["right_rpy"],
        "xyz": args["right_xyz"],
    }
    for prefix, xyz in (("left_", args["left_xyz"]), ("right_", args["right_xyz"])):
        plate_joint = physical_joints[f"{prefix}mounting_plate_joint"]
        assert plate_joint.find("parent").attrib["link"] == "world"
        assert plate_joint.find("origin").attrib == {"rpy": "0 0 0", "xyz": xyz}
        plate = next(
            link
            for link in root.findall("link")
            if link.attrib["name"] == f"{prefix}mounting_plate_link"
        )
        assert plate.find("collision") is None
        visual = plate.find("visual")
        assert visual.find("origin").attrib["xyz"] == "0 0.005 -0.005"
        assert visual.find("geometry/box").attrib["size"] == "0.26 0.1 0.01"
    for prefix in ("left_", "right_"):
        assert physical_joints[f"{prefix}gripper_tcp_joint"].find("origin").attrib == {
            "rpy": "0 0 0",
            "xyz": "0 0 0.1358",
        }


def test_dual_arm_can_disable_grippers():
    root = _render(
        "piper_bimanual_manipulation.urdf.xacro",
        enable_left_gripper="false",
        enable_right_gripper="false",
    )
    assert set(_components(root)) == {
        "left_piper_hardware",
        "right_piper_hardware",
    }
    links = {link.attrib["name"] for link in root.findall("link")}
    assert {"table_base_link", "table_table_link"}.issubset(links)


def test_dual_arm_workcell_and_hardware_tuning_are_configurable():
    root = _render(
        "piper_bimanual_manipulation.urdf.xacro",
        connected_to="cell_base",
        enable_table="false",
        use_fake_hardware="false",
        left_can_interface="piper0",
        right_can_interface="piper1",
        left_mit_kd_effort_damping="0.1",
        right_mit_kd_effort_damping="0.2",
        left_gripper_home_on_activate="false",
        right_gripper_home_on_activate="false",
    )
    links = {link.attrib["name"] for link in root.findall("link")}
    joints = {joint.attrib["name"]: joint for joint in root.findall("joint")}
    components = _components(root)

    assert "cell_base" in links
    assert {"table_base_link", "table_table_link"}.isdisjoint(links)
    assert joints["world_to_left_mount"].find("parent").attrib["link"] == "cell_base"
    assert joints["world_to_right_mount"].find("parent").attrib["link"] == "cell_base"
    assert joints["left_mounting_plate_joint"].find("parent").attrib["link"] == "cell_base"
    assert joints["right_mounting_plate_joint"].find("parent").attrib["link"] == "cell_base"
    assert _parameters(components["left_piper_hardware"])[
        "mit_kd_effort_damping"
    ] == "0.1"
    assert _parameters(components["right_piper_hardware"])[
        "mit_kd_effort_damping"
    ] == "0.2"
    assert _parameters(components["left_piper_gripper_hardware"])[
        "home_on_activate"
    ] == "false"
    assert _parameters(components["right_piper_gripper_hardware"])[
        "home_on_activate"
    ] == "false"


def _launch_arg_defaults(filename):
    path = SHARE / "launch" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    defaults = {}
    for entity in module.generate_launch_description().entities:
        if isinstance(entity, DeclareLaunchArgument):
            parts = entity.default_value or []
            defaults[entity.name] = "".join(
                getattr(part, "text", "") for part in parts
            )
    return defaults


def test_visualize_launches_defer_model_poses_to_xacro():
    bimanual = _launch_arg_defaults("visualize_piper_bimanual.launch.py")
    for name in ("left_xyz", "right_xyz", "left_rpy", "right_rpy"):
        assert bimanual[name] == ""

    single = _launch_arg_defaults("visualize_piper.launch.py")
    for name in ("xyz", "rpy", "connected_to", "xyz_ee", "rpy_ee", "tcp_xyz", "tcp_rpy"):
        assert single[name] == ""

    foxglove = _launch_arg_defaults("visualize_piper_foxglove.launch.py")
    for name in ("xyz", "rpy", "connected_to", "xyz_ee", "rpy_ee", "tcp_xyz", "tcp_rpy"):
        assert foxglove[name] == ""
