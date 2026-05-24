"""hamstern /hams:dashboard 의 local serve 모드.

plugin 정적 자산 (docs/{index,app,style}) + project 데이터 (.hamstern/dashboard-data/) 를
path 분기로 동시 serve. 동적 포트 (OS 할당). Stdlib only.
"""
from __future__ import annotations

import argparse
import socket
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path


class HamsHandler(SimpleHTTPRequestHandler):
    plugin_dir: Path = None
    data_dir: Path = None

    def translate_path(self, path: str) -> str:
        # self=None 호출 (단위 테스트) 과 인스턴스 호출 (HTTPServer) 모두 지원.
        cls = type(self) if self is not None else HamsHandler
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/data/"):
            return cls._safe_join(cls.data_dir, path[len("/data/"):])
        if path in ("/", ""):
            path = "/index.html"
        return cls._safe_join(cls.plugin_dir, path.lstrip("/"))

    @classmethod
    def _safe_join(cls, base: Path, rel: str) -> str:
        """base 의 자손인지 검증 후 path 반환. 탈출 시 sentinel (존재하지 않는 path) 반환 → 404."""
        candidate = (base / rel).resolve()
        base_resolved = base.resolve()
        try:
            candidate.relative_to(base_resolved)
        except ValueError:
            return str(base_resolved / "__forbidden__")
        return str(candidate)

    def log_message(self, fmt, *args):
        pass


def pick_port() -> int:
    """OS 가 할당한 자유 포트 (ephemeral range)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
