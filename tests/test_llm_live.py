import pytest

from tlaforge import MachineDraft, TLAForgeSession


SUPPORTED_PATCH_OPS = {
    "set_module_name",
    "set_summary",
    "put_state",
    "remove_state",
    "rename_state",
    "set_initial_state",
    "put_variable",
    "remove_variable",
    "rename_variable",
    "put_transition",
    "remove_transition",
    "put_rule",
    "remove_rule",
    "add_assumption",
    "remove_assumption",
    "add_open_question",
    "resolve_open_question",
}


@pytest.mark.live_network
def test_local_provider_returns_valid_assistant_turn(
    live_client,
    live_traffic_light_messages,
) -> None:
    turn = live_client.complete_turn(
        draft=MachineDraft(),
        transcript=[],
        user_message=live_traffic_light_messages[0],
    )

    operation_names = [operation.op for operation in turn.patch.operations]

    assert turn.reply
    assert operation_names
    assert set(operation_names) <= SUPPORTED_PATCH_OPS
    assert "set_module_name" in operation_names
    assert "set_initial_state" in operation_names
    assert operation_names.count("put_state") >= 3


@pytest.mark.live_network
def test_local_provider_can_drive_session_to_handoff(
    live_client,
    live_traffic_light_messages,
) -> None:
    session = TLAForgeSession.new()

    for message in live_traffic_light_messages:
        result = session.handle_user_message(message, live_client)
        assert result.reply
        assert result.patch.operations
        assert result.validation.issues == []

    artifact = session.export_handoff()

    assert artifact.validation.ready is True
    assert artifact.module_name == "TrafficLight"
    assert not artifact.open_questions
    assert "MODULE TrafficLight" in artifact.tla_source
    assert 'state = "red"' in artifact.tla_source
    assert 'state\' = "green"' in artifact.tla_source
    assert 'state = "green"' in artifact.tla_source
    assert 'state\' = "yellow"' in artifact.tla_source
    assert 'state = "yellow"' in artifact.tla_source
    assert 'state\' = "red"' in artifact.tla_source
    assert "ValidState ==" in artifact.tla_source
    assert "state \\in States" in artifact.tla_source
