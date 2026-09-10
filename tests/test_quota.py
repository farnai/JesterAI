import pytest
from jester_core.quota import InMemoryQuotaService


@pytest.mark.asyncio
async def test_quota_allows_first_three_questions():
    quota = InMemoryQuotaService(free_questions_limit=3, enforce=True)
    user_id = "usr_sovereign_99"

    # Turn 1: 3 remaining
    d1 = await quota.check_access(user_id)
    assert d1.allowed is True
    assert d1.remaining_free_questions == 3
    await quota.consume_quota(user_id)

    # Turn 2: 2 remaining
    d2 = await quota.check_access(user_id)
    assert d2.allowed is True
    assert d2.remaining_free_questions == 2
    await quota.consume_quota(user_id)

    # Turn 3: 1 remaining
    d3 = await quota.check_access(user_id)
    assert d3.allowed is True
    assert d3.remaining_free_questions == 1
    await quota.consume_quota(user_id)

    # Turn 4: 0 remaining -> REJECTED
    d4 = await quota.check_access(user_id)
    assert d4.allowed is False
    assert d4.remaining_free_questions == 0
    assert d4.rejection_code == "QUOTA_EXCEEDED"
    assert "ამოწურეთ" in d4.rejection_message


@pytest.mark.asyncio
async def test_quota_reset_and_isolation():
    quota = InMemoryQuotaService(free_questions_limit=3, enforce=True)
    user_a = "usr_a"
    user_b = "usr_b"

    # Exhaust user_a
    for _ in range(3):
        await quota.consume_quota(user_a)

    assert (await quota.check_access(user_a)).allowed is False
    # user_b should be completely unaffected
    assert (await quota.check_access(user_b)).allowed is True
    assert (await quota.check_access(user_b)).remaining_free_questions == 3

    # Reset user_a
    quota.reset(user_a)
    assert (await quota.check_access(user_a)).allowed is True
    assert (await quota.check_access(user_a)).remaining_free_questions == 3


@pytest.mark.asyncio
async def test_quota_unenforced_mode():
    quota = InMemoryQuotaService(free_questions_limit=3, enforce=False)
    user = "usr_infinite"

    for _ in range(10):
        await quota.consume_quota(user)
        d = await quota.check_access(user)
        assert d.allowed is True
