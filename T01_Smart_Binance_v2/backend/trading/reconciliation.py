"""Reconciliation Engine for T01 Smart Binance Intelligence v2.

This module provides comprehensive state reconciliation between the bot and the exchange.
It ensures that the bot's internal state (orders, positions, trades) matches the
exchange state, preventing state loss on restarts and handling edge cases.

Features:
- Full state synchronization on startup
- Periodic reconciliation during operation
- Discrepancy detection and resolution
- State persistence and recovery
- Exchange API error handling with retry logic
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set, TYPE_CHECKING

import ccxt.async_support as ccxt

if TYPE_CHECKING:
    from backend.trading.order_manager import OrderManager, Order, OrderSide, OrderType, OrderStatus
    from backend.trading.position_manager import PositionManager, Position, PositionSide, PositionStatus
    from backend.data.database import Database

log = logging.getLogger("trading.reconciliation")


# ============================================================================
# ENUMS
# ============================================================================

class ReconciliationStatus(Enum):
    """Status of reconciliation process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscrepancyType(Enum):
    """Types of discrepancies that can be detected."""
    MISSING_ORDER = "missing_order"           # Order exists locally but not on exchange
    ORPHANED_ORDER = "orphaned_order"         # Order exists on exchange but not locally
    STATUS_MISMATCH = "status_mismatch"       # Order/position status differs
    QUANTITY_MISMATCH = "quantity_mismatch"   # Position quantity differs
    PRICE_MISMATCH = "price_mismatch"         # Order/position price differs
    MISSING_POSITION = "missing_position"     # Position exists locally but not on exchange
    ORPHANED_POSITION = "orphaned_position"   # Position exists on exchange but not locally


