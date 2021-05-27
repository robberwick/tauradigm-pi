
from math import hypot
from typing import List, Optional


class Pose():
    def __init__(self, x: float=0, y: float=0, heading: float=0) -> None:
        self.x = x
        self.y = y
        self.heading = heading

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.x == other.x and self.y == other.y and self.heading == other.heading
        return False

    def __str__(self) -> str:
        return f"Pose, x: {self.x}, y: {self.y}, heading: {self.heading}"

    def __repr__(self) -> str:
        return f"Pose({self.x!r}, {self.y!r}, {self.heading!r})"

Waypoints = List[Pose]

class WaypointError(Exception):
    pass

class WaypointListEmptyError(WaypointError):
    pass

class WaypointNotFoundError(WaypointError):
    pass

class WaypointNotSetError(WaypointError):
    pass

class Navigator():
    def __init__(self, waypoints: Optional[Waypoints]=None) -> None:
        self.waypoints = waypoints if waypoints is not None else []
        self.current_waypoint_index: Optional[int] = None
        self.target_waypoint_index: Optional[int] = None

    def _get_waypoint_at_index(self, index: Optional[int]) -> Pose:
        # raise an exception if the list is empty
        if len(self.waypoints) is 0:
            raise WaypointListEmptyError

        # raise an exception if the given index is None
        if index is None:
            raise WaypointNotSetError("Could not get waypoint - index is None")
        try:
             return self.waypoints[index]
        except IndexError:
            raise WaypointNotFoundError(f'Could not get waypoint at {index}')


    @property
    def current_waypoint(self) -> Optional[Pose]:
        try:
            return self._get_waypoint_at_index(self.current_waypoint_index)
        except WaypointNotSetError:
            return None

    @property
    def target_waypoint(self):
        try:
            return self._get_waypoint_at_index(self.target_waypoint_index)
        except WaypointNotSetError:
            return None

    def increment_waypoint_index(self) -> Pose:
        """Increment the waypoint index to the next available value - returns waypoint if successful"""
        # can't increment the waypoint if the list is not set
        if len(self.waypoints) == 0:
            raise WaypointListEmptyError

        # if both target and current indexes are None then we're at the start - attempt to get the first waypoint
        if self.target_waypoint_index is None and self.current_waypoint_index is None:
            tmp_target_waypoint_index = 0
        # if the target is None, but current is not, then we've exhausted the list. Make no changes.
        elif self.target_waypoint_index is None:
            return None
        # otherwise just try to get the next element in the list
        else:
            tmp_target_waypoint_index = self.target_waypoint_index +  1 if self.target_waypoint_index is not None else 0

        # Attempt to get the waypoint at that index. If successful, update the target_waypoint_index
        # and current_waypoint_index properties or raise an appropriate exception
        try:
            next_waypoint = self._get_waypoint_at_index(tmp_target_waypoint_index)
            self.current_waypoint_index = self.target_waypoint_index
            self.target_waypoint_index = tmp_target_waypoint_index
            return next_waypoint
        except WaypointNotFoundError:
            # if the attempted waypoint index is greater or equal to the length of the waypoint list,
            # then update the current waypoint, and set the target waypoint to None
            if tmp_target_waypoint_index >= len(self.waypoints):
                self.current_waypoint_index = self.target_waypoint_index
                self.target_waypoint_index = None
        except WaypointError:
            raise

    def distance_to_waypoint(self, current_pos: Pose):
        """returns distance 'as the crow flies' to the target pose"""
        # hypotenuse of dx, dy triangle gives distance, using h^2=x^2+y^2
        if self.target_waypoint is None:
            return 0
        return hypot(self.target_waypoint.x - current_pos.x, self.target_waypoint.y - current_pos.y)