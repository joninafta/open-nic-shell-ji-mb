"""
Coverage collector base class for OpenNIC testbench environment.
Provides functional coverage collection and reporting.
"""

import cocotb
from typing import Any, Optional, Dict, List, Set, Callable
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from .component import Component


class CoverageType(Enum):
    """Types of coverage points."""
    FEATURE = "feature"
    CROSS = "cross"
    TRANSITION = "transition"


@dataclass
class CoveragePoint:
    """Individual coverage point definition."""
    name: str
    coverage_type: CoverageType
    description: str = ""
    target_hits: int = 1
    hits: int = 0
    bins: Dict[str, int] = field(default_factory=dict)
    
    @property
    def coverage_percent(self) -> float:
        """Calculate coverage percentage."""
        if self.coverage_type == CoverageType.FEATURE:
            return 100.0 if self.hits >= self.target_hits else 0.0
        elif self.bins:
            hit_bins = sum(1 for hits in self.bins.values() if hits > 0)
            return (hit_bins / len(self.bins)) * 100.0
        else:
            return 100.0 if self.hits >= self.target_hits else 0.0


@dataclass
class CoverageGroup:
    """Group of related coverage points."""
    name: str
    description: str = ""
    points: Dict[str, CoveragePoint] = field(default_factory=dict)
    
    @property
    def coverage_percent(self) -> float:
        """Calculate group coverage percentage."""
        if not self.points:
            return 100.0
        total_coverage = sum(point.coverage_percent for point in self.points.values())
        return total_coverage / len(self.points)


class Coverage(Component):
    """
    Base coverage collector class.
    Collects and reports functional coverage metrics.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize coverage collector.
        
        Args:
            name: Coverage collector instance name
            config: Optional configuration dictionary
        """
        super().__init__(name, config)
        self._groups: Dict[str, CoverageGroup] = {}
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._enabled = True
        
    def create_group(self, group_name: str, description: str = "") -> CoverageGroup:
        """
        Create a coverage group.
        
        Args:
            group_name: Name of the coverage group
            description: Optional description
            
        Returns:
            Created coverage group
        """
        group = CoverageGroup(group_name, description)
        self._groups[group_name] = group
        self.logger.debug(f"Created coverage group: {group_name}")
        return group
        
    def add_coverage_point(self, group_name: str, point_name: str, 
                          coverage_type: CoverageType, description: str = "",
                          target_hits: int = 1, bins: Optional[List[str]] = None) -> None:
        """
        Add a coverage point to a group.
        
        Args:
            group_name: Name of the coverage group
            point_name: Name of the coverage point
            coverage_type: Type of coverage
            description: Optional description
            target_hits: Target number of hits
            bins: Optional list of bin names for binned coverage
        """
        if group_name not in self._groups:
            self.create_group(group_name)
            
        point = CoveragePoint(
            name=point_name,
            coverage_type=coverage_type,
            description=description,
            target_hits=target_hits
        )
        
        if bins:
            point.bins = {bin_name: 0 for bin_name in bins}
            
        self._groups[group_name].points[point_name] = point
        self.logger.debug(f"Added coverage point: {group_name}.{point_name}")
        
    def hit_coverage_point(self, group_name: str, point_name: str, 
                          bin_name: Optional[str] = None) -> None:
        """
        Register a hit on a coverage point.
        
        Args:
            group_name: Name of the coverage group
            point_name: Name of the coverage point
            bin_name: Optional bin name for binned coverage
        """
        if not self._enabled:
            return
            
        if group_name not in self._groups:
            self.logger.warning(f"Unknown coverage group: {group_name}")
            return
            
        group = self._groups[group_name]
        if point_name not in group.points:
            self.logger.warning(f"Unknown coverage point: {group_name}.{point_name}")
            return
            
        point = group.points[point_name]
        
        if bin_name:
            if bin_name in point.bins:
                point.bins[bin_name] += 1
            else:
                self.logger.warning(f"Unknown bin: {group_name}.{point_name}.{bin_name}")
        else:
            point.hits += 1
            
        # Call registered callbacks
        callback_key = f"{group_name}.{point_name}"
        for callback in self._callbacks[callback_key]:
            try:
                callback(point, bin_name)
            except Exception as e:
                self.logger.error(f"Coverage callback error: {e}")
                
    def add_callback(self, group_name: str, point_name: str, 
                    callback: Callable[[CoveragePoint, Optional[str]], None]) -> None:
        """
        Add callback for coverage point hits.
        
        Args:
            group_name: Name of the coverage group
            point_name: Name of the coverage point
            callback: Function to call on hits
        """
        callback_key = f"{group_name}.{point_name}"
        self._callbacks[callback_key].append(callback)
        
    def enable_coverage(self, enabled: bool = True) -> None:
        """
        Enable or disable coverage collection.
        
        Args:
            enabled: Whether to enable coverage
        """
        self._enabled = enabled
        self.logger.info(f"Coverage collection {'enabled' if enabled else 'disabled'}")
        
    def get_coverage_percent(self, group_name: Optional[str] = None) -> float:
        """
        Get overall coverage percentage.
        
        Args:
            group_name: Optional specific group name
            
        Returns:
            Coverage percentage
        """
        if group_name:
            if group_name in self._groups:
                return self._groups[group_name].coverage_percent
            else:
                return 0.0
        else:
            if not self._groups:
                return 100.0
            total_coverage = sum(group.coverage_percent for group in self._groups.values())
            return total_coverage / len(self._groups)
            
    def report_coverage(self, detailed: bool = True) -> None:
        """
        Report coverage statistics.
        
        Args:
            detailed: Whether to include detailed point-by-point report
        """
        overall_coverage = self.get_coverage_percent()
        self.logger.info(f"=== Coverage Report for {self.name} ===")
        self.logger.info(f"Overall Coverage: {overall_coverage:.1f}%")
        
        if detailed:
            for group_name, group in self._groups.items():
                group_coverage = group.coverage_percent
                self.logger.info(f"\nGroup: {group_name} ({group_coverage:.1f}%)")
                if group.description:
                    self.logger.info(f"  Description: {group.description}")
                    
                for point_name, point in group.points.items():
                    point_coverage = point.coverage_percent
                    self.logger.info(f"  Point: {point_name} ({point_coverage:.1f}%)")
                    
                    if point.bins:
                        for bin_name, hits in point.bins.items():
                            self.logger.info(f"    Bin {bin_name}: {hits} hits")
                    else:
                        self.logger.info(f"    Hits: {point.hits}/{point.target_hits}")
                        
    def export_coverage_data(self) -> Dict[str, Any]:
        """
        Export coverage data for external analysis.
        
        Returns:
            Dictionary containing all coverage data
        """
        data = {
            "overall_coverage": self.get_coverage_percent(),
            "groups": {}
        }
        
        for group_name, group in self._groups.items():
            group_data = {
                "coverage": group.coverage_percent,
                "description": group.description,
                "points": {}
            }
            
            for point_name, point in group.points.items():
                point_data = {
                    "coverage": point.coverage_percent,
                    "type": point.coverage_type.value,
                    "description": point.description,
                    "hits": point.hits,
                    "target_hits": point.target_hits,
                    "bins": point.bins
                }
                group_data["points"][point_name] = point_data
                
            data["groups"][group_name] = group_data
            
        return data
        
    async def start(self) -> None:
        """Start coverage collection."""
        await super().start()
        self.logger.debug(f"Coverage collector {self.name} started")
        
    async def stop(self) -> None:
        """Stop coverage collection and report final statistics."""
        self.report_coverage()
        await super().stop()
