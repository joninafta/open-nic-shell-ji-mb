"""
Configuration classes for OpenNIC Shell verification environment.
Uses dataclasses for type-safe, frozen configuration objects.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import yaml
import json


@dataclass(frozen=True)
class FilterRule:
    """Configuration for a single packet filter rule."""
    ipv4_addr: int = 0  # IPv4 address to match (0 = don't care)
    ipv6_addr: int = 0  # IPv6 address to match (0 = don't care) - simplified as int for now
    src_port: int = 0   # Source port to match (0 = don't care)
    dst_port: int = 0   # Destination port to match (0 = don't care)
    enabled: bool = True


@dataclass(frozen=True)
class ClockConfig:
    """Clock configuration parameters."""
    frequency_mhz: float = 250.0
    period_ns: float = field(init=False)
    
    def __post_init__(self):
        # Calculate period from frequency
        object.__setattr__(self, 'period_ns', 1000.0 / self.frequency_mhz)


@dataclass(frozen=True)
class FilterRxPipelineConfig:
    """Configuration specific to filter_rx_pipeline module."""
    num_rules: int = 2
    filter_rules: List[FilterRule] = field(default_factory=lambda: [
        FilterRule(ipv4_addr=0xC0A80101, dst_port=80),  # 192.168.1.1:80
        FilterRule(ipv4_addr=0xC0A80102, dst_port=443)  # 192.168.1.2:443
    ])
    enable_debug: bool = True
    packet_timeout_cycles: int = 1000


@dataclass(frozen=True)
class TestConfig:
    """Test-specific configuration."""
    test_name: str = "filter_rx_pipeline_basic"
    seed: Optional[int] = None
    waves_enable: bool = True
    coverage_enable: bool = True
    timeout_ns: int = 100_000_000  # 100ms default timeout


@dataclass(frozen=True)
class BoardConfig:
    """Board-specific configuration."""
    name: str = "simulation"
    clock_config: ClockConfig = field(default_factory=ClockConfig)
    defines: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Config:
    """
    Top-level configuration object.
    Combines all configuration aspects for the verification environment.
    """
    board: BoardConfig = field(default_factory=BoardConfig)
    test: TestConfig = field(default_factory=TestConfig)
    filter_rx_pipeline: FilterRxPipelineConfig = field(default_factory=FilterRxPipelineConfig)
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Config':
        """Load configuration from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_json(cls, json_path: str) -> 'Config':
        """Load configuration from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        # This is a simplified implementation - in practice you'd want
        # more sophisticated nested dataclass creation
        board_data = data.get('board', {})
        test_data = data.get('test', {})
        filter_data = data.get('filter_rx_pipeline', {})
        
        return cls(
            board=BoardConfig(**board_data),
            test=TestConfig(**test_data),
            filter_rx_pipeline=FilterRxPipelineConfig(**filter_data)
        )
