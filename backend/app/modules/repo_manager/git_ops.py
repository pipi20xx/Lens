# -*- coding: utf-8 -*-
"""git 命令层（只做子进程调用，不实现任何 git 协议细节）。

Lens 跑在容器里、以 root 身份工作，所以这一层必须守住几条硬约束：

1. **绝不交互**：GIT_TERMINAL_PROMPT=0，并清空 GIT_ASKPASS / SSH_ASKPASS。
   缺凭证时 git 会直接失败返回，而不是把进程挂在那里等输入。
2. **输出必须可解析**：``--no-pager``、``color.ui=false``、``core.quotepath=false``，
   路径一律用 ``-z``（NUL 分隔）读取，避免中文/空格路径被 git 加引号转义。
3. **凭证不进 argv**：令牌通过 ``GIT_CONFIG_COUNT/GIT_CONFIG_KEY_n`` 环境变量注入
   ``http.extraHeader``，不会出现在 ``ps`` 的进程参数里（argv 对同机用户可见）。
   且只在目标主机与「设置 → 第三方 API 集成」里配置的主机完全一致时才注入，
   避免把令牌发给任意 URL。
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse


class GitError(Exception):
    """带中文可读信息的 git 失败。"""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


# ---------------------------------------------------------------- 环境与调用

def _base_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",   # 缺凭证时立即失败，不挂住
            "GIT_PAGER": "cat",
            "GIT_OPTIONAL_LOCKS": "0",    # 只读命令不抢 index.lock
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
    )
    # 清掉可能被外部继承的交互式助手
    for key in ("GIT_ASKPASS", "SSH_ASKPASS", "SSH_ASKPASS_REQUIRE", "GIT_PREFIX"):
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


async def run(
    cwd: str,
    args: Sequence[str],
    timeout: float = 120.0,
    auth_env: Optional[Dict[str, str]] = None,
    input_bytes: Optional[bytes] = None,
) -> Tuple[int, bytes, str]:
    """执行 git 子进程，返回 (returncode, stdout_bytes, stderr_text)。"""
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        env=_base_env(auth_env),
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(input_bytes), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        raise GitError(f"操作超时（{int(timeout)} 秒），已终止", "timeout")
    return proc.returncode, out or b"", (err or b"").decode("utf-8", "replace")


async def run_ok(
    cwd: str,
    args: Sequence[str],
    timeout: float = 120.0,
    auth_env: Optional[Dict[str, str]] = None,
    input_bytes: Optional[bytes] = None,
) -> str:
    """执行并要求成功，失败时抛带人类可读原因的 GitError。"""
    code, out, err = await run(cwd, args, timeout=timeout, auth_env=auth_env, input_bytes=input_bytes)
    if code != 0:
        raise GitError(humanize(err, args), err.strip())
    return out.decode("utf-8", "surrogateescape")


# ---------------------------------------------------------------- 错误翻译

_PATTERNS: List[Tuple[str, str]] = [
    (r"could not read Username|Authentication failed|invalid username or password",
     "凭证校验失败：请在「系统设置 → 第三方 API 集成」里检查访问令牌是否有效且有仓库读写权限"),
    (r"Permission denied \(publickey\)|no such identity",
     "SSH 公钥被拒绝：容器内没有可用的私钥，或该公钥未添加到远端账号"),
    (r"Repository not found|repository .* does not exist|404",
     "仓库不存在或无权访问：私有仓库需要令牌具备 repo / Contents 权限"),
    (r"Host key verification failed",
     "远端主机指纹未受信：需要把主机 key 加入 known_hosts"),
    (r"would be overwritten by (merge|checkout)|Your local changes to the following files would be overwritten",
     "本地有未提交改动，与远端冲突：请先提交或丢弃这些改动"),
    (r"\[rejected\]|non-fast-forward|fetch first",
     "推送被拒绝：远端有新提交，请先拉取（或使用强制推送并确认风险）"),
    (r"CONFLICT|Automatic merge failed",
     "合并冲突：请解决冲突文件后重新提交"),
    (r"Unable to create .*index\.lock|index\.lock.*File exists",
     "仓库正被另一个 git 进程占用（index.lock）：稍后重试"),
    (r"not a git repository",
     "该目录不是 git 仓库"),
    (r"No configured push destination|no upstream branch",
     "当前分支还没有远端跟踪分支：请先在推送时勾选「设置上游」"),
    (r"Please tell me who you are|unable to auto-detect email address",
     "未配置提交者身份：请在仓库页填写 user.name / user.email"),
    (r"fatal: destination path .* already exists",
     "目标目录已存在且非空"),
    (r"nothing to commit",
     "没有需要提交的改动"),
    (r"did not match any file",
     "指定的文件不存在或已被移动"),
    (r"RPC failed|early EOF|Connection timed out|Could not resolve host|Failed to connect",
     "网络不可达：检查代理设置或远端地址"),
]


def humanize(stderr: str, args: Sequence[str] = ()) -> str:
    text = (stderr or "").strip()
    for pattern, message in _PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return message
    first = next((line for line in text.splitlines() if line.strip()), "")
    if first:
        return first.strip()[:300]
    return f"git {' '.join(args[:2])} 执行失败"


# ---------------------------------------------------------------- 凭证注入

def _provider_hosts(cfg: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """[(host, provider, username)]，来自 config.json 的 gitea / github 段。"""
    out: List[Tuple[str, str, str]] = []

    gh = cfg.get("github") or {}
    gh_base = (gh.get("base") or "https://api.github.com").strip()
    gh_host = urlparse(gh_base).hostname or "api.github.com"
    if gh.get("token"):
        out.append((gh_host, "github", "x-access-token"))
        out.append(("github.com", "github", "x-access-token"))

    gt = cfg.get("gitea") or {}
    gt_base = (gt.get("base") or "").strip()
    if gt.get("token") and gt_base:
        host = urlparse(gt_base if "://" in gt_base else f"http://{gt_base}").hostname
        if host:
            out.append((host, "gitea", (gt.get("username") or "").strip() or "oauth2"))
    return out


def auth_env_for_url(url: str, cfg: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """为 HTTPS 仓库地址构造 http.extraHeader 注入（仅主机精确匹配时）。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None

    host = parsed.hostname.lower()
    for cfg_host, provider, username in _provider_hosts(cfg):
        if (cfg_host or "").lower() != host:
            continue
        section = cfg.get(provider) or {}
        token = (section.get("token") or "").strip()
        if not token:
            continue
        raw = f"{username}:{token}".encode("utf-8")
        value = "Authorization: Basic " + base64.b64encode(raw).decode("ascii")
        return {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": value,
            # 关掉任何 credential helper，避免容器里出现交互式提示
            "GIT_TERMINAL_PROMPT": "0",
        }
    return None


