import navigation
import pytest

@pytest.fixture
def waypoints():
    return [
        navigation.Pose(10, 20, 30),
        navigation.Pose(40, 50, 60),
        navigation.Pose(70, 80, 90),
    ]

@pytest.fixture
def make_navigator():
    def _make_navigator(waypoints=None):
        return navigation.Navigator(waypoints)

    return _make_navigator


def test_inits_with_list(make_navigator, waypoints):
    """Ensure that Navigator will correctly initialise the waypoints list if specified in constructor"""
    navigator = make_navigator(waypoints)
    assert navigator.waypoints == waypoints


def test_waypoints_default_empty_list(make_navigator):
    """When constructor is called without a waypoint list, the list should be initialised as an empty list"""
    navigator = make_navigator()
    assert navigator.waypoints == []

def test_default_waypoint_indices(make_navigator):
    """defaut waypoint indices should be None when init'ed with empty list or with waypoints"""

    # Initialise navigator without specifying a waypoint list
    navigator = make_navigator()

    assert navigator.current_waypoint_index is None
    assert navigator.target_waypoint_index is None

    # initialise navigatore passing a waypoint list
    navigator = make_navigator(waypoints)
    assert navigator.current_waypoint_index is None
    assert navigator.target_waypoint_index is None

def test_current_waypoint_empty_list(make_navigator):
    """Attempting to get the current waypoint with an empty waypoint list should raise a WaypointListEmptyError"""
    navigator = make_navigator()
    with pytest.raises(navigation.WaypointListEmptyError):
        navigator.current_waypoint

def test_target_waypoint_empty_list(make_navigator):
    """Attempting to get the target waypoint with an empty waypoint list should raise a WaypointListEmptyError"""
    navigator = make_navigator()
    with pytest.raises(navigation.WaypointListEmptyError):
        navigator.target_waypoint

def test_increment_waypoint_index(make_navigator, waypoints):
    """Assert that incrementing waypoint index behaviour is as expected"""
    navigator = make_navigator(waypoints)

    # should be able to call increment_waypoint_index() as many times as there are elements in the waypoint list
    # first call should return first element, as target_waypoint starts at None and increments to 0
    for i, pose in enumerate(waypoints):
        next_waypoint = navigator.increment_waypoint_index()
        assert next_waypoint == pose
        assert navigator.target_waypoint == next_waypoint
        if i == 0:
            assert navigator.current_waypoint == None
        else:
            assert navigator.current_waypoint == waypoints[i - 1]

    # subsequent call to increment_target_index should result in a current waypoint being the last item in the list
    # and the target waypoint should be None
    next_waypoint = navigator.increment_waypoint_index()
    assert next_waypoint == None
    assert navigator.current_waypoint == waypoints[-1]
    assert navigator.target_waypoint == None

    # calling increment_target_index again should now have no effect
    next_waypoint = navigator.increment_waypoint_index()
    assert next_waypoint == None
    assert navigator.current_waypoint == waypoints[-1]
    assert navigator.target_waypoint == None

def test_distance_to_waypoint(make_navigator, waypoints):
    navigator = make_navigator(waypoints)
    navigator.increment_waypoint_index()
    assert navigator.target_waypoint == navigation.Pose(10, 20, 30)
    assert navigator.distance_to_waypoint(navigation.Pose(0, 0, 0)) == pytest.approx(22.36, .01)

def test_distance_waypoint_target_none(make_navigator, waypoints):
    """If the target waypoint is None, the distance to the waypoint will always be 0"""
    navigator = make_navigator(waypoints)
    assert navigator.target_waypoint is None
    assert navigator.distance_to_waypoint(navigation.Pose(1, 2, 3)) == 0