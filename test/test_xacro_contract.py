from pathlib import Path
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
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
    assert physical_joints["left_gripper_joint1"].find("limit").attrib["upper"] == "0.04"
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


def test_dual_gripper_composition_has_four_unique_components():
    root = _render(
        "piper_manipulation.urdf.xacro",
        use_fake_hardware="false",
        enable_left_gripper="true",
        enable_right_gripper="true",
        left_can_interface="piper0",
        right_can_interface="piper1",
    )
    components = _components(root)
    assert set(components) == {
        "LeftPiperHardware",
        "LeftPiperGripperHardware",
        "RightPiperHardware",
        "RightPiperGripperHardware",
    }
    for side, can_interface in (("Left", "piper0"), ("Right", "piper1")):
        gripper = components[f"{side}PiperGripperHardware"]
        assert _plugin(gripper) == "piper_hardware_interface/PiperGripperInterface"
        assert _parameters(gripper)["can_interface"] == can_interface

    assert all("init_can" not in _parameters(component) for component in components.values())

    physical_joints = {joint.attrib["name"]: joint for joint in root.findall("joint")}
    for prefix in ("left_", "right_"):
        assert physical_joints[f"{prefix}gripper_tcp_joint"].find("origin").attrib == {
            "rpy": "0 0 0",
            "xyz": "0 0 0.1358",
        }


def test_dual_composition_defaults_to_arm_only():
    components = _components(_render("piper_manipulation.urdf.xacro"))
    assert set(components) == {"LeftPiperHardware", "RightPiperHardware"}
