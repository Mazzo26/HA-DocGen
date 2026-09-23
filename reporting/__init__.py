"""Immutable reporting models for HA-DocGen.

``Report``, ``ReportSection`` and ``ReportMetadata`` are pure
structural representations. ``Severity`` classifies section severity.
``HomeAssistantInventory`` projects parsed Home Assistant objects from
an ``AnalysisModel``. Concrete generators aggregate existing analysis.
No Home Assistant write coupling.
"""

from __future__ import annotations

from .architecture_generator import ArchitectureReportGenerator
from .configuration_generator import ConfigurationReportGenerator
from .console_renderer import ConsoleRenderer
from .dependency_generator import DependencyReportGenerator
from .documentation_index_generator import DocumentationIndexReportGenerator
from .health_generator import HealthReportGenerator
from .home_assistant_inventory import DiscoveredFile, HomeAssistantInventory
from .home_assistant_inventory_generator import HomeAssistantInventoryGenerator
from .inventory_generator import InventoryReportGenerator
from .json_renderer import JsonRenderer
from .markdown_renderer import MarkdownRenderer
from .models import Report, ReportMetadata, ReportSection, Severity
from .performance_generator import PerformanceReportGenerator

__all__ = [
    "ArchitectureReportGenerator",
    "ConfigurationReportGenerator",
    "ConsoleRenderer",
    "DependencyReportGenerator",
    "DiscoveredFile",
    "DocumentationIndexReportGenerator",
    "HealthReportGenerator",
    "HomeAssistantInventory",
    "HomeAssistantInventoryGenerator",
    "InventoryReportGenerator",
    "JsonRenderer",
    "MarkdownRenderer",
    "PerformanceReportGenerator",
    "Report",
    "ReportMetadata",
    "ReportSection",
    "Severity",
]
