"""Coverage push for ``visus.desktop.utils.config``.

Targets the missing line ranges 40-55 (linux/darwin/other branches in
get_tesseract_candidate_paths), 119-128 (overlay validation),
202-210 (PATH-fallback / not-found path), 224-235 (validation +
subprocess errors), 255-256 (tessdata not found), 274-275 (missing
modules), 296-297 (pytesseract import error), 309-323 (__getattr__ /
__setattr__ branches), 352-375 (create_config_from_file branches).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from visus.desktop.exceptions import (
    ConfigurationError,
    TesseractNotFoundError,
)
from visus.desktop.utils import config as _cfg


class TestGetTesseractCandidatePaths:
    def test_linux_paths(self):
        with patch.object(_cfg.platform, "system", return_value="Linux"):
            paths = _cfg.get_tesseract_candidate_paths()
        assert "/usr/bin/tesseract" in paths
        assert "/snap/bin/tesseract" in paths

    def test_darwin_paths(self):
        with patch.object(_cfg.platform, "system", return_value="Darwin"):
            paths = _cfg.get_tesseract_candidate_paths()
        assert "/opt/homebrew/bin/tesseract" in paths
        assert "/usr/local/bin/tesseract" in paths

    def test_unknown_os_falls_back_to_unix_defaults(self):
        with patch.object(_cfg.platform, "system", return_value="FreeBSD"):
            paths = _cfg.get_tesseract_candidate_paths()
        assert "/usr/bin/tesseract" in paths


class TestBotVisionConfigValidation:
    @pytest.fixture
    def cfg(self):
        with patch.object(
            _cfg.BotVisionConfig, "_detect_tesseract", lambda self: None
        ):
            return _cfg.BotVisionConfig({"tesseract_path": "/x"})

    def test_invalid_overlay_duration_resets_to_default(self, cfg):
        cfg.config["overlay_duration"] = -5
        cfg._validate_overlay_config()
        assert cfg.config["overlay_duration"] == 1000

    def test_invalid_overlay_duration_type_resets(self, cfg):
        cfg.config["overlay_duration"] = "fast"
        cfg._validate_overlay_config()
        assert cfg.config["overlay_duration"] == 1000

    def test_invalid_overlay_width_resets_to_default(self, cfg):
        cfg.config["overlay_width"] = 0
        cfg._validate_overlay_config()
        assert cfg.config["overlay_width"] == 4

    def test_invalid_overlay_width_type_resets(self, cfg):
        cfg.config["overlay_width"] = "thick"
        cfg._validate_overlay_config()
        assert cfg.config["overlay_width"] == 4


class TestDetectTesseract:
    def test_uses_path_when_candidates_miss(self, tmp_path):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = cfg._load_default_config()
        with patch.object(cfg, "_get_tesseract_paths", return_value=[]), patch(
            "shutil.which", return_value="/usr/local/bin/tesseract"
        ), patch.object(cfg, "_validate_tesseract_path", return_value=True), patch.object(
            cfg, "_get_tessdata_path", return_value=None
        ):
            cfg._detect_tesseract()
        assert cfg.config["tesseract_path"] == "/usr/local/bin/tesseract"

    def test_raises_when_nothing_found(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = cfg._load_default_config()
        with patch.object(cfg, "_get_tesseract_paths", return_value=[]), patch(
            "shutil.which", return_value=None
        ):
            with pytest.raises(TesseractNotFoundError):
                cfg._detect_tesseract()


class TestValidateTesseractPath:
    def _cfg(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {}
        return cfg

    def test_empty_path_returns_false(self):
        assert self._cfg()._validate_tesseract_path("") is False

    def test_nonexistent_path_returns_false(self):
        assert (
            self._cfg()._validate_tesseract_path("/does/not/exist") is False
        )

    def test_subprocess_failure_returns_false(self, tmp_path):
        fake = tmp_path / "tess.exe"
        fake.write_text("x")
        with patch(
            "subprocess.run", side_effect=RuntimeError("boom")
        ):
            assert (
                self._cfg()._validate_tesseract_path(str(fake)) is False
            )

    def test_returncode_nonzero_returns_false(self, tmp_path):
        fake = tmp_path / "tess.exe"
        fake.write_text("x")
        proc = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=proc):
            assert (
                self._cfg()._validate_tesseract_path(str(fake)) is False
            )


class TestGetTessdataPath:
    def _cfg(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        return cfg

    def test_finds_existing_tessdata_sibling(self, tmp_path):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        tessdata = bin_dir / "tessdata"
        tessdata.mkdir()
        result = self._cfg()._get_tessdata_path(str(bin_dir / "tesseract"))
        assert result == str(tessdata)

    def test_returns_none_when_nothing_matches(self, tmp_path):
        result = self._cfg()._get_tessdata_path(
            str(tmp_path / "nowhere" / "tesseract")
        )
        assert result is None


class TestValidateDependencies:
    def test_missing_module_raises_configuration_error(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {}
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pyperclip":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(ConfigurationError, match="pyperclip"):
                cfg._validate_dependencies()


class TestSetupTesseract:
    def test_pytesseract_not_installed_raises_configuration_error(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {"tesseract_path": "/x", "tesseract_data_path": None}
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pytesseract":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(
                ConfigurationError, match="pytesseract is not installed"
            ):
                cfg.setup_tesseract()


class TestAttributeAccess:
    def test_getattr_returns_config_value(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {"my_key": 42}
        assert cfg.my_key == 42

    def test_getattr_raises_for_unknown_attribute(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {}
        with pytest.raises(AttributeError, match="not found"):
            _ = cfg.not_a_real_setting  # noqa: B018 - triggers __getattr__

    def test_setattr_writes_to_config_when_key_known(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {"known": 1}
        cfg.known = 99
        assert cfg.config["known"] == 99

    def test_setattr_writes_to_instance_for_unknown_keys(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {}
        cfg.new_attr = "x"
        assert cfg.new_attr == "x"

    def test_get_with_default(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {"a": 1}
        assert cfg.get("a") == 1
        assert cfg.get("missing", default="fallback") == "fallback"

    def test_set_value(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {}
        cfg.set("k", "v")
        assert cfg.config["k"] == "v"

    def test_update_dict(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {"a": 1}
        cfg.update({"a": 2, "b": 3})
        assert cfg.config == {"a": 2, "b": 3}

    def test_to_dict_returns_a_copy(self):
        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = {"a": 1}
        snap = cfg.to_dict()
        snap["a"] = 99
        assert cfg.config["a"] == 1


class TestCreateConfigFromFile:
    def test_json_file_loaded(self, tmp_path):
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps({"confidence_threshold": 50.0}))
        with patch.object(
            _cfg.BotVisionConfig, "_detect_tesseract", lambda self: None
        ):
            cfg = _cfg.create_config_from_file(str(p))
        assert cfg.config["confidence_threshold"] == 50.0

    def test_yaml_file_loaded_when_pyyaml_present(self, tmp_path):
        pytest.importorskip("yaml")
        p = tmp_path / "cfg.yaml"
        p.write_text("confidence_threshold: 60.0\n")
        with patch.object(
            _cfg.BotVisionConfig, "_detect_tesseract", lambda self: None
        ):
            cfg = _cfg.create_config_from_file(str(p))
        assert cfg.config["confidence_threshold"] == 60.0

    def test_yaml_without_pyyaml_raises_configuration_error(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text("a: 1\n")
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(ConfigurationError, match="PyYAML"):
                _cfg.create_config_from_file(str(p))

    def test_unsupported_extension_raises(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("a = 1")
        with pytest.raises(ConfigurationError, match="Unsupported file format"):
            _cfg.create_config_from_file(str(p))

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _cfg.create_config_from_file(str(tmp_path / "missing.json"))


def test_get_default_config_returns_singleton():
    with patch.object(
        _cfg.BotVisionConfig, "_detect_tesseract", lambda self: None
    ):
        # Force a fresh singleton via the module-level setter.
        _cfg.default_config = None
        first = _cfg.get_default_config()
        second = _cfg.get_default_config()
    assert first is second
