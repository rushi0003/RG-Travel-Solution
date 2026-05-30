# backend/services/geo_clustering.py
"""
RG Travel Solution - Geo-Clustering Service
STEP 6: Assign employees to groups using geo clustering to reduce route time

Geo Grouping (Nearest/Cluster-Based):
- Sort employees by distance from office
- Build clusters by selecting seed employee and adding nearest neighbors
- Ensure employees in same direction/area are grouped together
- Keep logic stable and reproducible (same input -> same grouping)

Algorithm:
1. Calculate haversine distance from each employee to office/start point
2. For each group:
   a. Pick seed point (furthest unassigned or random)
   b. Add nearest neighbors until group is full
   c. Return group with optimized stop sequence
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmployeePoint:
    """Employee location point for clustering."""
    id: int
    name: str
    mobile: str
    address: str
    lat: float
    lng: float
    distance_from_office: float = 0.0
    bearing_from_office: float = 0.0
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, EmployeePoint):
            return False
        return self.id == other.id


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Args:
        lat1, lng1: First point coordinates
        lat2, lng2: Second point coordinates
    
    Returns:
        Distance in kilometers (rounded to 3 decimals for consistency)
    """
    R = 6371  # Earth radius in kilometers
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    
    # Haversine formula
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2)
    c = 2 * math.asin(math.sqrt(a))
    
    distance_km = R * c
    return round(distance_km, 3)


def cluster_employees_by_proximity(
    employees: List[EmployeePoint],
    group_sizes: List[int],
    office_lat: float,
    office_lng: float,
    method: str = "nearest_neighbor"
) -> List[List[EmployeePoint]]:
    """
    Cluster employees into groups based on geographical proximity.
    
    Args:
        employees: List of EmployeePoint objects
        group_sizes: List of desired group sizes (e.g., [4, 4, 6])
        office_lat, office_lng: Office coordinates (cluster seed)
        method: Clustering method ("nearest_neighbor" or "kmeans_simple")
        
    Returns:
        List of groups, each containing EmployeePoint objects in optimized stop order
        
    Example:
        >>> employees = [
        ...     EmployeePoint(1, "Alice", "9876543210", "Home A", 19.10, 72.80),
        ...     EmployeePoint(2, "Bob", "9876543211", "Home B", 19.15, 72.85),
        ... ]
        >>> group_sizes = [2]
        >>> clusters = cluster_employees_by_proximity(employees, group_sizes, 19.05, 72.75)
        >>> len(clusters)
        1
        >>> len(clusters[0])
        2
    """
    if not employees:
        return []
    
    if not group_sizes:
        return []
    
    total_requested = sum(group_sizes)
    if total_requested != len(employees):
        logger.warning(
            f"Group sizes don't match employee count: {total_requested} vs {len(employees)}"
        )
    
    # Choose clustering method
    if method == "kmeans_simple":
        return _cluster_kmeans_simple(employees, group_sizes, office_lat, office_lng)
    else:
        return _cluster_nearest_neighbor(employees, group_sizes, office_lat, office_lng)


def _cluster_nearest_neighbor(
    employees: List[EmployeePoint],
    group_sizes: List[int],
    office_lat: float,
    office_lng: float
) -> List[List[EmployeePoint]]:
    """
    Cluster using Nearest Neighbor algorithm.
    
    Algorithm:
    1. Start with unassigned employees
    2. For each group:
       a. Pick seed (furthest from office or start)
       b. Add N nearest unassigned neighbors
       c. Calculate optimal stop order (TSP heuristic)
    """
    clusters = []
    unassigned = set(employees)
    
    # Calculate distances from office to all employees (for seed selection)
    distances_from_office = {
        emp: haversine_distance(office_lat, office_lng, emp.lat, emp.lng)
        for emp in employees
    }
    
    for group_size in group_sizes:
        if not unassigned:
            break
        
        # Pick seed: furthest unassigned (typically at periphery, good for routing)
        seed = max(unassigned, key=lambda e: distances_from_office[e])
        
        group = {seed}
        unassigned.remove(seed)
        
        # Add nearest neighbors until group is full
        while len(group) < group_size and unassigned:
            # Find nearest unassigned employee to any member of the group
            nearest_emp = None
            nearest_dist = float('inf')
            
            for candidate in unassigned:
                # Find minimum distance from candidate to any group member
                min_dist = min(
                    haversine_distance(candidate.lat, candidate.lng, grp.lat, grp.lng)
                    for grp in group
                )
                
                if min_dist < nearest_dist:
                    nearest_dist = min_dist
                    nearest_emp = candidate
            
            if nearest_emp:
                group.add(nearest_emp)
                unassigned.remove(nearest_emp)
        
        # Optimize order using simple TSP heuristic (nearest neighbor from office)
        ordered_group = _optimize_stop_order(list(group), office_lat, office_lng)
        clusters.append(ordered_group)
    
    return clusters


