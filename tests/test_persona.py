import pytest
from pathlib import Path
from jester_core import PersonaManager, ContextBuilder, OutputFilter

PERSONA_DIR = Path(__file__).resolve().parent.parent / "persona"


def test_persona_manager_loading():
    pm = PersonaManager(persona_dir=PERSONA_DIR)
    prompt = pm.get_compiled_system_prompt()
    assert "JESTER" in prompt
    assert "OPERATIONAL RULES" in prompt

    examples = pm.get_examples()
    assert len(examples) > 0
    assert "user" in examples[0]
    assert "assistant" in examples[0]


def test_output_filter_strips_stage_directions():
    f = OutputFilter()

    # Asterisk stage directions
    test_str_1 = "*laughs* Truly an astonishing decree."
    assert f.sanitize(test_str_1) == "Truly an astonishing decree."

    # Georgian asterisk stage directions
    test_str_2 = "*იცინის* რა თქმა უნდა, ბატონო."
    assert f.sanitize(test_str_2) == "რა თქმა უნდა, ბატონო."

    # Parentheses stage directions
    test_str_3 = "(იცინის) ეს უკვე მეტისმეტია."
    assert f.sanitize(test_str_3) == "ეს უკვე მეტისმეტია."

    test_str_4 = "(rolls eyes) As you wish."
    assert f.sanitize(test_str_4) == "As you wish."

    # Normal text should remain intact
    normal_text = "This is pure wit without any silly roleplay actions."
    assert f.sanitize(normal_text) == normal_text


def test_context_builder():
    pm = PersonaManager(persona_dir=PERSONA_DIR)
    cb = ContextBuilder(persona_manager=pm, max_history_messages=2)

    history = [
        {"role": "user", "content": "Query 1"},
        {"role": "assistant", "content": "Answer 1"},
        {"role": "user", "content": "Query 2"},
        {"role": "assistant", "content": "Answer 2"},
    ]

    messages = cb.build_messages(
        current_message="Query 3",
        history=history,
        include_examples=False,
    )

    # First message should be system prompt
    assert messages[0]["role"] == "system"
    # Last message should be current message
    assert messages[-1] == {"role": "user", "content": "Query 3"}
    # Because max_history_messages=2, only last 2 history items + system + current message = 4 items
    assert len(messages) == 4
    assert messages[1] == {"role": "user", "content": "Query 2"}
    assert messages[2] == {"role": "assistant", "content": "Answer 2"}
