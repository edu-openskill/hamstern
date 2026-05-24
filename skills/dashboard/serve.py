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
        if path in ("/", ""):
            path = "/index.html"
        rel = path.lstrip("/")
        return str(cls.plugin_dir / rel)

    def log_message(self, fmt, *args):
        pass