class ResolutionAction(Enum):
    """Actions taken to resolve discrepancies."""
    NONE = "none"
    CREATE_LOCAL = "create_local"             # Create local record for orphaned exchange item
    CANCEL_EXCHANGE = "cancel_exchange"       # Cancel order on exchange
    UPDATE_LOCAL = "update_local"             # Update local state to match exchange
    UPDATE_EXCHANGE = "update_exchange"       # Update exchange (rare)
    IGNORE = "ignore"                         # Ignore discrepancy (manual resolution needed)


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class Discrepancy:
    """Represents a detected discrepancy between local and exchange state.
    
    Attributes:
        discrepancy_id: Unique ID for this discrepancy
        discrepancy_type: Type of discrepancy
        item_type: 'order' or 'position'
        item_id: Local ID of the item
        exchange_id: Exchange ID of the item (if available)
        symbol: Trading pair
        local_data: Local data for the item
        exchange_data: Exchange data for the item
        detected_at: When the discrepancy was detected
        resolved: Whether the discrepancy has been resolved
        resolution_action: Action taken to resolve
        resolved_at: When the discrepancy was resolved
        severity: 'low', 'medium', 'high', 'critical'
    """
    discrepancy_id: str = field(default_factory=lambda: f"disc_{datetime.now(timezone.utc).timestamp()}")
    discrepancy_type: DiscrepancyType = DiscrepancyType.STATUS_MISMATCH
    item_type: str = "order"
    item_id: Optional[str] = None
    exchange_id: Optional[str] = None
    symbol: str = ""
    local_data: Dict[str, Any] = field(default_factory=dict)
    exchange_data: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolution_action: ResolutionAction = ResolutionAction.NONE
    resolved_at: Optional[datetime] = None
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Convert discrepancy to dictionary."""
        return {
            "discrepancy_id": self.discrepancy_id,
            "discrepancy_type": self.discrepancy_type.value,
            "item_type": self.item_type,
            "item_id": self.item_id,
            "exchange_id": self.exchange_id,
            "symbol": self.symbol,
            "local_data": self.local_data,
            "exchange_data": self.exchange_data,
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved,
            "resolution_action": self.resolution_action.value,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "severity": self.severity
        }


@dataclass
class ReconciliationReport:
    """Report summarizing a reconciliation run.
    
    Attributes:
        report_id: Unique ID for this report
        started_at: When reconciliation started
        completed_at: When reconciliation completed
        status: Final status of reconciliation
        duration_seconds: Duration of reconciliation in seconds
        orders_checked: Number of orders checked
        positions_checked: Number of positions checked
        discrepancies_found: Number of discrepancies found
        discrepancies_resolved: Number of discrepancies resolved
        discrepancies_remaining: Number of discrepancies remaining
        errors: List of error messages
        warnings: List of warning messages
        discrepancies: List of Discrepancy objects
    """
    report_id: str = field(default_factory=lambda: f"report_{datetime.now(timezone.utc).timestamp()}")
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    duration_seconds: float = 0.0
    orders_checked: int = 0
    positions_checked: int = 0
    discrepancies_found: int = 0
    discrepancies_resolved: int = 0
    discrepancies_remaining: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    discrepancies: List[Discrepancy] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "report_id": self.report_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "orders_checked": self.orders_checked,
            "positions_checked": self.positions_checked,
            "discrepancies_found": self.discrepancies_found,
            "discrepancies_resolved": self.discrepancies_resolved,
            "discrepancies_remaining": self.discrepancies_remaining,
            "errors": self.errors,
            "warnings": self.warnings,
            "discrepancies": [d.to_dict() for d in self.discrepancies]
        }


# ============================================================================
# RECONCILIATION ENGINE
# ============================================================================

class ReconciliationEngine:
    """Manages state reconciliation between bot and exchange.
    
    The ReconciliationEngine ensures that the bot's internal state
    (orders, positions) matches the exchange state. It handles:
    
    1. Full state sync on startup
    2. Periodic reconciliation during operation
    3. Discrepancy detection and automatic resolution
    4. State persistence for crash recovery
    5. Error handling and retry logic
    
    The engine works with OrderManager and PositionManager to maintain
    consistency and uses the database for persistence.
    """

    def __init__(
        self,
        exchange: ccxt.Exchange,
        order_manager: "OrderManager",
        position_manager: "PositionManager",
        db: "Database",
        reconcile_interval: float = 60.0,  # Reconcile every 60 seconds
        max_retries: int = 3,
        retry_delay: float = 1.0,
        test: bool = True
    ):
        """Initialize ReconciliationEngine.
        
        Args:
            exchange: CCXT exchange instance
            order_manager: OrderManager instance
            position_manager: PositionManager instance
            db: Database instance
            reconcile_interval: Seconds between reconciliations
            max_retries: Maximum retries for exchange API calls
            retry_delay: Delay between retries in seconds
            test: Whether to use paper trading mode
        """
        self.exchange = exchange
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.db = db
        self.reconcile_interval = reconcile_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.test = test
        
        # Background task
        self._reconcile_task: Optional[asyncio.Task] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Discrepancy tracking
        self._discrepancies: Dict[str, Discrepancy] = {}
        
        # Last reconciliation timestamp
        self._last_reconcile: Optional[datetime] = None
        
        # Statistics
        self._total_reconciliations = 0
        self._total_discrepancies = 0
        self._total_resolved = 0
        
        log.info(f"ReconciliationEngine initialized (test={self.test})")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start background reconciliation task."""
        log.info("Starting ReconciliationEngine background task")
        
        # Perform initial full reconciliation
        await self.full_reconciliation()
        
        # Start background task
        self._reconcile_task = asyncio.create_task(
            self._background_reconcile()
        )
        
        log.info("ReconciliationEngine started")

    async def stop(self) -> None:
        """Stop background reconciliation task."""
        log.info("Stopping ReconciliationEngine background task")
        
        if self._reconcile_task:
            self._reconcile_task.cancel()
            try:
                await self._reconcile_task
            except asyncio.CancelledError:
                pass
        
        log.info("ReconciliationEngine stopped")

    # ========================================================================
    # RECONCILIATION METHODS
    # ========================================================================

    async def full_reconciliation(self, symbol: Optional[str] = None) -> ReconciliationReport:
        """Perform a full state reconciliation.
        
        This method:
        1. Fetches all orders from exchange
        2. Fetches all positions from exchange (if supported)
        3. Compares with local state
        4. Detects and resolves discrepancies
        5. Returns a detailed report
        
        Args:
            symbol: Optional symbol to reconcile (default: all symbols)
            
        Returns:
            ReconciliationReport with results
        """
        report = ReconciliationReport()
        report.status = ReconciliationStatus.IN_PROGRESS
        
        start_time = datetime.now(timezone.utc)
        
        try:
            log.info(f"Starting full reconciliation" + (f" for {symbol}" if symbol else ""))
            
            # Step 1: Reconcile orders
            order_report = await self._reconcile_orders(symbol)
            report.orders_checked = order_report["orders_checked"]
            report.discrepancies.extend(order_report["discrepancies"])
            report.discrepancies_found += order_report["discrepancies_found"]
            report.discrepancies_resolved += order_report["discrepancies_resolved"]
            report.errors.extend(order_report["errors"])
            report.warnings.extend(order_report["warnings"])
            
            # Step 2: Reconcile positions
            position_report = await self._reconcile_positions(symbol)
            report.positions_checked = position_report["positions_checked"]
            report.discrepancies.extend(position_report["discrepancies"])
            report.discrepancies_found += position_report["discrepancies_found"]
            report.discrepancies_resolved += position_report["discrepancies_resolved"]
            report.errors.extend(position_report["errors"])
            report.warnings.extend(position_report["warnings"])
            
            # Step 3: Cross-validate orders and positions
            cross_report = await self._cross_validate(symbol)
            report.discrepancies.extend(cross_report["discrepancies"])
            report.discrepancies_found += cross_report["discrepancies_found"]
            report.discrepancies_resolved += cross_report["discrepancies_resolved"]
            report.errors.extend(cross_report["errors"])
            report.warnings.extend(cross_report["warnings"])
            
            # Calculate statistics
            report.completed_at = datetime.now(timezone.utc)
            report.duration_seconds = (report.completed_at - start_time).total_seconds()
            report.discrepancies_remaining = sum(
                1 for d in report.discrepancies if not d.resolved
            )
            report.status = ReconciliationStatus.COMPLETED
            
            # Update engine statistics
            self._total_reconciliations += 1
            self._total_discrepancies += report.discrepancies_found
            self._total_resolved += report.discrepancies_resolved
            self._last_reconcile = report.completed_at
            
            log.info(f"Full reconciliation completed: {report.discrepancies_found} discrepancies found, "
                    f"{report.discrepancies_resolved} resolved, {report.discrepancies_remaining} remaining")
            
        except Exception as e:
            report.status = ReconciliationStatus.FAILED
            report.completed_at = datetime.now(timezone.utc)
            report.errors.append(f"Reconciliation failed: {str(e)}")
            log.error(f"Full reconciliation failed: {e}")
        
        return report

    async def quick_reconciliation(self, symbol: Optional[str] = None) -> ReconciliationReport:
        """Perform a quick reconciliation (orders only).
        
        This is a lighter-weight reconciliation that only checks orders,
        suitable for more frequent runs.
        
        Args:
            symbol: Optional symbol to reconcile (default: all symbols)
            
        Returns:
            ReconciliationReport with results
        """
        report = ReconciliationReport()
        report.status = ReconciliationStatus.IN_PROGRESS
        
        start_time = datetime.now(timezone.utc)
        
        try:
            log.debug(f"Starting quick reconciliation" + (f" for {symbol}" if symbol else ""))
            
            # Only reconcile orders
            order_report = await self._reconcile_orders(symbol)
            report.orders_checked = order_report["orders_checked"]
            report.discrepancies.extend(order_report["discrepancies"])
            report.discrepancies_found = order_report["discrepancies_found"]
            report.discrepancies_resolved = order_report["discrepancies_resolved"]
            report.errors = order_report["errors"]
            report.warnings = order_report["warnings"]
            
            report.completed_at = datetime.now(timezone.utc)
            report.duration_seconds = (report.completed_at - start_time).total_seconds()
            report.discrepancies_remaining = sum(
                1 for d in report.discrepancies if not d.resolved
            )
            report.status = ReconciliationStatus.COMPLETED
            
            log.debug(f"Quick reconciliation completed: {report.discrepancies_found} discrepancies")
            
        except Exception as e:
            report.status = ReconciliationStatus.FAILED
            report.completed_at = datetime.now(timezone.utc)
            report.errors.append(f"Quick reconciliation failed: {str(e)}")
            log.error(f"Quick reconciliation failed: {e}")
        
        return report

    async def _reconcile_orders(
        self,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reconcile orders between local and exchange.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Report dictionary
        """
        report = {
            "orders_checked": 0,
            "discrepancies_found": 0,
            "discrepancies_resolved": 0,
            "errors": [],
            "warnings": [],
            "discrepancies": []
        }
        
        try:
            # Get local orders
            local_orders = await self.order_manager.get_orders()
            report["orders_checked"] = len(local_orders)
            
            # Build local order maps
            local_by_id = {o.order_id: o for o in local_orders}
            local_by_exchange_id = {
                o.exchange_order_id: o for o in local_orders
                if o.exchange_order_id
            }
            
            # Get exchange orders (if not test mode)
            exchange_orders = []
            if not self.test:
                try:
                    # Fetch open orders first
                    open_orders = await self._fetch_with_retry(
                        self.exchange.fetch_open_orders,
                        symbol if symbol else None
                    )
                    exchange_orders.extend(open_orders)
                    
                    # Also fetch closed orders from the last 24 hours
                    # (This would need exchange-specific implementation)
                    # For now, we'll just use open orders
                    
                except Exception as e:
                    report["errors"].append(f"Failed to fetch exchange orders: {str(e)}")
                    return report
            
            # Build exchange order map
            exchange_by_id = {str(o["id"]): o for o in exchange_orders}
            
            # Check for orphaned orders on exchange
            for exchange_id, exchange_order in exchange_by_id.items():
                if exchange_id not in local_by_exchange_id:
                    # Order exists on exchange but not locally
                    discrepancy = Discrepancy(
                        discrepancy_type=DiscrepancyType.ORPHANED_ORDER,
                        item_type="order",
                        exchange_id=exchange_id,
                        symbol=exchange_order.get("symbol", ""),
                        exchange_data=exchange_order,
                        severity="high"
                    )
                    
                    # Try to resolve: create local order record
                    resolved = await self._resolve_orphaned_order(discrepancy)
                    if resolved:
                        discrepancy.resolved = True
                        discrepancy.resolution_action = ResolutionAction.CREATE_LOCAL
                        discrepancy.resolved_at = datetime.now(timezone.utc)
                        report["discrepancies_resolved"] += 1
                    
                    report["discrepancies"].append(discrepancy)
                    report["discrepancies_found"] += 1
                    report["warnings"].append(f"Orphaned order on exchange: {exchange_id}")
            
            # Check for missing orders locally
            for order_id, local_order in local_by_id.items():
                if local_order.exchange_order_id and local_order.exchange_order_id not in exchange_by_id:
                    # Order exists locally but not on exchange
                    if local_order.is_active:
                        discrepancy = Discrepancy(
                            discrepancy_type=DiscrepancyType.MISSING_ORDER,
                            item_type="order",
                            item_id=order_id,
                            exchange_id=local_order.exchange_order_id,
                            symbol=local_order.symbol,
                            local_data=local_order.to_dict(),
                            severity="high"
                        )
                        
                        # Try to resolve: mark as cancelled locally
                        resolved = await self._resolve_missing_order(discrepancy)
                        if resolved:
                            discrepancy.resolved = True
                            discrepancy.resolution_action = ResolutionAction.UPDATE_LOCAL
                            discrepancy.resolved_at = datetime.now(timezone.utc)
                            report["discrepancies_resolved"] += 1
                        
                        report["discrepancies"].append(discrepancy)
                        report["discrepancies_found"] += 1
                        report["warnings"].append(f"Missing order on exchange: {order_id}")
                elif local_order.exchange_order_id and local_order.exchange_order_id in exchange_by_id:
                    # Order exists on both sides, check status
                    exchange_order = exchange_by_id[local_order.exchange_order_id]
                    exchange_status = self._normalize_order_status(
                        exchange_order.get("status", "unknown")
                    )
                    
                    if local_order.status.value != exchange_status:
                        discrepancy = Discrepancy(
                            discrepancy_type=DiscrepancyType.STATUS_MISMATCH,
                            item_type="order",
                            item_id=order_id,
                            exchange_id=local_order.exchange_order_id,
                            symbol=local_order.symbol,
                            local_data={"status": local_order.status.value},
                            exchange_data={"status": exchange_status},
                            severity="medium"
                        )
                        
                        # Try to resolve: update local status
                        resolved = await self._resolve_status_mismatch(discrepancy, local_order, exchange_order)
                        if resolved:
                            discrepancy.resolved = True
                            discrepancy.resolution_action = ResolutionAction.UPDATE_LOCAL
                            discrepancy.resolved_at = datetime.now(timezone.utc)
                            report["discrepancies_resolved"] += 1
                        
                        report["discrepancies"].append(discrepancy)
                        report["discrepancies_found"] += 1
                        report["warnings"].append(
                            f"Status mismatch for order {order_id}: local={local_order.status.value}, exchange={exchange_status}"
                        )
            
        except Exception as e:
            report["errors"].append(f"Order reconciliation error: {str(e)}")
            log.error(f"Order reconciliation error: {e}")
        
        return report

    async def _reconcile_positions(
        self,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reconcile positions between local and exchange.
        
        Note: Not all exchanges support position APIs, so this may be
        limited in functionality.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Report dictionary
        """
        report = {
            "positions_checked": 0,
            "discrepancies_found": 0,
            "discrepancies_resolved": 0,
            "errors": [],
            "warnings": [],
            "discrepancies": []
        }
        
        try:
            # Get local positions
            local_positions = await self.position_manager.get_positions()
            report["positions_checked"] = len(local_positions)
            
            # Try to get exchange positions (if supported)
            exchange_positions = []
            if not self.test:
                try:
                    # Check if exchange supports fetch_positions
                    if hasattr(self.exchange, 'fetch_positions'):
                        exchange_positions = await self._fetch_with_retry(
                            self.exchange.fetch_positions,
                            symbol if symbol else None
                        )
                    else:
                        report["warnings"].append("Exchange does not support position API")
                except Exception as e:
                    report["errors"].append(f"Failed to fetch exchange positions: {str(e)}")
                    # This is not critical, we can still check local positions
            
            # If we have exchange positions, reconcile
            if exchange_positions:
                exchange_by_id = {str(p.get("id", p.get("positionId", ""))): p for p in exchange_positions}
                
                for position_id, local_position in local_positions:
                    # Try to match by symbol (positions don't always have exchange IDs)
                    matching_exchange = [
                        p for p in exchange_positions
                        if p.get("symbol") == local_position.symbol and
                           p.get("side").lower() == local_position.side.value.lower()
                    ]
                    
                    if not matching_exchange and local_position.is_active:
                        # Position exists locally but not on exchange
                        discrepancy = Discrepancy(
                            discrepancy_type=DiscrepancyType.MISSING_POSITION,
                            item_type="position",
                            item_id=position_id,
                            symbol=local_position.symbol,
                            local_data={"qty": local_position.current_qty, "side": local_position.side.value},
                            severity="high"
                        )
                        
                        # Try to resolve: mark as closed locally
                        resolved = await self._resolve_missing_position(discrepancy)
                        if resolved:
                            discrepancy.resolved = True
                            discrepancy.resolution_action = ResolutionAction.UPDATE_LOCAL
                            discrepancy.resolved_at = datetime.now(timezone.utc)
                            report["discrepancies_resolved"] += 1
                        
                        report["discrepancies"].append(discrepancy)
                        report["discrepancies_found"] += 1
                        report["warnings"].append(f"Missing position on exchange: {position_id}")
                    elif matching_exchange:
                        # Check quantity
                        exchange_qty = sum(float(p.get("contracts", p.get("amount", 0))) for p in matching_exchange)
                        if abs(exchange_qty - local_position.current_qty) > 0.0001:
                            discrepancy = Discrepancy(
                                discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                                item_type="position",
                                item_id=position_id,
                                symbol=local_position.symbol,
                                local_data={"qty": local_position.current_qty},
                                exchange_data={"qty": exchange_qty},
                                severity="high"
                            )
                            
                            # Try to resolve: update local quantity
                            resolved = await self._resolve_quantity_mismatch(discrepancy, local_position, exchange_qty)
                            if resolved:
                                discrepancy.resolved = True
                                discrepancy.resolution_action = ResolutionAction.UPDATE_LOCAL
                                discrepancy.resolved_at = datetime.now(timezone.utc)
                                report["discrepancies_resolved"] += 1
                            
                            report["discrepancies"].append(discrepancy)
                            report["discrepancies_found"] += 1
                            report["warnings"].append(
                                f"Quantity mismatch for position {position_id}: local={local_position.current_qty}, exchange={exchange_qty}"
                            )
            
        except Exception as e:
            report["errors"].append(f"Position reconciliation error: {str(e)}")
            log.error(f"Position reconciliation error: {e}")
        
        return report

    async def _cross_validate(
        self,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cross-validate orders and positions.
        
        This checks that:
        1. Entry orders have corresponding positions
        2. Exit orders have corresponding positions
        3. Positions have corresponding entry orders
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Report dictionary
        """
        report = {
            "discrepancies_found": 0,
            "discrepancies_resolved": 0,
            "errors": [],
            "warnings": [],
            "discrepancies": []
        }
        
        try:
            # Get all orders and positions
            orders = await self.order_manager.get_orders()
            positions = await self.position_manager.get_positions()
            
            # Build lookups
            orders_by_id = {o.order_id: o for o in orders}
            positions_by_id = {p.position_id: p for p in positions}
            positions_by_entry_order = {
                p.entry_order_id: p for p in positions
                if p.entry_order_id
            }
            positions_by_exit_order = {
                p.exit_order_id: p for p in positions
                if p.exit_order_id
            }
            
            # Check 1: Entry orders should have positions
            for order_id, order in orders_by_id.items():
                if order.bot_position_id and order.bot_position_id not in positions_by_id:
                    # Order has a position ID but position doesn't exist
                    discrepancy = Discrepancy(
                        discrepancy_type=DiscrepancyType.MISSING_POSITION,
                        item_type="order",
                        item_id=order_id,
                        symbol=order.symbol,
                        local_data={"bot_position_id": order.bot_position_id},
                        severity="high"
                    )
                    report["discrepancies"].append(discrepancy)
                    report["discrepancies_found"] += 1
                    report["errors"].append(f"Order {order_id} references missing position {order.bot_position_id}")
            
            # Check 2: Positions should have entry orders
            for position_id, position in positions_by_id.items():
                if position.entry_order_id and position.entry_order_id not in orders_by_id:
                    discrepancy = Discrepancy(
                        discrepancy_type=DiscrepancyType.MISSING_ORDER,
                        item_type="position",
                        item_id=position_id,
                        symbol=position.symbol,
                        local_data={"entry_order_id": position.entry_order_id},
                        severity="medium"
                    )
                    report["discrepancies"].append(discrepancy)
                    report["discrepancies_found"] += 1
                    report["warnings"].append(f"Position {position_id} references missing entry order {position.entry_order_id}")
            
            # Check 3: Exit orders should have positions
            for order_id, order in orders_by_id.items():
                if order.bot_position_id and order.bot_position_id in positions_by_exit_order:
                    position = positions_by_exit_order[order.bot_position_id]
                    if position.status != "PositionStatus.CLOSED":
                        # Exit order exists but position not marked as closed
                        discrepancy = Discrepancy(
                            discrepancy_type=DiscrepancyType.STATUS_MISMATCH,
                            item_type="position",
                            item_id=position.position_id,
                            symbol=position.symbol,
                            local_data={"status": position.status.value},
                            severity="medium"
                        )
                        
                        # Try to resolve: mark position as closed
                        resolved = await self._resolve_position_status(discrepancy, position)
                        if resolved:
                            discrepancy.resolved = True
                            discrepancy.resolution_action = ResolutionAction.UPDATE_LOCAL
                            discrepancy.resolved_at = datetime.now(timezone.utc)
                            report["discrepancies_resolved"] += 1
                        
                        report["discrepancies"].append(discrepancy)
                        report["discrepancies_found"] += 1
            
        except Exception as e:
            report["errors"].append(f"Cross-validation error: {str(e)}")
            log.error(f"Cross-validation error: {e}")
        
        return report

    # ========================================================================
    # DISCREPANCY RESOLUTION
    # ========================================================================

    async def _resolve_orphaned_order(self, discrepancy: Discrepancy) -> bool:
        """Resolve an orphaned order (exists on exchange but not locally).
        
        Args:
            discrepancy: Discrepancy to resolve
            
        Returns:
            True if resolved successfully
        """
        try:
            exchange_order = discrepancy.exchange_data
            
            # Create local order record
            order = await self.order_manager.create_order(
                symbol=exchange_order.get("symbol", ""),
                side="OrderSide.BUY" if exchange_order.get("side", "").lower() == "buy" else "OrderSide.SELL",
                order_type="OrderType.LIMIT" if exchange_order.get("type", "").lower() == "limit" else "OrderType.MARKET",
                qty=float(exchange_order.get("amount", exchange_order.get("cost", 0))),
                price=float(exchange_order.get("price")) if exchange_order.get("price") else None,
                stop_price=float(exchange_order.get("stopPrice")) if exchange_order.get("stopPrice") else None,
                stop_limit_price=float(exchange_order.get("stopLimitPrice")) if exchange_order.get("stopLimitPrice") else None,
                test=self.test
            )
            
            log.info(f"Created local order for orphaned exchange order: {discrepancy.exchange_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to resolve orphaned order: {e}")
            return False

    async def _resolve_missing_order(self, discrepancy: Discrepancy) -> bool:
        """Resolve a missing order (exists locally but not on exchange).
        
        Args:
            discrepancy: Discrepancy to resolve
            
        Returns:
            True if resolved successfully
        """
        try:
            # Mark order as cancelled locally
            await self.order_manager.cancel_order(discrepancy.item_id)
            
            log.info(f"Cancelled local order missing on exchange: {discrepancy.item_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to resolve missing order: {e}")
            return False

    async def _resolve_status_mismatch(
        self,
        discrepancy: Discrepancy,
        local_order: "Order",
        exchange_order: Dict[str, Any]
    ) -> bool:
        """Resolve a status mismatch between local and exchange order.
        
        Args:
            discrepancy: Discrepancy to resolve
            local_order: Local order object
            exchange_order: Exchange order data
            
        Returns:
            True if resolved successfully
        """
        try:
            # Update local order status from exchange
            exchange_status = self._normalize_order_status(
                exchange_order.get("status", "unknown")
            )
            
            # Convert to OrderStatus
            from backend.trading.order_manager import OrderStatus
            new_status = OrderStatus(exchange_status)
            
            # Update order in OrderManager
            local_order.status = new_status
            local_order.filled = float(exchange_order.get("filled", local_order.filled))
            local_order.avg_fill_price = float(exchange_order.get("average", 0)) if exchange_order.get("average") else local_order.avg_fill_price
            local_order.updated_at = datetime.now(timezone.utc)
            
            # Update in database
            await self.db.update_order(
                order_id=local_order.order_id,
                status=new_status.value,
                filled=local_order.filled,
                avg_fill_price=local_order.avg_fill_price,
                updated_at=local_order.updated_at
            )
            
            log.info(f"Updated order status from exchange: {local_order.order_id} -> {new_status.value}")
            return True
            
        except Exception as e:
            log.error(f"Failed to resolve status mismatch: {e}")
            return False

    async def _resolve_missing_position(self, discrepancy: Discrepancy) -> bool:
        """Resolve a missing position (exists locally but not on exchange).
        
        Args:
            discrepancy: Discrepancy to resolve
            
        Returns:
            True if resolved successfully
        """
        try:
            # Mark position as closed locally
            position = await self.position_manager.get_position(discrepancy.item_id)
            if position:
                await self.position_manager.close_position(
                    position_id=discrepancy.item_id,
                    exit_price=position.entry_price,  # Use entry price as fallback
                    exit_reason="ExitReason.MANUAL"
                )
            
            log.info(f"Closed local position missing on exchange: {discrepancy.item_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to resolve missing position: {e}")
            return False

    async def _resolve_quantity_mismatch(
        self,
        discrepancy: Discrepancy,
        local_position: "Position",
        exchange_qty: float
    ) -> bool:
        """Resolve a quantity mismatch between local and exchange position.
        
        Args:
            discrepancy: Discrepancy to resolve
            local_position: Local position object
            exchange_qty: Quantity from exchange
            
        Returns:
            True if resolved successfully
        """
        try:
            # Update local position quantity to match exchange
            local_position.current_qty = exchange_qty
            local_position.updated_at = datetime.now(timezone.utc)
            
            # Update in database
            await self.db.update_position(
                position_id=local_position.position_id,
                current_qty=exchange_qty,
                updated_at=local_position.updated_at
            )
            
            log.info(f"Updated position quantity from exchange: {local_position.position_id} -> {exchange_qty}")
            return True
            
        except Exception as e:
            log.error(f"Failed to resolve quantity mismatch: {e}")
            return False

    async def _resolve_position_status(
        self,
        discrepancy: Discrepancy,
        position: "Position"
    ) -> bool:
        """Resolve a position status mismatch.
        
        Args:
            discrepancy: Discrepancy to resolve
            position: Position object
            
        Returns:
            True if resolved successfully
        """
        try:
            # Mark position as closed
            position.status = "PositionStatus.CLOSED"
            position.exit_time = datetime.now(timezone.utc)
            
            await self.db.update_position(
                position_id=position.position_id,
                status=position.status.value,
                exit_time=position.exit_time
            )
            
            log.info(f"Updated position status: {position.position_id} -> CLOSED")
            return True
            
        except Exception as e:
            log.error(f"Failed to resolve position status: {e}")
            return False

    # ========================================================================
    # BACKGROUND TASK
    # ========================================================================

    async def _background_reconcile(self) -> None:
        """Background reconciliation task."""
        try:
            while True:
                await asyncio.sleep(self.reconcile_interval)
                
                # Perform quick reconciliation (orders only)
                report = await self.quick_reconciliation()
                
                if report.discrepancies_found > 0:
                    log.info(f"Background reconciliation: {report.discrepancies_found} discrepancies found")
                
                # Every 10 minutes, do a full reconciliation
                if self._total_reconciliations % 10 == 0:
                    await self.full_reconciliation()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Background reconciliation failed: {e}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _normalize_order_status(self, status: str) -> str:
        """Normalize exchange order status to our format.
        
        Args:
            status: Exchange status string
            
        Returns:
            Normalized status string
        """
        status_map = {
            "open": "pending",
            "pending": "pending",
            "partially_filled": "partially_filled",
            "filled": "filled",
            "canceled": "canceled",
            "rejected": "rejected",
            "expired": "expired",
            "closed": "filled"
        }
        return status_map.get(status.lower(), "unknown")

    async def _fetch_with_retry(
        self,
        func,
        *args,
        **kwargs
    ) -> Any:
        """Execute exchange API call with retry logic.
        
        Args:
            func: Exchange function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from exchange API
            
        Raises:
            Exception: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                log.warning(f"Exchange API attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        raise Exception(f"Exchange API failed after {self.max_retries} attempts: {last_error}")

    # ========================================================================
    # STATISTICS & REPORTING
    # ========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """Get reconciliation statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_reconciliations": self._total_reconciliations,
            "total_discrepancies": self._total_discrepancies,
            "total_resolved": self._total_resolved,
            "last_reconcile": self._last_reconcile.isoformat() if self._last_reconcile else None,
            "pending_discrepancies": sum(
                1 for d in self._discrepancies.values() if not d.resolved
            ),
            "resolved_discrepancies": sum(
                1 for d in self._discrepancies.values() if d.resolved
            )
        }

    async def get_discrepancies(
        self,
        resolved: Optional[bool] = None,
        severity: Optional[str] = None
    ) -> List[Discrepancy]:
        """Get list of discrepancies.
        
        Args:
            resolved: Filter by resolved status (True/False/None for all)
            severity: Filter by severity
            
        Returns:
            List of Discrepancy objects
        """
        discrepancies = list(self._discrepancies.values())
        
        if resolved is not None:
            discrepancies = [d for d in discrepancies if d.resolved == resolved]
        
        if severity:
            discrepancies = [d for d in discrepancies if d.severity == severity]
        
        return discrepancies

    async def get_discrepancy(self, discrepancy_id: str) -> Optional[Discrepancy]:
        """Get a specific discrepancy by ID.
        
        Args:
            discrepancy_id: ID of discrepancy to retrieve
            
        Returns:
            Discrepancy object or None
        """
        return self._discrepancies.get(discrepancy_id)

    # ========================================================================
    # STATE PERSISTENCE
    # ========================================================================

    async def save_state(self) -> None:
        """Save current state to database.
        
        This persists all orders and positions to ensure state survival
        across restarts.
        """
        try:
            # Orders are already saved by OrderManager
            # Positions are already saved by PositionManager
            
            # Save last reconciliation timestamp
            if self._last_reconcile:
                await self.db.set_state(
                    "last_reconciliation",
                    self._last_reconcile.isoformat()
                )
            
            log.debug("State saved to database")
        except Exception as e:
            log.error(f"Failed to save state: {e}")

    async def load_state(self) -> None:
        """Load state from database on startup.
        
        This is called during initialization to restore state.
        """
        try:
            # Load last reconciliation timestamp
            last_reconcile_str = await self.db.get_state("last_reconciliation")
            if last_reconcile_str:
                self._last_reconcile = datetime.fromisoformat(last_reconcile_str)
            
            log.debug("State loaded from database")
        except Exception as e:
            log.error(f"Failed to load state: {e}")
