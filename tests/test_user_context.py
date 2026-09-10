from pathlib import Path
from backend.schemas import UserContext
from jester_core import ContextBuilder, PersonaManager


PERSONA_DIR = Path(__file__).resolve().parent.parent / "persona"


def test_user_context_schema_validation():
    ctx = UserContext(
        name="დავით მეფე",
        birth_date="1989-11-23",
        zodiac="მშვილდოსანი",
        daily_energy=85,
        custom_attributes={"title": "Master of the Realm"},
    )
    assert ctx.name == "დავით მეფე"
    assert ctx.daily_energy == 85
    assert ctx.custom_attributes["title"] == "Master of the Realm"


def test_context_builder_injects_sovereign_attributes():
    pm = PersonaManager(persona_dir=PERSONA_DIR)
    cb = ContextBuilder(persona_manager=pm)

    ctx = UserContext(
        name="ალექსანდრე",
        zodiac="ლომი",
        daily_energy=92,
    )

    messages = cb.build_messages(
        current_message="როგორია დღევანდელი დღე?",
        user_context=ctx,
        include_examples=False,
    )

    system_msg = messages[0]["content"]

    # Assert Sovereign block presence and correct attributes
    assert "### THE CURRENT SOVEREIGN (USER ATTRIBUTES)" in system_msg
    assert "- Name / Title: ალექსანდრე" in system_msg
    assert "- Zodiac Sign: ლომი" in system_msg
    assert "- Daily Energy Score: 92 / 100" in system_msg
    assert "Court Instruction" in system_msg


def test_context_builder_without_sovereign_context():
    pm = PersonaManager(persona_dir=PERSONA_DIR)
    cb = ContextBuilder(persona_manager=pm)

    messages = cb.build_messages(
        current_message="Hello",
        user_context=None,
        include_examples=False,
    )

    system_msg = messages[0]["content"]
    assert "### THE CURRENT SOVEREIGN" not in system_msg
