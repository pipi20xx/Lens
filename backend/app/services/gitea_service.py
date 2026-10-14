# -*- coding: utf-8 -*-
"""兼容 shim：实现已移至 git_repo_service.py（现在同时支持 Gitea 与 GitHub）。"""
from app.services.git_repo_service import (  # noqa: F401
    GitRepoService,
    PROVIDERS,
    humanize_error,
)

__all__ = ["GitRepoService", "PROVIDERS", "humanize_error"]
