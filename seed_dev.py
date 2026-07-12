import asyncio
from app.domain.entities import Organization, User, KeyScope
from app.infrastructure.database import init_db, get_session_factory
from app.infrastructure.uow import SqlUnitOfWork
from app.core.config import settings
from app.application.auth_service import AuthService
from app.application.commands import CreateKeyCommand
from uuid import uuid4

async def main():
    await init_db(settings)
    uow = SqlUnitOfWork(get_session_factory())
    org_id = uuid4()
    user_id = uuid4()
    async with uow:
        await uow.organizations.add(Organization(id=org_id, name="Dev", slug="dev"))
        await uow.users.add(User(id=user_id, org_id=org_id, email="dev@local"))
        await uow.commit()
    svc = AuthService(SqlUnitOfWork(get_session_factory()))
    out = await svc.create_key(CreateKeyCommand(
        org_id=org_id, user_id=user_id, name="dev-key", scope=KeyScope.PERSONAL,
    ))
    print(f"\n  API KEY (save it — shown once):\n  {out.plaintext}\n")

asyncio.run(main())