# ---------------------------------------------------------------- status 解析

DECODE_ERR = "surrogateescape"


def _s(raw: bytes) -> str:
    return raw.decode("utf-8", DECODE_ERR)


def _label(x: str, y: str, kind: str) -> str:
    if kind == "untracked":
        return "未跟踪"
    if kind == "conflict":
        return "冲突"
    code = y if y not in (" ", ".") else x
    return {
        "M": "已修改",
        "A": "新增",
        "D": "已删除",
        "R": "重命名",
        "C": "复制",
        "T": "类型变更",
        "U": "冲突",
    }.get(code, "改动")


def _mk_file(path: str, xy: str, kind: str, orig: str = "") -> Dict[str, Any]:
    x = xy[0] if len(xy) > 0 else "."
    y = xy[1] if len(xy) > 1 else "."
    if kind in ("untracked", "conflict"):
        staged, unstaged = False, True
    else:
        staged = x not in (".", " ")
        unstaged = y not in (".", " ")
    return {
        "path": path,
        "orig_path": orig,
        "xy": xy,
        "kind": kind,
        "label": _label(x, y, kind),
        "staged": staged,
        "unstaged": unstaged,
    }


STATUS_ARGS = [
    "-c", "color.ui=false",
    "-c", "core.quotepath=false",
    "status",
    "--porcelain=v2",
    "-z",
    "--branch",
    "--untracked-files=normal",
]