def _cluster_kmeans_simple(
    employees: List[EmployeePoint],
    group_sizes: List[int],
    office_lat: float,
    office_lng: float,
    iterations: int = 3
) -> List[List[EmployeePoint]]:
    """
    Simple K-means clustering adapted for fixed group sizes.
    
    Note: This is a simplified K-means that respects group_sizes constraints.
    Not a true K-means but provides good geographical grouping.
    """
    num_clusters = len(group_sizes)
    
    if num_clusters == 1:
        # Single cluster - just optimize the route
        ordered = _optimize_stop_order(employees, office_lat, office_lng)
        return [ordered]
    
    # Initialize cluster centroids around office
    centroids = _initialize_centroids(office_lat, office_lng, num_clusters)
    
    clusters = [[] for _ in range(num_clusters)]
    
    for _ in range(iterations):
        # Clear clusters
        clusters = [[] for _ in range(num_clusters)]
        
        # Assign each employee to nearest centroid
        for emp in employees:
            nearest_cluster = min(
                range(num_clusters),
                key=lambda i: haversine_distance(
                    emp.lat, emp.lng,
                    centroids[i][0], centroids[i][1]
                )
            )
            clusters[nearest_cluster].append(emp)
        
        # Recalculate centroids
        for i, cluster in enumerate(clusters):
            if cluster:
                avg_lat = sum(emp.lat for emp in cluster) / len(cluster)
                avg_lng = sum(emp.lng for emp in cluster) / len(cluster)
                centroids[i] = (avg_lat, avg_lng)
    
    # Rebalance clusters to match group_sizes
    result_clusters = []
    all_employees = []
    
    for cluster in clusters:
        all_employees.extend(cluster)
    
    # Re-cluster using nearest neighbor with fixed sizes
    unassigned = set(all_employees)
    for size in group_sizes:
        if not unassigned:
            break
        
        # Pick seed from unassigned
        seed = list(unassigned)[0]
        group = {seed}
        unassigned.remove(seed)
        
        # Add nearest neighbors
        while len(group) < size and unassigned:
            nearest = min(
                unassigned,
                key=lambda e: min(
                    haversine_distance(e.lat, e.lng, g.lat, g.lng)
                    for g in group
                )
            )
            group.add(nearest)
            unassigned.remove(nearest)
        
        ordered_group = _optimize_stop_order(list(group), office_lat, office_lng)
        result_clusters.append(ordered_group)
    
    return result_clusters


def _optimize_stop_order(
    employees: List[EmployeePoint],
    office_lat: float,
    office_lng: float
) -> List[EmployeePoint]:
    """
    Optimize the order of stops using nearest neighbor TSP heuristic.
    
    Algorithm:
    1. Start at office
    2. Always go to nearest unvisited neighbor
    3. Repeat until all visited
    
    This is O(n^2) but produces reasonable routes for small groups (4-6).
    Deterministic: same input always produces same output.
    """
    if not employees:
        return []
    
    if len(employees) == 1:
        return employees
    
    visited = []
    current_lat, current_lng = office_lat, office_lng
    remaining = set(employees)
    
    while remaining:
        # Find nearest unvisited
        nearest = min(
            remaining,
            key=lambda e: haversine_distance(current_lat, current_lng, e.lat, e.lng)
        )
        visited.append(nearest)
        remaining.remove(nearest)
        current_lat, current_lng = nearest.lat, nearest.lng
    
    return visited


def _initialize_centroids(
    center_lat: float,
    center_lng: float,
    num_clusters: int
) -> List[Tuple[float, float]]:
    """
    Initialize cluster centroids in a circle around center point.
    Creates evenly distributed initial cluster centers.
    """
    centroids = []
    radius = 0.01  # ~1km in lat/lng
    
    for i in range(num_clusters):
        angle = (2 * math.pi * i) / num_clusters
        lat = center_lat + radius * math.sin(angle)
        lng = center_lng + radius * math.cos(angle)
        centroids.append((lat, lng))
    
    return centroids


