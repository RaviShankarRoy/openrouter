"""OAuth token exchange: claim validation that is currently missing.

`OAuthService.exchange` turns a third-party *access token* into a backend JWT.
Two checks that this flow requires are absent, and both are exploitable:

1. **`email_verified` is never checked on the Google path.** `_google_email`
   returns `data.get("email")` straight from userinfo. The GitHub path does
   filter on `verified` (`_github_email`), which is what makes the Google
   omission clearly an oversight rather than a decision.

2. **The token's audience is never validated.** Google's userinfo endpoint
   accepts *any* valid Google access token, including one minted for a
   different OAuth client. So a token issued to some unrelated application can
   be replayed here to obtain a backend JWT for that user — the confused-deputy
   / token-substitution attack. A correct implementation verifies the token was
   issued to our own client id (via tokeninfo's `aud`, or by using an ID token
   and checking `aud`) before trusting any claim in it.

The tests for those two are RED until Phase 4. The GitHub tests alongside them
pass today and exist to keep the behaviour that is already correct.
"""
from __future__ import annotations

from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest
import respx
from httpx import Response

from app.service.domain.entities import Organization, User, UserRole
from app.service.domain.errors import DomainError
from app.service.domain.repositories import OrganizationRepository, UserRepository
from app.service.oauth_service import OAuthExchangeCommand, OAuthService
from app.service.uow import UnitOfWork

_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
_GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


class _InMemoryUserRepo(UserRepository):
    def __init__(self) -> None:
        self.by_email: dict[str, User] = {}

    async def get(self, user_id: UUID) -> User | None:
        return next((u for u in self.by_email.values() if u.id == user_id), None)

    async def find_by_email(self, email: str) -> User | None:
        return self.by_email.get(email)

    async def add(self, user: User) -> User:
        self.by_email[user.email] = user
        return user


class _InMemoryOrgRepo(OrganizationRepository):
    def __init__(self) -> None:
        self.by_id: dict[UUID, Organization] = {}

    async def get(self, org_id: UUID) -> Organization | None:
        return self.by_id.get(org_id)

    async def add(self, org: Organization) -> Organization:
        self.by_id[org.id] = org
        return org


class _FakeUoW(UnitOfWork):
    def __init__(self) -> None:
        self.users = _InMemoryUserRepo()
        self.organizations = _InMemoryOrgRepo()
        self.api_keys = None  # type: ignore[assignment]
        self.credits = None  # type: ignore[assignment]
        self.usage = None  # type: ignore[assignment]
        self.video_jobs = None  # type: ignore[assignment]
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None


# ---------------------------------------------------------------- Google: RED