def parse_status(raw: bytes) -> Dict[str, Any]:
    branch = {
        "oid": "", "head": "", "upstream": "", "ahead": 0, "behind": 0, "detached": False,
    }
    files: List[Dict[str, Any]] = []
    toks = raw.split(b"\x00")
    i, n = 0, len(toks)

    while i < n:
        tok = toks[i]
        i += 1
        if not tok:
            continue

        if tok.startswith(b"# "):
            line = _s(tok[2:])
            if line.startswith("branch.oid "):
                branch["oid"] = line[len("branch.oid "):].strip()
            elif line.startswith("branch.head "):
                head = line[len("branch.head "):].strip()
                branch["detached"] = head == "(detached)"
                branch["head"] = "" if branch["detached"] else head
            elif line.startswith("branch.upstream "):
                branch["upstream"] = line[len("branch.upstream "):].strip()
            elif line.startswith("branch.ab "):
                m = re.match(r"\+(\d+)\s+-(\d+)", line[len("branch.ab "):].strip())
                if m:
                    branch["ahead"], branch["behind"] = int(m.group(1)), int(m.group(2))
            continue

        kind_byte = tok[0:1]
        if kind_byte == b"1":
            parts = tok.split(b" ", 8)
            if len(parts) < 9:
                continue
            files.append(_mk_file(_s(parts[8]), _s(parts[1]), "change"))
        elif kind_byte == b"2":
            parts = tok.split(b" ", 9)
            if len(parts) < 10:
                continue
            orig = _s(toks[i]) if i < n else ""
            i += 1
            files.append(_mk_file(_s(parts[9]), _s(parts[1]), "rename", orig))
        elif kind_byte == b"u":
            parts = tok.split(b" ", 10)
            if len(parts) < 11:
                continue
            files.append(_mk_file(_s(parts[10]), _s(parts[1]), "conflict"))
        elif kind_byte == b"?":
            files.append(_mk_file(_s(tok[2:]), "??", "untracked"))

    counts = {
        "staged": sum(1 for f in files if f["staged"]),
        "unstaged": sum(1 for f in files if f["unstaged"] and f["kind"] != "untracked"),
        "untracked": sum(1 for f in files if f["kind"] == "untracked"),
        "conflict": sum(1 for f in files if f["kind"] == "conflict"),
    }
    return {"branch": branch, "files": files, "counts": counts}


async def status(repo: str, timeout: float = 60.0) -> Dict[str, Any]:
    code, out, err = await run(repo, STATUS_ARGS, timeout=timeout)
    if code != 0:
        raise GitError(humanize(err, ["status"]), err.strip())
    return parse_status(out)


# ---------------------------------------------------------------- 变更操作

async def stage(repo: str, paths: Sequence[str]) -> None:
    await run_ok(repo, ["add", "-A", "--", *paths])


async def unstage(repo: str, paths: Sequence[str]) -> None:
    code, _, err = await run(repo, ["restore", "--staged", "--", *paths])
    if code != 0:
        # 尚无任何提交（unborn HEAD）时 restore --staged 不可用
        await run_ok(repo, ["rm", "--cached", "-r", "--quiet", "--", *paths])


async def discard(repo: str, paths: Sequence[str]) -> List[str]:
    """丢弃工作区改动：已跟踪的 restore，未跟踪的 clean。返回被清理的路径。"""
    cleaned: List[str] = []
    code, _, err = await run(repo, ["restore", "--worktree", "--", *paths])
    if code == 0:
        cleaned.extend(paths)
    code2, _, err2 = await run(repo, ["clean", "-fd", "--", *paths])
    if code2 == 0 and code != 0:
        cleaned.extend(paths)
    if code != 0 and code2 != 0:
        text = (err or "") + (err2 or "")
        if "did not match" in text or "No such file" in text:
            raise GitError("这些路径没有可丢弃的工作区改动")
        raise GitError(humanize(text, ["restore"]), text.strip())
    return cleaned


async def resolve_conflict(repo: str, path: str, strategy: str) -> None:
    side = "--ours" if strategy == "ours" else "--theirs"
    await run_ok(repo, ["checkout", side, "--", path])
    await run_ok(repo, ["add", "-A", "--", path])


