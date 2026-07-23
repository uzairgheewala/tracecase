from __future__ import annotations
from collections.abc import Sequence
from typing import Protocol
from tracecase_model import ExecutionCase

class AdapterPlugin(Protocol):
    plugin_id: str; plugin_version: str
    def normalize(self, records: Sequence[object]) -> ExecutionCase: ...

class AnalyzerPlugin(Protocol):
    plugin_id: str; plugin_version: str
    def analyze(self, case: ExecutionCase) -> Sequence[object]: ...

class PluginRegistry:
    def __init__(self): self._plugins={}
    def register(self,plugin):
        key=(plugin.plugin_id,plugin.plugin_version)
        if key in self._plugins: raise ValueError(f"duplicate plugin {key}")
        self._plugins[key]=plugin
    def list(self): return tuple(self._plugins.values())
    def get(self,plugin_id,plugin_version): return self._plugins[(plugin_id,plugin_version)]
