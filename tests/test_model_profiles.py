# -*- coding: utf-8 -*-
"""Testy profili modelu agenta: czyste funkcje loop.py (resolve_agent_env /
redacted_config) oraz wiring --model -> środowisko PROCESU agenta.

Inwariant: nadpisania dotyczą TYLKO agenta. Weryfikatory i git zostają na
domyślnym środowisku, żeby sygnał prawdy był niezależny od backendu modelu.
Sekret żyje w otoczeniu (${ZMIENNA}), nie w configu ani w logu.
"""
import importlib.util
from pathlib import Path

from conftest import LoopEnv, VERIFY_GREEN

LOOP_PY = Path(__file__).resolve().parents[1] / "loop.py"
_spec = importlib.util.spec_from_file_location("loop_mod", LOOP_PY)
loop = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loop)


# ---------------------------------------------------------------------------
# resolve_agent_env: merge profilu nad bazą + rozwinięcie ${ZMIENNA}
# ---------------------------------------------------------------------------

def test_resolve_expands_env_refs_and_merges_profile_over_base():
    base = {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000"}
    profile = {
        "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
        "ANTHROPIC_AUTH_TOKEN": "${ZAI_API_KEY}",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.2[1m]",
    }
    resolved, missing = loop.resolve_agent_env(
        base, profile, {"ZAI_API_KEY": "sk-secret-123"}
    )
    assert resolved["ANTHROPIC_AUTH_TOKEN"] == "sk-secret-123"
    assert resolved["ANTHROPIC_BASE_URL"] == "https://api.z.ai/api/anthropic"
    assert resolved["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "1000000"
    assert missing == []


def test_resolve_reports_missing_env_ref_and_leaves_it_empty():
    resolved, missing = loop.resolve_agent_env(
        {}, {"ANTHROPIC_AUTH_TOKEN": "${ZAI_API_KEY}"}, {}
    )
    assert resolved["ANTHROPIC_AUTH_TOKEN"] == ""
    assert missing == ["ZAI_API_KEY"]


def test_profile_value_overrides_base_env_value():
    resolved, _ = loop.resolve_agent_env(
        {"ANTHROPIC_DEFAULT_OPUS_MODEL": "opus"},
        {"ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.2[1m]"},
        {},
    )
    assert resolved["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "glm-5.2[1m]"


def test_resolve_empty_is_noop():
    resolved, missing = loop.resolve_agent_env({}, {}, {})
    assert resolved == {}
    assert missing == []


# ---------------------------------------------------------------------------
# redacted_config: wartości środowiska nie wyciekają do logu (tylko klucze)
# ---------------------------------------------------------------------------

def test_redacted_config_hides_env_values_keeps_keys():
    cfg = {
        "max_iterations": 20,
        "agent_env": {"ANTHROPIC_AUTH_TOKEN": "sk-WPISANY-WPROST-SEKRET"},
        "model_profiles": {"glm": {"ANTHROPIC_BASE_URL": "https://api.z.ai/..."}},
    }
    snap = loop.redacted_config(cfg)
    blob = repr(snap)
    assert "sk-WPISANY-WPROST-SEKRET" not in blob
    assert "https://api.z.ai" not in blob
    # klucze (nazwy zmiennych / profili) zostają jako ślad konfiguracji
    assert "ANTHROPIC_AUTH_TOKEN" in blob
    assert "glm" in blob
    # nietknięte pola configu przechodzą bez zmian; oryginał nie jest mutowany
    assert snap["max_iterations"] == 20
    assert cfg["agent_env"] == {"ANTHROPIC_AUTH_TOKEN": "sk-WPISANY-WPROST-SEKRET"}


# ---------------------------------------------------------------------------
# wiring end-to-end: --model wstrzykuje środowisko do PROCESU agenta
# ---------------------------------------------------------------------------

def test_model_profile_env_reaches_agent_process(tmp_path):
    env = LoopEnv(
        tmp_path, ["good:done.txt"], VERIFY_GREEN,
        config_overrides={
            "model_profiles": {"probe": {"LOOP_TEST_ENV_PROBE": "reached-agent"}}
        },
    )
    rc, out, err = env.run_loop("--model", "probe")
    assert rc == 0, f"stdout:\n{out}\nstderr:\n{err}"

    probe = tmp_path / "agent_env_probe.txt"
    assert probe.exists(), "agent nie dostał nadpisania środowiska z profilu"
    assert probe.read_text(encoding="utf-8") == "reached-agent"


def test_unknown_model_profile_refused_before_run(tmp_path):
    env = LoopEnv(tmp_path, ["good:done.txt"], VERIFY_GREEN)
    rc, out, err = env.run_loop("--model", "nie-ma-takiego")
    assert rc == 2, f"stdout:\n{out}\nstderr:\n{err}"
    assert "model_profiles" in err
    assert env.prompts() == []  # agent nie ruszył