async def commit(repo: str, message: str, amend: bool = False,
                 author_name: str = "", author_email: str = "") -> Dict[str, Any]:
    args = ["commit", "--no-gpg-sign", "-F", "-"]
    if amend:
        args.insert(1, "--amend")
    env: Dict[str, str] = {}
    if author_name:
        env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = author_name
    if author_email:
        env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = author_email

    code, out, err = await run(repo, args, input_bytes=message.encode("utf-8"), auth_env=env or None)
    if code != 0:
        raise GitError(humanize(err, ["commit"]), err.strip())
    text = out.decode("utf-8", "replace") + err
    m = re.search(r"\[[^\]]*?\s([0-9a-f]{7,40})\]", text)
    summary = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return {"commit": m.group(1) if m else "", "summary": summary}


# ---------------------------------------------------------------- 远端同步

_PROGRESS_RE = re.compile(r"(Writing|Receiving|Resolving|Counting|Compressing|Enumerating)[^%]*?(\d{1,3})%")


async def _stream(
    repo: str,
    args: Sequence[str],
    timeout: float,
    auth_env: Optional[Dict[str, str]] = None,
    on_line: Optional[Callable[[str], None]] = None,
) -> Tuple[int, str]:
    """流式执行（clone / push 用），逐行回调 stderr 以便解析进度。"""
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=repo, env=_base_env(auth_env),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    collected: List[str] = []

    async def pump_stderr():
        assert proc.stderr is not None
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            text = line.decode("utf-8", "replace").rstrip()
            if not text:
                continue
            collected.append(text)
            if on_line:
                on_line(text)

    async def drain_stdout() -> bytes:
        assert proc.stdout is not None
        return await proc.stdout.read()

    try:
        _, stdout_data = await asyncio.wait_for(
            asyncio.gather(pump_stderr(), drain_stdout()), timeout=timeout
        )
        code = await proc.wait()
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        raise GitError(f"操作超时（{int(timeout)} 秒），已终止", "timeout")
    text = "\n".join(collected)
    extra = stdout_data.decode("utf-8", "replace").strip() if stdout_data else ""
    if extra:
        text = f"{text}\n{extra}".strip()
    return code, text


def progress_of(line: str) -> Optional[int]:
    m = _PROGRESS_RE.search(line)
    return int(m.group(2)) if m else None


async def push(
    repo: str,
    set_upstream: bool = False,
    force: bool = False,
    auth_env: Optional[Dict[str, str]] = None,
    on_line: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    args = ["push", "--porcelain", "--progress"]
    if force:
        args.append("--force-with-lease")
    if set_upstream:
        args.extend(["-u", "origin", "HEAD"])
    code, text = await _stream(repo, args, 300.0, auth_env=auth_env, on_line=on_line)
    if code != 0:
        raise GitError(humanize(text, ["push"]), text.strip())
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("To ")]
    return {"ok": True, "detail": lines[-1] if lines else "已推送"}