@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_google_unverified_email_is_rejected(respx_mock: respx.Router) -> None:
    """An unverified Google email must not be accepted as an identity.

    Trusting an unverified address lets a caller claim any email the provider
    has not actually proven they control, which is account takeover by
    pre-registration.
    """
    respx_mock.get(_GOOGLE_USERINFO_URL).mock(
        return_value=Response(
            200,
            json={"email": "victim@example.com", "verified_email": False, "id": "1"},
        )
    )
    uow = _FakeUoW()
    svc = OAuthService(uow)

    with pytest.raises(DomainError):
        await svc.exchange(OAuthExchangeCommand(provider="google", access_token="tok"))

    assert "victim@example.com" not in uow.users.by_email, (
        "an account was provisioned from an unverified Google email"
    )


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_google_token_issued_to_another_client_is_rejected(
    respx_mock: respx.Router,
) -> None:
    """A Google access token minted for a different OAuth client must be refused.

    userinfo happily accepts any valid Google token, so without an audience
    check an attacker can take a token their own app obtained and exchange it
    here for a backend JWT belonging to that user.
    """
    respx_mock.get(_GOOGLE_TOKENINFO_URL).mock(
        return_value=Response(
            200,
            json={
                "aud": "attacker-app.apps.googleusercontent.com",
                "email": "victim@example.com",
                "email_verified": "true",
            },
        )
    )
    respx_mock.get(_GOOGLE_USERINFO_URL).mock(
        return_value=Response(
            200,
            json={"email": "victim@example.com", "verified_email": True, "id": "1"},
        )
    )
    svc = OAuthService(_FakeUoW())

    with pytest.raises(DomainError):
        await svc.exchange(OAuthExchangeCommand(provider="google", access_token="foreign"))


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_google_verified_email_is_accepted(respx_mock: respx.Router) -> None:
    """The happy path must keep working once the checks above are added."""
    respx_mock.get(_GOOGLE_TOKENINFO_URL).mock(
        return_value=Response(
            200, json={"aud": "", "email": "ok@example.com", "email_verified": "true"}
        )
    )
    respx_mock.get(_GOOGLE_USERINFO_URL).mock(
        return_value=Response(
            200, json={"email": "ok@example.com", "verified_email": True, "id": "2"}
        )
    )
    uow = _FakeUoW()
    issued = await OAuthService(uow).exchange(
        OAuthExchangeCommand(provider="google", access_token="tok")
    )

    assert issued.access_token
    assert issued.role == UserRole.OWNER.value
    assert uow.users.by_email["ok@example.com"].email == "ok@example.com"
    assert uow.committed is True


# ------------------------------------------------- GitHub: already correct

@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_github_uses_the_verified_primary_email(respx_mock: respx.Router) -> None:
    respx_mock.get(_GITHUB_EMAILS_URL).mock(
        return_value=Response(
            200,
            json=[
                {"email": "secondary@example.com", "primary": False, "verified": True},
                {"email": "primary@example.com", "primary": True, "verified": True},
            ],
        )
    )
    uow = _FakeUoW()
    issued = await OAuthService(uow).exchange(
        OAuthExchangeCommand(provider="github", access_token="gh")
    )
    assert issued.access_token
    assert "primary@example.com" in uow.users.by_email


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_github_unverified_primary_email_is_rejected(
    respx_mock: respx.Router,
) -> None:
    respx_mock.get(_GITHUB_EMAILS_URL).mock(
        return_value=Response(
            200,
            json=[{"email": "unverified@example.com", "primary": True, "verified": False}],
        )
    )
    uow = _FakeUoW()
    with pytest.raises(DomainError):
        await OAuthService(uow).exchange(
            OAuthExchangeCommand(provider="github", access_token="gh")
        )
    assert uow.users.by_email == {}


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_unsupported_provider_is_rejected(respx_mock: respx.Router) -> None:
    with pytest.raises(DomainError):
        await OAuthService(_FakeUoW()).exchange(
            OAuthExchangeCommand(provider="gitlab", access_token="x")  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_existing_user_is_reused_not_reprovisioned(
    respx_mock: respx.Router,
) -> None:
    """A returning user must map to their existing org, not get a second one."""
    respx_mock.get(_GOOGLE_TOKENINFO_URL).mock(
        return_value=Response(
            200, json={"aud": "", "email": "back@example.com", "email_verified": "true"}
        )
    )
    respx_mock.get(_GOOGLE_USERINFO_URL).mock(
        return_value=Response(
            200, json={"email": "back@example.com", "verified_email": True, "id": "3"}
        )
    )
    uow = _FakeUoW()
    existing_org = Organization(name="theirs", slug="org-existing")
    await uow.organizations.add(existing_org)
    await uow.users.add(
        User(org_id=existing_org.id, email="back@example.com", role=UserRole.MEMBER)
    )

    issued = await OAuthService(uow).exchange(
        OAuthExchangeCommand(provider="google", access_token="tok")
    )

    assert issued.org_id == str(existing_org.id)
    assert issued.role == UserRole.MEMBER.value
    assert len(uow.organizations.by_id) == 1, "a duplicate organisation was created"
