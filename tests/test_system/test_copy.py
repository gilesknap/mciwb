from tests.test_unit.test_copier import copy_anchors


def test_copy_anchors(minecraft_client):
    """
    Runs the unit test copy_anchors() but uses a real client so tests
    against a real minecraft server instead of a mock one.
    """
    copy_anchors()
