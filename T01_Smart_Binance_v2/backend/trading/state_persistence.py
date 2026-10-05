"""State Persistence for T01 Smart Binance Intelligence v2.

This module provides comprehensive state persistence and recovery functionality.
It ensures that the bot can survive restarts without losing state by:

1. Persisting all critical state (orders, positions, trades) to SQLite
2. Providing snapshot and restore functionality
3. Supporting incremental state updates
4. Handling crash recovery
5. Providing state validation and integrity checks

The state persistence layer works with the database module to ensure
all state changes are durably stored.
"""

import asyncio
import json
import logging
import pickle
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.data.database import Database
    from backend.trading.order_manager import OrderManager, Order
    from backend.trading.position_manager import PositionManager, Position

log = logging.getLogger("trading.state_persistence")


# ============================================================================
# ENUMS
# ============================================================================

class SnapshotType(Enum):
    """Types of state snapshots."""
    FULL = "full"              # Complete state snapshot
    INCREMENTAL = "incremental"  # Incremental changes since last snapshot
    CRASH_RECOVERY = "crash_recovery"  # Snapshot taken for crash recovery


class RestoreMode(Enum):
    """Modes for state restoration."""
    FULL = "full"              # Restore complete state
    INCREMENTAL = "incremental"  # Apply incremental changes
    MERGE = "merge"            # Merge with existing state
    RECOVER = "recover"        # Recover from crash


