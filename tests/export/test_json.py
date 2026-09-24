"""Unit tests for JsonExporter."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ha_docgen.context import AIContext, ContextMetadata, PackageContext
from ha_docgen.export import JsonExporter
from ha_docgen.packages import Package
from ha_docgen.prompt import (
    Prompt,
    PromptBuilder,
    PromptSection,
    PromptSectionKind,
    PromptType,
)
from ha_docgen.yaml import YamlDocument
from tests.export.factory import (
    empty_prompt,
    ordered_entity_prompt,
    populated_prompt,
)


def _load(prompt: object) -> dict[str, object]:
    rendered = JsonExporter().export(prompt)  # type: ignore[arg-type]
    loaded = json.loads(rendered)
    assert isinstance(loaded, dict)
    return loaded


def _assert_sorted(value: object) -> None:
    if isinstance(value, dict):
        assert list(value) == sorted(value)
        for item in value.values():
            _assert_sorted(item)
    elif isinstance(value, list):
        for item in value:
            _assert_sorted(item)


def test_empty_prompt_json_is_valid_and_exact() -> None:
    rendered = JsonExporter().export(empty_prompt())
    assert json.loads(rendered) == {
        "formatting_hints": [],
        "prompt_type": "generic",
        "sections": [],
        "system_instructions": "Use only the supplied context.",
        "task_description": "Complete the task.",
    }
    assert rendered.endswith("\n")
    assert "title" not in json.loads(rendered)


def test_populated_prompt_json_keeps_sections_and_omits_computed_fields() -> None:
    payload = _load(populated_prompt())
    assert payload["prompt_type"] == "programming"
    sections = payload["sections"]
    assert isinstance(sections, list)
    assert [section["kind"] for section in sections] == ["entity", "automation", "package"]
    entity_section = sections[0]
    assert isinstance(entity_section, dict)
    content = entity_section["content"]
    assert isinstance(content, list)
    assert content[0]["entity"]["entity_id"] == "light.a"
    assert content[1]["entity"]["entity_id"] == "light.b"
    assert "domain" not in content[0]["entity"]
    assert "packages/alpha.yaml" in json.dumps(payload)
    _assert_sorted(payload)


def test_json_preserves_sequence_order_and_sorts_object_keys() -> None:
    first = JsonExporter().export(ordered_entity_prompt())
    payload = json.loads(first)
    content = payload["sections"][0]["content"]
    assert content[0]["entity"]["entity_id"] == "light.b"
    assert content[1]["entity"]["entity_id"] == "light.a"
    assert list(content[0]["entity"]["extra"]) == ["m", "z"]
    assert payload["formatting_hints"] == ["keep facts", "keep order"]
    assert first.index('"formatting_hints"') < first.index('"prompt_type"')
    assert first.index('"prompt_type"') < first.index('"sections"')
    _assert_sorted(payload)


def test_json_round_trip_is_stable() -> None:
    rendered = JsonExporter().export(populated_prompt())
    again = json.dumps(json.loads(rendered), indent=2, sort_keys=True, ensure_ascii=False)
    assert f"{again}\n" == rendered


def test_json_exports_paths_and_datetimes_without_computed_titles() -> None:
    metadata = ContextMetadata(
        project_path=Path("packages") / "home",
        generated_at=datetime(2026, 9, 22, 8, 0, 0, tzinfo=UTC),
    )
    prompt = PromptBuilder().build(AIContext(metadata=metadata), PromptType.GENERIC)
    payload = _load(prompt)
    content = payload["sections"][0]["content"]
    assert isinstance(content, dict)
    assert content["project_path"] == "packages/home"
    assert content["generated_at"] == "2026-09-22T08:00:00+00:00"
    assert "title" not in payload


def test_cyclic_content_is_rejected() -> None:
    data: list[object] = []
    data.append(data)
    prompt = _package_prompt(data)
    with pytest.raises(TypeError, match="Cyclic prompt content"):
        JsonExporter().export(prompt)


def test_unsupported_content_is_rejected() -> None:
    prompt = _package_prompt(object())
    with pytest.raises(TypeError, match="Unsupported export value"):
        JsonExporter().export(prompt)


def test_mapping_keys_become_stable_strings() -> None:
    from ha_docgen.relationships import ObjectType

    rendered = JsonExporter().export(
        _package_prompt(
            {
                ObjectType.ENTITY: "light",
                True: "yes",
                False: "no",
                None: "empty",
                3: "three",
            }
        )
    )
    assert '"3": "three"' in rendered
    assert '"entity": "light"' in rendered
    assert '"false": "no"' in rendered
    assert '"null": "empty"' in rendered
    assert '"true": "yes"' in rendered
    _assert_sorted(json.loads(rendered))


def test_text_renderer_rejects_a_scalar_root() -> None:
    from ha_docgen.export._text import render_data

    with pytest.raises(TypeError, match="Unsupported export value: str"):
        render_data("text")


def test_bytes_content_is_rejected() -> None:
    with pytest.raises(TypeError, match="Unsupported export value: bytes"):
        JsonExporter().export(_package_prompt(b"raw"))


def test_unsupported_mapping_key_is_rejected() -> None:
    prompt = _package_prompt({("source", "target"): "edge"})
    with pytest.raises(TypeError, match="Unsupported export key"):
        JsonExporter().export(prompt)


def _package_prompt(data: object) -> Prompt:
    path = Path("packages") / "alpha.yaml"
    owned = Package(name="alpha", path=path, document=YamlDocument(path=path, text="", data=data))
    return Prompt(
        prompt_type=PromptType.DOCUMENTATION,
        system_instructions="Use only the supplied context.",
        task_description="Document the context.",
        sections=(
            PromptSection(
                kind=PromptSectionKind.PACKAGE,
                title="Package Context",
                content=(PackageContext(package=owned),),
            ),
        ),
    )


def test_repeated_json_exports_are_identical() -> None:
    exporter = JsonExporter()
    prompt = ordered_entity_prompt()
    first = exporter.export(prompt)
    assert exporter.export(prompt) == first
    assert exporter.export(empty_prompt()) != first
    assert exporter.export(prompt) == first
