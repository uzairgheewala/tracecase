from __future__ import annotations
import contextlib, contextvars, json, threading, uuid
from collections.abc import Iterator
from typing import Protocol
from datetime import datetime, timezone
from pathlib import Path
from .models import EffectRecord, SDKContext, SDKEvent, SDKEventKind

class EventSink(Protocol):
    def emit(self,event:SDKEvent)->None: ...

class InMemorySink:
    def __init__(self): self._events=[]; self._lock=threading.Lock()
    def emit(self,event):
        with self._lock: self._events.append(event)
    @property
    def events(self): return tuple(self._events)

class JsonlSink:
    def __init__(self,path:Path): self.path=path; path.parent.mkdir(parents=True,exist_ok=True); self._lock=threading.Lock()
    def emit(self,event):
        with self._lock, self.path.open("a",encoding="utf-8") as handle: handle.write(event.model_dump_json(exclude_none=True)+"\n")

_current_context: contextvars.ContextVar[SDKContext]=contextvars.ContextVar("tracecase_context",default=SDKContext())
_current_event: contextvars.ContextVar[str|None]=contextvars.ContextVar("tracecase_parent_event",default=None)

class TracecaseSDK:
    def __init__(self,component:str,sink:EventSink): self.component=component; self.sink=sink
    @contextlib.contextmanager
    def bind_context(self,**values)->Iterator[SDKContext]:
        merged=self.context().model_copy(update=values); token=_current_context.set(merged)
        try: yield merged
        finally: _current_context.reset(token)
    def context(self): return _current_context.get()
    def emit(self,kind:SDKEventKind,operation:str,*,attributes=None,sensitivity=None,parent_event_id=None,event_id=None):
        event=SDKEvent(event_id=event_id or f"event.{uuid.uuid4().hex}",kind=kind,timestamp=datetime.now(timezone.utc),component=self.component,operation=operation,context=self.context(),parent_event_id=parent_event_id if parent_event_id is not None else _current_event.get(),attributes=attributes or {},sensitivity=sensitivity or set()); self.sink.emit(event); return event
    @contextlib.contextmanager
    def operation(self,operation:str,*,attributes=None)->Iterator[SDKEvent]:
        start=self.emit(SDKEventKind.OPERATION_START,operation,attributes=attributes); token=_current_event.set(start.event_id)
        try:
            yield start
        except Exception as exc:
            self.emit(SDKEventKind.ERROR,operation,attributes={"exception_type":type(exc).__name__,"message":str(exc)})
            self.emit(SDKEventKind.OPERATION_END,operation,attributes={"status":"error"}); raise
        else: self.emit(SDKEventKind.OPERATION_END,operation,attributes={"status":"ok"})
        finally: _current_event.reset(token)
    def domain_event(self,name:str,**attributes): return self.emit(SDKEventKind.DOMAIN_EVENT,name,attributes=attributes)
    def effect(self,record:EffectRecord): return self.emit(SDKEventKind.EFFECT,record.operation,attributes=record.model_dump(mode="json"))