async def pull(repo: str, rebase: bool = False,
               auth_env: Optional[Dict[str, str]] = None,
               on_line: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    args = ["pull", "--no-edit", "--rebase" if rebase else "--ff-only"]
    code, text = await _stream(repo, args, 300.0, auth_env=auth_env, on_line=on_line)
    if code != 0:
        raise GitError(humanize(text, ["pull"]), text.strip())
    return {"ok": True, "detail": text.strip().splitlines()[-1] if text.strip() else "已是最新"}


async def fetch(repo: str, timeout: float = 180.0,
                auth_env: Optional[Dict[str, str]] = None) -> None:
    code, _, err = await run(repo, ["fetch", "--prune", "--quiet"],
                             timeout=timeout, auth_env=auth_env)
    if code != 0:
        raise GitError(humanize(err, ["fetch"]), err.strip())


# ---------------------------------------------------------------- 分支 / 历史

async def branches(repo: str) -> List[Dict[str, Any]]:
    fmt = "%(refname:short)%09%(HEAD)%09%(upstream:short)%09%(committerdate:iso-strict)"
    out = await run_ok(repo, ["for-each-ref", "--sort=-committerdate",
                              f"--format={fmt}", "refs/heads"])
    result = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        while len(parts) < 4:
            parts.append("")
        current = parts[1].strip() == "*"
        result.append({
            "name": parts[0].strip(),
            "current": current,
            "upstream": parts[2].strip(),
            "date": parts[3].strip(),
        })
    return result


async def switch_branch(repo: str, name: str) -> None:
    await run_ok(repo, ["switch", name])


async def create_branch(repo: str, name: str, checkout: bool = True) -> None:
    await run_ok(repo, ["switch", "-c", name] if checkout else ["branch", name])


async def delete_branch(repo: str, name: str, force: bool = False) -> None:
    await run_ok(repo, ["branch", "-D" if force else "-d", name])


async def log(repo: str, limit: int = 50) -> List[Dict[str, Any]]:
    fmt = "%H%x1f%h%x1f%an%x1f%ae%x1f%ad%x1f%s%x1f%D%x1e"
    code, out, err = await run(repo, ["log", f"-n{max(1, min(limit, 200))}",
                                      "--date=iso", f"--pretty=format:{fmt}"])
    if code != 0:
        if "does not have any commits" in err or "unknown revision" in err:
            return []
        raise GitError(humanize(err, ["log"]), err.strip())
    text = out.decode("utf-8", "surrogateescape")
    commits = []
    for rec in text.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        f = rec.split("\x1f")
        while len(f) < 7:
            f.append("")
        commits.append({
            "hash": f[0], "short": f[1], "author": f[2], "email": f[3],
            "date": f[4], "subject": f[5],
            "refs": [r.strip() for r in f[6].split(",") if r.strip()],
        })
    return commits


async def diff(repo: str, path: str = "", staged: bool = False,
               untracked: bool = False, max_chars: int = 400_000) -> str:
    common = ["--no-color", "--no-ext-diff", "-U3"]
    if untracked and path:
        code, out, _ = await run(
            repo, ["diff", "--no-index", *common, "--", os.devnull, path], timeout=60.0
        )
    else:
        args = ["diff", *common]
        if staged:
            args.append("--cached")
        if path:
            args.extend(["--", path])
        code, out, err = await run(repo, args, timeout=60.0)
    text = out.decode("utf-8", "surrogateescape")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (内容过长，已截断)"
    return text


async def remote_url(repo: str, remote: str = "origin") -> str:
    code, out, err = await run(repo, ["remote", "get-url", remote])
    if code != 0:
        return ""
    return out.decode("utf-8", "surrogateescape").strip()


# ---------------------------------------------------------------- 提交者身份

_IDENT_RE = re.compile(r"^(.*?)\s*<(.*?)>\s*\d+\s+[+-]\d{4}$")


async def _config_get(repo: str, key: str, local: bool = False) -> str:
    args = ["config"] + (["--local"] if local else []) + ["--get", key]
    code, out, _ = await run(repo, args)
    return out.decode("utf-8", "replace").strip() if code == 0 else ""


async def get_identity(repo: str) -> Dict[str, Any]:
    """读取仓库级身份配置，以及 git 自己算出来的「最终生效身份」。"""
    local_name = await _config_get(repo, "user.name", local=True)
    local_email = await _config_get(repo, "user.email", local=True)
    global_name = await _config_get(repo, "user.name")
    global_email = await _config_get(repo, "user.email")

    effective: Dict[str, str] = {}
    code, out, _ = await run(repo, ["var", "GIT_COMMITTER_IDENT"])
    if code == 0:
        match = _IDENT_RE.match(out.decode("utf-8", "replace").strip())
        if match:
            effective = {"name": match.group(1).strip(), "email": match.group(2).strip()}

    return {
        "local": {"name": local_name, "email": local_email},
        "resolved": {"name": global_name, "email": global_email},
        "effective": effective,
    }


async def set_identity(repo: str, name: str, email: str) -> None:
    """把身份写进仓库自己的 .git/config（清空则移除该键）。"""
    for key, value in (("user.name", name), ("user.email", email)):
        if value:
            await run_ok(repo, ["config", "--local", key, value])
        else:
            # 键不存在时 unset 会返回非 0，忽略即可
            await run(repo, ["config", "--local", "--unset", key])


def provider_for_url(url: str, cfg: Dict[str, Any]) -> str:
    """按地址主机判断它属于哪个已配置的 provider（用于克隆后自动套用身份）。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    host = (parsed.hostname or "").lower()
    if not host:
        return ""
    for cfg_host, provider, _username in _provider_hosts(cfg):
        if (cfg_host or "").lower() == host:
            return provider
    return ""


# ---------------------------------------------------------------- 提交详情

_REV_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")


def check_rev(rev: str) -> str:
    """提交号只接受十六进制，避免被当成 git 选项注入。"""
    rev = (rev or "").strip()
    if not _REV_RE.match(rev):
        raise GitError("提交号不合法")
    return rev


async def commit_detail(repo: str, rev: str) -> Dict[str, Any]:
    """单个提交的元信息 + 本次改动的文件清单（含增删行数）。"""
    rev = check_rev(rev)

    fmt = "%H%x1f%h%x1f%an%x1f%ae%x1f%ad%x1f%s%x1f%b"
    code, out, err = await run(repo, ["show", "-s", "--date=iso", f"--pretty=format:{fmt}", rev])
    if code != 0:
        raise GitError(humanize(err, ["show"]), err.strip())

    fields = out.decode("utf-8", "surrogateescape").split("\x1f")
    while len(fields) < 7:
        fields.append("")
    commit = {
        "hash": fields[0].strip(),
        "short": fields[1].strip(),
        "author": fields[2].strip(),
        "email": fields[3].strip(),
        "date": fields[4].strip(),
        "subject": fields[5].strip(),
        "body": fields[6].strip(),
    }

    files: List[Dict[str, Any]] = []
    code, out, _ = await run(
        repo, ["diff-tree", "--no-commit-id", "-r", "--root", "--name-status", "-z", rev]
    )
    if code == 0:
        tokens = [token for token in out.split(b"\x00") if token]
        index = 0
        while index + 1 < len(tokens):
            status = tokens[index].decode("ascii", "replace")[:1] or "M"
            path = tokens[index + 1].decode("utf-8", "surrogateescape")
            files.append({
                "status": status,
                "path": path,
                "additions": 0,
                "deletions": 0,
            })
            index += 2

    code, out, _ = await run(
        repo, ["diff-tree", "--no-commit-id", "-r", "--root", "--numstat", "-z", rev]
    )
    if code == 0:
        stats: Dict[str, tuple] = {}
        for record in [token for token in out.split(b"\x00") if token]:
            parts = record.split(b"\t")
            if len(parts) < 3:
                continue
            path = b"\t".join(parts[2:]).decode("utf-8", "surrogateescape")
            try:
                stats[path] = (int(parts[0]), int(parts[1]))
            except ValueError:
                stats[path] = (0, 0)   # 二进制文件是 "-\t-\tpath"
        for item in files:
            item["additions"], item["deletions"] = stats.get(item["path"], (0, 0))

    return {"commit": commit, "files": files}


async def commit_file_diff(repo: str, rev: str, path: str,
                           max_chars: int = 400_000) -> str:
    """某个提交里单个文件的 patch。"""
    rev = check_rev(rev)
    args = ["diff-tree", "--no-commit-id", "-p", "--root", "--no-color", "--no-ext-diff", "-U3", rev]
    if path:
        args.extend(["--", path])
    code, out, err = await run(repo, args, timeout=60.0)
    if code != 0:
        raise GitError(humanize(err, ["diff-tree"]), err.strip())
    text = out.decode("utf-8", "surrogateescape")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (内容过长，已截断)"
    return text


# ---------------------------------------------------------------- 克隆

async def clone(url: str, dest: str, auth_env: Optional[Dict[str, str]] = None,
                on_line: Optional[Callable[[str], None]] = None,
                depth: int = 0) -> Dict[str, Any]:
    parent = os.path.dirname(dest.rstrip("/")) or "."
    os.makedirs(parent, exist_ok=True)
    args = ["clone", "--progress", "--no-hardlinks"]
    if depth and depth > 0:
        args.extend(["--depth", str(depth)])
    args.extend(["--", url, dest])
    code, text = await _stream(parent, args, 1800.0, auth_env=auth_env, on_line=on_line)
    if code != 0:
        raise GitError(humanize(text, ["clone"]), text.strip())
    return {"ok": True, "path": dest}
