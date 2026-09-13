from __future__ import annotations

from collections.abc import Callable

from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult

Check = Callable[[AgentRecord, dict], CheckResult]
