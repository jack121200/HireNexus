from __future__ import annotations

from app.routes.ws import _parse_transcript_event


def test_parse_turn_partial() -> None:
    payload = {"type": "Turn", "transcript": "hello there", "end_of_turn": False}
    assert _parse_transcript_event(payload) == ("stt.partial", "hello there")


def test_parse_turn_final() -> None:
    payload = {"type": "Turn", "transcript": "final answer", "end_of_turn": True}
    assert _parse_transcript_event(payload) == ("stt.final", "final answer")


def test_parse_legacy_partial_and_final() -> None:
    partial_payload = {"message_type": "PartialTranscript", "text": "draft"}
    final_payload = {"message_type": "FinalTranscript", "text": "done"}
    assert _parse_transcript_event(partial_payload) == ("stt.partial", "draft")
    assert _parse_transcript_event(final_payload) == ("stt.final", "done")
