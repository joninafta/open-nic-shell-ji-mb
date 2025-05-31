"""
Base component class for all verification components.
Provides common functionality like logging, start/stop methods, and test failure handling.
"""

import logging
import cocotb
from abc import ABC, abstractmethod


class Component(ABC):
    """
    Abstract base class for all verification components.
    
    Provides:
    - Structured logging with component names
    - start() and stop() lifecycle management
    - Test failure handling utilities
    - Common configuration access
    """
    
    def __init__(self, name: str, config=None):
        """
        Initialize component with name and optional configuration.
        
        Args:
            name: Component instance name for logging
            config: Configuration object (optional)
        """
        self.name = name
        self.config = config
        self._started = False
        
        # Set up logging with component name
        self.log = logging.getLogger(f"tb.{self.__class__.__name__}.{name}")
        self.log.setLevel(logging.DEBUG)
        
        # Create formatter if not already configured
        if not self.log.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'[%(asctime)s] %(levelname)-8s | {name} | %(message)s',
                datefmt='%H:%M:%S.%f'
            )
            handler.setFormatter(formatter)
            self.log.addHandler(handler)
    
    async def start(self):
        """Start the component. Override in subclasses for specific startup behavior."""
        if self._started:
            self.log.warning(f"Component {self.name} already started")
            return
            
        self.log.info(f"Starting {self.__class__.__name__}")
        await self._start_impl()
        self._started = True
        self.log.info(f"Started {self.__class__.__name__}")
    
    async def stop(self):
        """Stop the component. Override in subclasses for specific shutdown behavior."""
        if not self._started:
            self.log.warning(f"Component {self.name} not started")
            return
            
        self.log.info(f"Stopping {self.__class__.__name__}")
        await self._stop_impl()
        self._started = False
        self.log.info(f"Stopped {self.__class__.__name__}")
    
    @abstractmethod
    async def _start_impl(self):
        """Implementation-specific start behavior. Must be implemented by subclasses."""
        pass
    
    async def _stop_impl(self):
        """Implementation-specific stop behavior. Override if needed."""
        pass
    
    def raise_test_failure(self, message: str):
        """
        Raise a test failure with proper logging.
        
        Args:
            message: Failure description
        """
        self.log.error(f"TEST FAILURE: {message}")
        raise AssertionError(f"{self.name}: {message}")
    
    @property
    def is_started(self) -> bool:
        """Check if component is started."""
        return self._started
