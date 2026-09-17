"""The example environment file should track public app configuration."""

from pathlib import Path

from authentic_dynamics.config import Config


def test_example_env_covers_runtime_config_without_a_secret():
    example = Path(__file__).resolve().parents[1] / "example.env"
    assignments = [line for line in example.read_text().splitlines() if line.startswith("AD_")]
    names = [line.split("=", 1)[0] for line in assignments]
    expected = {
        f"AD_{name}"
        for name in vars(Config)
        if name.isupper() and name not in {"DEBUG", "TESTING"}
    }

    assert len(names) == len(set(names))
    assert set(names) == expected
    assert "AD_SECRET_KEY=" in assignments
