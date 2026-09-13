"""Composition root — the only layer allowed to see both the kernel and the fleet.

Per ADR-0001 the kernel never imports an agent; this package does the wiring instead,
registering each agent's thin, read-only bus adapter into the MessageBus. The adapters
are duck-typed over the bus Message (they read `.type` / `.payload` only), so the agents
never import the kernel — downward-only imports hold.
"""
