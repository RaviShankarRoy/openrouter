"""Credit balance repository — atomic deduction via UPDATE...RETURNING."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import CreditBalance
from app.domain.repositories import CreditRepository
from app.domain.value_objects import Money
from app.infrastructure import orm_models as orm


class SqlCreditRepository(CreditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_update(self, org_id: UUID) -> CreditBalance:
        # SELECT ... FOR UPDATE prevents concurrent reservations from racing.
        row = await self._session.get(orm.CreditBalance, org_id, with_for_update=True)
        if row is None:
            row = orm.CreditBalance(org_id=org_id, available=Decimal("0"))
            self._session.add(row)
            await self._session.flush()
        return _to_domain(row)

    async def update(self, balance: CreditBalance) -> None:
        stmt = (
            update(orm.CreditBalance)
            .where(orm.CreditBalance.org_id == balance.org_id)
            .values(
                available=balance.available,
                reserved=balance.reserved,
                monthly_cap=balance.monthly_cap,
                daily_cap=balance.daily_cap,
                hard_stop=balance.hard_stop,
            )
        )
        await self._session.execute(stmt)

    async def deduct_atomic(self, org_id: UUID, amount: Money) -> bool:
        """Atomic deduction with non-negative invariant. Returns True if deducted."""
        stmt = (
            update(orm.CreditBalance)
            .where(orm.CreditBalance.org_id == org_id)
            .where(orm.CreditBalance.available >= amount.amount)
            .values(available=orm.CreditBalance.available - amount.amount)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


def _to_domain(row: orm.CreditBalance) -> CreditBalance:
    return CreditBalance(
        org_id=row.org_id,
        available=row.available,
        reserved=row.reserved,
        monthly_cap=row.monthly_cap,
        daily_cap=row.daily_cap,
        hard_stop=row.hard_stop,
    )