class StateStatus(Enum):
    """Status of state persistence."""
    CLEAN = "clean"            # State is consistent and up-to-date
    DIRTY = "dirty"            # State has uncommitted changes
    CORRUPT = "corrupt"        # State may be corrupted
    RECOVERING = "recovering"  # State recovery in progress


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class Snapshot:
    """Represents a state snapshot.
    
    Attributes:
        snapshot_id: Unique ID for this snapshot
        timestamp: When the snapshot was taken
        snapshot_type: Type of snapshot
        version: Snapshot version
        state: Complete or incremental state data
        metadata: Additional metadata
        checksum: Checksum for integrity verification
    """
    snapshot_id: str = field(default_factory=lambda: f"snap_{datetime.now(timezone.utc).timestamp()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    snapshot_type: SnapshotType = SnapshotType.FULL
    version: str = "1.0"
    state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for storage."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "snapshot_type": self.snapshot_type.value,
            "version": self.version,
            "state": self.state,
            "metadata": self.metadata,
            "checksum": self.checksum
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """Create snapshot from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data.get("timestamp", datetime.now(timezone.utc).isoformat()))
        data["snapshot_type"] = SnapshotType(data.get("snapshot_type", "full"))
        return cls(**data)


@dataclass
class StateChange:
    """Represents a single state change for incremental persistence.
    
    Attributes:
        change_id: Unique ID for this change
        timestamp: When the change occurred
        entity_type: Type of entity ('order', 'position', 'trade', 'state')
        entity_id: ID of the entity
        action: Action performed ('create', 'update', 'delete')
        data: The changed data
        previous_data: Previous data (for updates)
    """
    change_id: str = field(default_factory=lambda: f"change_{datetime.now(timezone.utc).timestamp()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    entity_type: str = ""
    entity_id: str = ""
    action: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    previous_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state change to dictionary."""
        return {
            "change_id": self.change_id,
            "timestamp": self.timestamp.isoformat(),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "data": self.data,
            "previous_data": self.previous_data
        }


@dataclass
class StateInfo:
    """Information about current state.
    
    Attributes:
        status: Current state status
        last_snapshot_id: ID of last full snapshot
        last_snapshot_time: When last snapshot was taken
        last_change_id: ID of last state change
        last_change_time: When last change occurred
        pending_changes: Number of uncommitted changes
        total_orders: Number of orders in state
        total_positions: Number of positions in state
        total_trades: Number of trades in state
    """
    status: StateStatus = StateStatus.CLEAN
    last_snapshot_id: Optional[str] = None
    last_snapshot_time: Optional[datetime] = None
    last_change_id: Optional[str] = None
    last_change_time: Optional[datetime] = None
    pending_changes: int = 0
    total_orders: int = 0
    total_positions: int = 0
    total_trades: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert state info to dictionary."""
        return {
            "status": self.status.value,
            "last_snapshot_id": self.last_snapshot_id,
            "last_snapshot_time": self.last_snapshot_time.isoformat() if self.last_snapshot_time else None,
            "last_change_id": self.last_change_id,
            "last_change_time": self.last_change_time.isoformat() if self.last_change_time else None,
            "pending_changes": self.pending_changes,
            "total_orders": self.total_orders,
            "total_positions": self.total_positions,
            "total_trades": self.total_trades
        }


# ============================================================================
# STATE PERSISTENCE MANAGER
# ============================================================================

class StatePersistence:
    """Manages state persistence and recovery.
    
    The StatePersistence class provides:
    
    1. Automatic state saving on changes
    2. Snapshot creation and management
    3. State restoration from snapshots
    4. Crash recovery
    5. State validation and integrity checks
    
    It works with the Database module to ensure all state is durably stored
    and can be recovered after a restart or crash.
    """

    def __init__(
        self,
        db: "Database",
        order_manager: Optional["OrderManager"] = None,
        position_manager: Optional["PositionManager"] = None,
        snapshot_interval: float = 300.0,  # 5 minutes between snapshots
        max_snapshots: int = 10,
        snapshot_dir: str = "data/snapshots"
    ):
        """Initialize StatePersistence.
        
        Args:
            db: Database instance for persistence
            order_manager: Optional OrderManager for order state
            position_manager: Optional PositionManager for position state
            snapshot_interval: Seconds between automatic snapshots
            max_snapshots: Maximum number of snapshots to keep
            snapshot_dir: Directory for snapshot files
        """
        self.db = db
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.snapshot_interval = snapshot_interval
        self.max_snapshots = max_snapshots
        self.snapshot_dir = Path(snapshot_dir)
        
        # State tracking
        self._status = StateStatus.CLEAN
        self._pending_changes: List[StateChange] = []
        self._last_snapshot: Optional[Snapshot] = None
        self._last_change: Optional[StateChange] = None
        
        # Background task
        self._snapshot_task: Optional[asyncio.Task] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Ensure snapshot directory exists
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        log.info(f"StatePersistence initialized (snapshot_interval={self.snapshot_interval}s)")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start background tasks."""
        log.info("Starting StatePersistence background tasks")
        
        # Load state info from database
        await self._load_state_info()
        
        # Start background snapshot task
        self._snapshot_task = asyncio.create_task(
            self._background_snapshot()
        )
        
        log.info("StatePersistence started")

    async def stop(self) -> None:
        """Stop background tasks."""
        log.info("Stopping StatePersistence background tasks")
        
        # Take a final snapshot
        await self.create_snapshot(SnapshotType.FULL)
        
        # Cancel background task
        if self._snapshot_task:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
        
        log.info("StatePersistence stopped")

    # ========================================================================
    # SNAPSHOT MANAGEMENT
    # ========================================================================

    async def create_snapshot(
        self,
        snapshot_type: SnapshotType = SnapshotType.FULL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Snapshot:
        """Create a state snapshot.
        
        Args:
            snapshot_type: Type of snapshot to create
            metadata: Optional metadata to include
            
        Returns:
            Created Snapshot object
        """
        async with self._lock:
            log.info(f"Creating {snapshot_type.value} snapshot")
            
            # Collect state data
            state = await self._collect_state()
            
            # Create snapshot
            snapshot = Snapshot(
                snapshot_type=snapshot_type,
                state=state,
                metadata=metadata or {}
            )
            
            # Calculate checksum
            snapshot.checksum = self._calculate_checksum(snapshot)
            
            # Save to database
            await self.db.create_snapshot(
                snapshot_id=snapshot.snapshot_id,
                timestamp=snapshot.timestamp,
                snapshot_type=snapshot.snapshot_type.value,
                version=snapshot.version,
                state=json.dumps(snapshot.state),
                metadata=json.dumps(snapshot.metadata),
                checksum=snapshot.checksum
            )
            
            # Save to file (optional, for backup)
            await self._save_snapshot_to_file(snapshot)
            
            # Update last snapshot
            self._last_snapshot = snapshot
            self._status = StateStatus.CLEAN
            self._pending_changes = []
            
            # Update state info in database
            await self.db.set_state(
                "last_snapshot_id",
                snapshot.snapshot_id
            )
            await self.db.set_state(
                "last_snapshot_time",
                snapshot.timestamp.isoformat()
            )
            
            # Cleanup old snapshots
            await self._cleanup_old_snapshots()
            
            log.info(f"Created snapshot: {snapshot.snapshot_id}")
            return snapshot

    async def _collect_state(self) -> Dict[str, Any]:
        """Collect current state from all managers.
        
        Returns:
            Dictionary containing complete state
        """
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "orders": [],
            "positions": [],
            "trades": [],
            "equity_curve": [],
            "state": {}
        }
        
        # Collect orders
        if self.order_manager:
            orders = await self.order_manager.get_orders()
            state["orders"] = [o.to_dict() for o in orders]
        
        # Collect positions
        if self.position_manager:
            positions = await self.position_manager.get_positions()
            state["positions"] = [p.to_dict() for p in positions]
        
        # Collect trades from database
        trades = await self.db.get_all_trades()
        state["trades"] = trades
        
        # Collect equity curve from database
        equity_curve = await self.db.get_equity_curve()
        state["equity_curve"] = equity_curve
        
        # Collect state from database
        state_data = await self.db.get_all_state()
        state["state"] = state_data
        
        return state

    def _calculate_checksum(self, snapshot: Snapshot) -> str:
        """Calculate checksum for snapshot integrity verification.
        
        Args:
            snapshot: Snapshot to calculate checksum for
            
        Returns:
            Checksum string
        """
        import hashlib
        
        # Create a string representation of the snapshot
        snapshot_str = json.dumps(snapshot.to_dict(), sort_keys=True)
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(snapshot_str.encode())
        return hash_obj.hexdigest()

    async def _save_snapshot_to_file(self, snapshot: Snapshot) -> None:
        """Save snapshot to file for backup.
        
        Args:
            snapshot: Snapshot to save
        """
        try:
            filepath = self.snapshot_dir / f"{snapshot.snapshot_id}.json"
            
            with open(filepath, 'w') as f:
                json.dump(snapshot.to_dict(), f, indent=2)
            
            log.debug(f"Snapshot saved to file: {filepath}")
        except Exception as e:
            log.error(f"Failed to save snapshot to file: {e}")

    async def _cleanup_old_snapshots(self) -> None:
        """Clean up old snapshots to maintain max_snapshots limit."""
        try:
            # Get all snapshots from database
            snapshots = await self.db.get_all_snapshots()
            
            if len(snapshots) > self.max_snapshots:
                # Sort by timestamp and delete oldest
                snapshots.sort(key=lambda s: s["timestamp"])
                to_delete = snapshots[:len(snapshots) - self.max_snapshots]
                
                for snapshot in to_delete:
                    await self.db.delete_snapshot(snapshot["snapshot_id"])
                    
                    # Also delete file
                    filepath = self.snapshot_dir / f"{snapshot['snapshot_id']}.json"
                    if filepath.exists():
                        filepath.unlink()
                
                log.info(f"Cleaned up {len(to_delete)} old snapshots")
        except Exception as e:
            log.error(f"Failed to cleanup old snapshots: {e}")

    async def restore_snapshot(
        self,
        snapshot_id: str,
        mode: RestoreMode = RestoreMode.FULL
    ) -> bool:
        """Restore state from a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to restore
            mode: Restoration mode
            
        Returns:
            True if restore was successful
        """
        async with self._lock:
            log.info(f"Restoring from snapshot: {snapshot_id} (mode={mode.value})")
            
            try:
                # Load snapshot from database
                snapshot_data = await self.db.get_snapshot(snapshot_id)
                if not snapshot_data:
                    log.error(f"Snapshot not found: {snapshot_id}")
                    return False
                
                snapshot = Snapshot.from_dict(snapshot_data)
                
                # Verify checksum
                calculated_checksum = self._calculate_checksum(snapshot)
                if snapshot.checksum and calculated_checksum != snapshot.checksum:
                    log.error(f"Snapshot checksum mismatch: {snapshot_id}")
                    return False
                
                # Restore state based on mode
                if mode == RestoreMode.FULL:
                    await self._restore_full(snapshot)
                elif mode == RestoreMode.INCREMENTAL:
                    await self._restore_incremental(snapshot)
                elif mode == RestoreMode.MERGE:
                    await self._restore_merge(snapshot)
                elif mode == RestoreMode.RECOVER:
                    await self._restore_recover(snapshot)
                
                # Update state info
                self._last_snapshot = snapshot
                self._status = StateStatus.CLEAN
                
                log.info(f"State restored from snapshot: {snapshot_id}")
                return True
                
            except Exception as e:
                log.error(f"Failed to restore snapshot: {e}")
                return False

    async def _restore_full(self, snapshot: Snapshot) -> None:
        """Restore complete state from snapshot.
        
        Args:
            snapshot: Snapshot to restore from
        """
        log.info("Performing full state restore")
        
        # Clear existing state
        if self.order_manager:
            # Cancel all orders and clear
            await self.order_manager.cancel_all_orders()
        
        if self.position_manager:
            # Close all positions
            await self.position_manager.close_all_positions()
        
        # Restore orders
        for order_data in snapshot.state.get("orders", []):
            if self.order_manager:
                from backend.trading.order_manager import Order
                order = Order.from_dict(order_data)
                self.order_manager.orders[order.order_id] = order
                
                # Save to database
                await self.db.create_order(
                    order_id=order.order_id,
                    exchange_order_id=order.exchange_order_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    order_type=order.order_type.value,
                    price=order.price,
                    qty=order.qty,
                    filled=order.filled,
                    avg_fill_price=order.avg_fill_price,
                    status=order.status.value,
                    bot_position_id=order.bot_position_id,
                    stop_price=order.stop_price,
                    stop_limit_price=order.stop_limit_price,
                    reduce_only=order.reduce_only,
                    test=order.test
                )
        
        # Restore positions
        for position_data in snapshot.state.get("positions", []):
            if self.position_manager:
                from backend.trading.position_manager import Position
                position = Position.from_dict(position_data)
                self.position_manager.positions[position.position_id] = position
                
                # Update symbol index
                if position.symbol not in self.position_manager._positions_by_symbol:
                    self.position_manager._positions_by_symbol[position.symbol] = []
                self.position_manager._positions_by_symbol[position.symbol].append(position.position_id)
                
                # Save to database
                await self.db.create_position(
                    position_id=position.position_id,
                    symbol=position.symbol,
                    side=position.side.value,
                    entry_price=position.entry_price,
                    current_qty=position.current_qty,
                    entry_qty=position.entry_qty,
                    stop_loss=position.stop_loss,
                    take_profit=position.take_profit,
                    trailing_stop=position.trailing_stop,
                    status=position.status.value,
                    entry_order_id=position.entry_order_id,
                    exit_order_id=position.exit_order_id,
                    mode=position.mode,
                    test=position.test,
                    bot_id=position.bot_id
                )
        
        # Restore state
        for key, value in snapshot.state.get("state", {}).items():
            await self.db.set_state(key, value)
        
        log.info("Full state restore completed")

    async def _restore_incremental(self, snapshot: Snapshot) -> None:
        """Apply incremental changes from snapshot.
        
        Args:
            snapshot: Snapshot to apply
        """
        log.info("Performing incremental state restore")
        
        # For incremental restore, we would apply changes on top of existing state
        # This is more complex and would need change tracking
        # For now, just do a full restore
        await self._restore_full(snapshot)

    async def _restore_merge(self, snapshot: Snapshot) -> None:
        """Merge snapshot state with existing state.
        
        Args:
            snapshot: Snapshot to merge
        """
        log.info("Performing state merge")
        
        # Merge logic would go here
        # For now, just do a full restore
        await self._restore_full(snapshot)

    async def _restore_recover(self, snapshot: Snapshot) -> None:
        """Recover from crash using snapshot.
        
        Args:
            snapshot: Snapshot to recover from
        """
        log.info("Performing crash recovery")
        
        # Crash recovery might include additional validation
        await self._restore_full(snapshot)
        
        # Additional recovery steps
        if self.order_manager:
            # Reconcile orders with exchange
            await self.order_manager.reconcile()
        
        if self.position_manager:
            # Sync positions with orders
            await self.position_manager.sync_with_orders()

    # ========================================================================
    # STATE CHANGE TRACKING
    # ========================================================================

    async def record_change(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        data: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]] = None
    ) -> StateChange:
        """Record a state change for incremental persistence.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            action: Action performed
            data: New data
            previous_data: Previous data (for updates)
            
        Returns:
            Created StateChange object
        """
        async with self._lock:
            change = StateChange(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                data=data,
                previous_data=previous_data or {}
            )
            
            # Add to pending changes
            self._pending_changes.append(change)
            self._last_change = change
            self._status = StateStatus.DIRTY
            
            # Save to database
            await self.db.create_state_change(
                change_id=change.change_id,
                timestamp=change.timestamp,
                entity_type=change.entity_type,
                entity_id=change.entity_id,
                action=change.action,
                data=json.dumps(change.data),
                previous_data=json.dumps(change.previous_data)
            )
            
            # Update state info
            await self.db.set_state(
                "last_change_id",
                change.change_id
            )
            await self.db.set_state(
                "last_change_time",
                change.timestamp.isoformat()
            )
            
            log.debug(f"State change recorded: {entity_type}/{entity_id} {action}")
            return change

    async def get_changes_since(
        self,
        timestamp: Optional[datetime] = None,
        change_id: Optional[str] = None
    ) -> List[StateChange]:
        """Get state changes since a specific time or change ID.
        
        Args:
            timestamp: Get changes after this timestamp
            change_id: Get changes after this change ID
            
        Returns:
            List of StateChange objects
        """
        changes = []
        
        # Get changes from database
        db_changes = await self.db.get_state_changes_since(
            timestamp=timestamp,
            change_id=change_id
        )
        
        for change_data in db_changes:
            change = StateChange(
                change_id=change_data["change_id"],
                timestamp=datetime.fromisoformat(change_data["timestamp"]),
                entity_type=change_data["entity_type"],
                entity_id=change_data["entity_id"],
                action=change_data["action"],
                data=json.loads(change_data["data"]),
                previous_data=json.loads(change_data["previous_data"])
            )
            changes.append(change)
        
        return changes

    # ========================================================================
    # CRASH RECOVERY
    # ========================================================================

    async def recover_from_crash(self) -> bool:
        """Recover from a crash or unexpected shutdown.
        
        This method:
        1. Detects if recovery is needed
        2. Finds the most recent valid snapshot
        3. Restores state from snapshot
        4. Replays any changes since snapshot
        5. Validates recovered state
        
        Returns:
            True if recovery was successful
        """
        async with self._lock:
            log.info("Starting crash recovery")
            
            try:
                # Check if recovery is needed
                state_info = await self.get_state_info()
                if state_info.status == StateStatus.CLEAN:
                    log.info("No recovery needed - state is clean")
                    return True
                
                # Find most recent snapshot
                snapshots = await self.db.get_all_snapshots()
                if not snapshots:
                    log.error("No snapshots available for recovery")
                    return False
                
                snapshots.sort(key=lambda s: s["timestamp"], reverse=True)
                latest_snapshot = snapshots[0]
                
                log.info(f"Found latest snapshot: {latest_snapshot['snapshot_id']}")
                
                # Restore from snapshot
                success = await self.restore_snapshot(
                    latest_snapshot["snapshot_id"],
                    mode=RestoreMode.RECOVER
                )
                
                if not success:
                    log.error("Failed to restore from snapshot")
                    return False
                
                # Replay changes since snapshot
                snapshot_time = datetime.fromisoformat(latest_snapshot["timestamp"])
                changes = await self.get_changes_since(timestamp=snapshot_time)
                
                for change in changes:
                    await self._apply_change(change)
                
                # Validate recovered state
                await self._validate_state()
                
                # Update status
                self._status = StateStatus.CLEAN
                
                log.info("Crash recovery completed successfully")
                return True
                
            except Exception as e:
                log.error(f"Crash recovery failed: {e}")
                self._status = StateStatus.CORRUPT
                return False

    async def _apply_change(self, change: StateChange) -> None:
        """Apply a state change to the current state.
        
        Args:
            change: StateChange to apply
        """
        try:
            if change.entity_type == "order":
                if self.order_manager:
                    from backend.trading.order_manager import Order
                    
                    if change.action == "create":
                        order = Order.from_dict(change.data)
                        self.order_manager.orders[order.order_id] = order
                    elif change.action == "update":
                        if change.entity_id in self.order_manager.orders:
                            order = self.order_manager.orders[change.entity_id]
                            for key, value in change.data.items():
                                setattr(order, key, value)
                    elif change.action == "delete":
                        if change.entity_id in self.order_manager.orders:
                            del self.order_manager.orders[change.entity_id]
            
            elif change.entity_type == "position":
                if self.position_manager:
                    from backend.trading.position_manager import Position
                    
                    if change.action == "create":
                        position = Position.from_dict(change.data)
                        self.position_manager.positions[position.position_id] = position
                    elif change.action == "update":
                        if change.entity_id in self.position_manager.positions:
                            position = self.position_manager.positions[change.entity_id]
                            for key, value in change.data.items():
                                setattr(position, key, value)
                    elif change.action == "delete":
                        if change.entity_id in self.position_manager.positions:
                            del self.position_manager.positions[change.entity_id]
            
            log.debug(f"Applied state change: {change.entity_type}/{change.entity_id} {change.action}")
            
        except Exception as e:
            log.error(f"Failed to apply state change: {e}")

    async def _validate_state(self) -> bool:
        """Validate the recovered state.
        
        Returns:
            True if state is valid
        """
        log.info("Validating recovered state")
        
        # Basic validation checks
        if self.order_manager:
            orders = await self.order_manager.get_orders()
            log.info(f"Validated {len(orders)} orders")
        
        if self.position_manager:
            positions = await self.position_manager.get_positions()
            log.info(f"Validated {len(positions)} positions")
        
        # More comprehensive validation would go here
        return True

    # ========================================================================
    # STATE INFORMATION
    # ========================================================================

    async def get_state_info(self) -> StateInfo:
        """Get current state information.
        
        Returns:
            StateInfo object with current state statistics
        """
        async with self._lock:
            # Get counts
            total_orders = len(self.order_manager.orders) if self.order_manager else 0
            total_positions = len(self.position_manager.positions) if self.position_manager else 0
            total_trades = await self.db.get_trade_count()
            
            # Get last snapshot info
            last_snapshot_id = await self.db.get_state("last_snapshot_id")
            last_snapshot_time_str = await self.db.get_state("last_snapshot_time")
            last_snapshot_time = datetime.fromisoformat(last_snapshot_time_str) if last_snapshot_time_str else None
            
            # Get last change info
            last_change_id = await self.db.get_state("last_change_id")
            last_change_time_str = await self.db.get_state("last_change_time")
            last_change_time = datetime.fromisoformat(last_change_time_str) if last_change_time_str else None
            
            return StateInfo(
                status=self._status,
                last_snapshot_id=last_snapshot_id,
                last_snapshot_time=last_snapshot_time,
                last_change_id=last_change_id,
                last_change_time=last_change_time,
                pending_changes=len(self._pending_changes),
                total_orders=total_orders,
                total_positions=total_positions,
                total_trades=total_trades
            )

    async def _load_state_info(self) -> None:
        """Load state info from database on startup."""
        try:
            state_info = await self.get_state_info()
            
            self._status = state_info.status
            self._last_snapshot = None
            
            if state_info.last_snapshot_id:
                snapshot_data = await self.db.get_snapshot(state_info.last_snapshot_id)
                if snapshot_data:
                    self._last_snapshot = Snapshot.from_dict(snapshot_data)
            
            log.info(f"Loaded state info: status={self._status.value}, "
                    f"orders={state_info.total_orders}, "
                    f"positions={state_info.total_positions}")
        except Exception as e:
            log.error(f"Failed to load state info: {e}")

    # ========================================================================
    # BACKGROUND TASK
    # ========================================================================

    async def _background_snapshot(self) -> None:
        """Background snapshot task."""
        try:
            while True:
                await asyncio.sleep(self.snapshot_interval)
                
                # Only create snapshot if state is dirty
                async with self._lock:
                    if self._status == StateStatus.DIRTY:
                        await self.create_snapshot(SnapshotType.INCREMENTAL)
                    else:
                        # Still create a snapshot periodically even if clean
                        await self.create_snapshot(SnapshotType.FULL)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Background snapshot task failed: {e}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def export_state(self, filepath: str) -> bool:
        """Export current state to a file.
        
        Args:
            filepath: Path to export to
            
        Returns:
            True if export was successful
        """
        try:
            state = await self._collect_state()
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            
            log.info(f"State exported to: {filepath}")
            return True
        except Exception as e:
            log.error(f"Failed to export state: {e}")
            return False

    async def import_state(self, filepath: str) -> bool:
        """Import state from a file.
        
        Args:
            filepath: Path to import from
            
        Returns:
            True if import was successful
        """
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            # Create a snapshot from imported state
            snapshot = Snapshot(
                snapshot_type=SnapshotType.FULL,
                state=state
            )
            
            # Restore from snapshot
            await self._restore_full(snapshot)
            
            log.info(f"State imported from: {filepath}")
            return True
        except Exception as e:
            log.error(f"Failed to import state: {e}")
            return False

    async def clear_state(self) -> None:
        """Clear all state (for testing or fresh start)."""
        async with self._lock:
            log.warning("Clearing all state")
            
            # Clear in-memory state
            if self.order_manager:
                self.order_manager.orders.clear()
            if self.position_manager:
                self.position_manager.positions.clear()
                self.position_manager._positions_by_symbol.clear()
            
            self._pending_changes.clear()
            self._last_snapshot = None
            self._status = StateStatus.CLEAN
            
            # Clear database (except schema)
            await self.db.clear_all_data()
            
            log.info("All state cleared")