def calculate_group_distances(
    group: List[EmployeePoint],
    office_lat: float,
    office_lng: float
) -> Dict[str, float]:
    """
    Calculate total route distance metrics for a group.
    
    Returns:
        {
            "office_to_first": float km,
            "inter_stop_total": float km,
            "last_to_office": float km,
            "total_route": float km
        }
    """
    if not group:
        return {
            "office_to_first": 0.0,
            "inter_stop_total": 0.0,
            "last_to_office": 0.0,
            "total_route": 0.0
        }
    
    # Office to first stop
    first_dist = haversine_distance(office_lat, office_lng, group[0].lat, group[0].lng)
    
    # Between stops
    inter_stop_total = 0.0
    for i in range(len(group) - 1):
        dist = haversine_distance(
            group[i].lat, group[i].lng,
            group[i + 1].lat, group[i + 1].lng
        )
        inter_stop_total += dist
    
    # Last stop to office
    last_dist = haversine_distance(group[-1].lat, group[-1].lng, office_lat, office_lng)
    
    total = first_dist + inter_stop_total + last_dist
    
    return {
        "office_to_first": round(first_dist, 2),
        "inter_stop_total": round(inter_stop_total, 2),
        "last_to_office": round(last_dist, 2),
        "total_route": round(total, 2)
    }

    return round(distance_km, 3)


def calculate_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate bearing (direction) from point 1 to point 2.
    
    Returns:
        Bearing in degrees (0-360), where 0 is North
    """
    dlng = math.radians(lng2 - lng1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    
    x = math.sin(dlng) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlng))
    
    bearing = math.degrees(math.atan2(x, y))
    return round((bearing + 360) % 360, 1)  # Normalize to 0-360


def find_nearest_employee(
    seed: EmployeePoint,
    candidates: List[EmployeePoint]
) -> EmployeePoint:
    """
    Find the employee closest to the seed employee.
    
    Args:
        seed: Reference employee
        candidates: List of employees to search
    
    Returns:
        Nearest employee from candidates
    
    Uses ID as tiebreaker for deterministic selection.
    """
    if not candidates:
        return None
    
    min_dist = float('inf')
    nearest = None
    
    for candidate in candidates:
        dist = haversine_distance(
            seed.lat, seed.lng,
            candidate.lat, candidate.lng
        )
        
        # Use ID as tiebreaker for determinism
        if dist < min_dist or (dist == min_dist and (nearest is None or candidate.id < nearest.id)):
            min_dist = dist
            nearest = candidate
    
    return nearest


# Removed shadowed function. The dispatcher cluster_employees_by_proximity at line 77 is the correct one.


def cluster_with_direction_preference(
    employees: List[EmployeePoint],
    group_sizes: List[int],
    office_lat: float,
    office_lng: float
) -> List[List[EmployeePoint]]:
    """
    Advanced clustering with direction (bearing) awareness.
    Groups employees in similar directions together.
    
    This is an enhanced version that considers both distance AND direction.
    """
    # Calculate distances and bearings
    for emp in employees:
        emp.distance_from_office = haversine_distance(
            office_lat, office_lng, emp.lat, emp.lng
        )
        emp.bearing_from_office = calculate_bearing(
            office_lat, office_lng, emp.lat, emp.lng
        )
    
    # Sort by distance (farthest first), then by bearing for same distance
    employees_sorted = sorted(
        employees,
        key=lambda e: (-e.distance_from_office, e.bearing_from_office, e.id)
    )
    
    # Build clusters (same logic as basic clustering)
    groups: List[List[EmployeePoint]] = []
    remaining = list(employees_sorted)
    
    for group_size in group_sizes:
        if not remaining:
            break
        
        seed = remaining.pop(0)
        group = [seed]
        
        while len(group) < group_size and remaining:
            # Find nearest with direction preference
            nearest = _find_nearest_with_direction(seed, remaining, weight_direction=0.3)
            if nearest:
                group.append(nearest)
                remaining.remove(nearest)
                seed = nearest
            else:
                break
        
        groups.append(group)
    
    if remaining and groups:
        groups[-1].extend(remaining)
    
    return groups


def _find_nearest_with_direction(
    seed: EmployeePoint,
    candidates: List[EmployeePoint],
    weight_direction: float = 0.3
) -> EmployeePoint:
    """
    Find nearest employee considering both distance and direction.
    
    Args:
        seed: Reference employee
        candidates: List to search
        weight_direction: How much to weight direction similarity (0-1)
    
    Returns:
        Employee with lowest combined score
    """
    if not candidates:
        return None
    
    min_score = float('inf')
    nearest = None
    
    for candidate in candidates:
        # Distance component
        dist = haversine_distance(seed.lat, seed.lng, candidate.lat, candidate.lng)
        
        # Direction component (bearing difference)
        bearing_diff = abs(seed.bearing_from_office - candidate.bearing_from_office)
        if bearing_diff > 180:
            bearing_diff = 360 - bearing_diff  # Shorter angle
        
        # Combined score: weighted sum
        score = (1 - weight_direction) * dist + weight_direction * (bearing_diff / 180) * dist
        
        if score < min_score or (score == min_score and candidate.id < nearest.id):
            min_score = score
            nearest = candidate
    
    return nearest
