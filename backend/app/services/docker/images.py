"""镜像操作：列表、详情、增删、导入导出、拉取进度、远程更新检查。"""
import os
import re
import json
import time
import uuid
import paramiko
from typing import List, Dict, Any, Optional

from app.utils.logger import logger

from .base import DockerServiceBase


class ImageOpsMixin(DockerServiceBase):
    _images_cache = {}  # { host_id: (data, timestamp) }
    _pull_tasks = {}  # { task_id: {...} } 镜像拉取任务进度（全主机共享，task_id 含 host 前缀）

    async def get_image_update_info(self, image_tag: str):
        """
        获取镜像的更新信息。支持 Docker Hub 以及第三方仓库 (如 lscr.io, ghcr.io)。
        """
        if not image_tag: return None
        
        # 1. 解析镜像名与仓库地址
        # lscr.io/linuxserver/qbittorrent:latest -> host=lscr.io, repo=linuxserver/qbittorrent, tag=latest
        # nginx -> host=registry-1.docker.io, repo=library/nginx, tag=latest
        parts = image_tag.split("/")
        host = "registry-1.docker.io"
        repo = ""
        tag = "latest"
        
        full_repo_path = image_tag
        if ":" in image_tag:
            full_repo_path, tag = image_tag.rsplit(":", 1)
            
        if "." in parts[0] or ":" in parts[0]:
            host = parts[0]
            repo = "/".join(parts[1:])
            if ":" in repo: repo = repo.rsplit(":", 1)[0]
        else:
            repo = full_repo_path
            if "/" not in repo:
                repo = f"library/{repo}"
        
        # 修正 Docker Hub 的主机名
        reg_host = host
        if host == "docker.io": reg_host = "registry-1.docker.io"
            
        # 2. 获取本地 RepoDigests
        local_digests = []
        res = self.exec_command(f"docker inspect --format='{{{{json .RepoDigests}}}}' {image_tag}", log_error=False)
        if res["success"] and res["stdout"].strip():
            try:
                import json
                local_digests = json.loads(res["stdout"])
            except Exception: pass
            
        if not local_digests and self.client:
            try:
                img = self.client.images.get(image_tag)
                local_digests = img.attrs.get("RepoDigests", [])
            except Exception: pass
            
        # 3. 动态获取远程 Digest (支持 OCI 挑战认证)
        remote_digest = ""
        try:
            from app.utils.http_client import get_async_client
            # 扩展 Accept 头，支持多架构镜像清单
            accept_headers = (
                "application/vnd.docker.distribution.manifest.v2+json, "
                "application/vnd.docker.distribution.manifest.list.v2+json, "
                "application/vnd.oci.image.manifest.v1+json, "
                "application/vnd.oci.image.index.v1+json"
            )
            
            async with get_async_client(timeout=15.0) as client:
                manifest_url = f"https://{reg_host}/v2/{repo}/manifests/{tag}"
                headers = {"Accept": accept_headers}
                
                # 显式开启重定向跟随
                res = await client.get(manifest_url, headers=headers, follow_redirects=True)
                
                if res.status_code == 401:
                    auth_header = res.headers.get("WWW-Authenticate", "")
                    if "Bearer" in auth_header:
                        import re
                        realm = re.search(r'realm="([^"]+)"', auth_header).group(1)
                        service_match = re.search(r'service="([^"]+)"', auth_header)
                        service = service_match.group(1) if service_match else ""
                        scope_match = re.search(r'scope="([^"]+)"', auth_header)
                        scope = scope_match.group(1) if scope_match else f"repository:{repo}:pull"
                        
                        auth_params = {"scope": scope}
                        if service: auth_params["service"] = service
                        
                        auth_res = await client.get(realm, params=auth_params, follow_redirects=True)
                        if auth_res.status_code == 200:
                            token = auth_res.json().get("token") or auth_res.json().get("access_token")
                            headers["Authorization"] = f"Bearer {token}"
                            res = await client.get(manifest_url, headers=headers, follow_redirects=True)
                
                if res.status_code == 200:
                    remote_digest = res.headers.get("Docker-Content-Digest", "")
                else:
                    logger.debug(f"HTTP {res.status_code} for {manifest_url}")
        except Exception as e:
            logger.warning(f"Failed to fetch remote digest for {image_tag} on {host}: {e}")

        # 4. 对比判定
        has_update = False
        if remote_digest:
            is_latest = any(remote_digest in d for d in local_digests)
            has_update = not is_latest
            status_text = "发现新版本" if has_update else "已是最新"
            logger.info(f"🔍 [镜像检测] 站点: {host} | 镜像: {repo}:{tag}")
            logger.info(f"   ┣ 本地指纹: {local_digests}")
            logger.info(f"   ┣ 远程指纹: {remote_digest}")
            logger.info(f"   ┗ 判定结果: {status_text}")
        else:
            logger.warning(f"⚠️ [镜像检测] 无法获取远程指纹: {image_tag} (Host: {host})")

        return {
            "image": image_tag,
            "local_digests": local_digests,
            "remote_digest": remote_digest,
            "has_update": has_update
        }

    # ==================== 镜像管理 ====================

    _SAFE_REF_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.\-/:@]+$")

    @classmethod
    def _ensure_safe_ref(cls, ref: str) -> str:
        """校验镜像引用/ID 合法性，防止 CLI 兜底时被注入"""
        if not ref or len(ref) > 300 or not cls._SAFE_REF_RE.fullmatch(ref):
            raise Exception(f"非法的镜像引用: {ref}")
        return ref

    @staticmethod
    def _format_size(size_bytes) -> str:
        try:
            size = float(size_bytes or 0)
        except (TypeError, ValueError):
            return "--"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @staticmethod
    def _format_created(created) -> str:
        """将镜像创建时间转为相对时间描述"""
        if not created:
            return "--"
        try:
            import datetime
            if isinstance(created, (int, float)):
                dt = datetime.datetime.utcfromtimestamp(created)
            else:
                dt = datetime.datetime.fromisoformat(str(created).split(".")[0].replace("Z", ""))
            delta = datetime.datetime.utcnow() - dt
            if delta.days > 0: return f"{delta.days} 天前"
            hours, remainder = divmod(delta.seconds, 3600)
            if hours > 0: return f"{hours} 小时前"
            return f"{max(remainder // 60, 1)} 分钟前"
        except Exception:
            return str(created)

    @staticmethod
    def _split_image_tag(ref: str):
        """拆分镜像名与标签（正确处理 registry 带端口的情形）"""
        colon, slash = ref.rfind(":"), ref.rfind("/")
        if colon > slash:
            return ref[:colon], ref[colon + 1:]
        return ref, "latest"

    def _invalidate_images_cache(self):
        self._images_cache.pop(f"{self.host_id}_images", None)

    def list_images(self) -> List[Dict[str, Any]]:
        """获取镜像列表（含占用状态），SDK 失败时回退 docker images CLI"""
        cache_key = f"{self.host_id}_images"
        if cache_key in self._images_cache:
            data, ts = self._images_cache[cache_key]
            if time.time() - ts < 5:
                return data

        # 容器占用映射：镜像完整ID -> [容器名]
        used_map = {}
        if self.client:
            try:
                for c in self.client.containers.list(all=True):
                    try:
                        used_map.setdefault(c.image.id, []).append(c.name)
                    except Exception:
                        continue
            except Exception as e:
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"[Docker] 获取容器占用信息失败: {e}")

        results = []
        if self.client:
            try:
                for img in self.client.images.list(all=True):
                    tags = img.tags or []
                    used_by = used_map.get(img.id, [])
                    results.append({
                        "id": img.short_id,
                        "full_id": img.id,
                        "tags": tags,
                        "repo_tag": tags[0] if tags else "<none>:<none>",
                        "size": self._format_size(img.attrs.get("Size")),
                        "created": self._format_created(img.attrs.get("Created")),
                        "in_use": bool(used_by),
                        "used_by": used_by,
                        "dangling": not tags,
                    })
                self._images_cache[cache_key] = (results, time.time())
                return results
            except Exception as e:
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py images.list failed, falling back to CLI: {e}")

        # CLI 兜底：docker images -a，占用状态通过 docker ps -a 的镜像名交叉比对
        res = self.exec_command("docker images -a --format '{{json .}}'", log_error=False)
        if res["success"]:
            try:
                cli_used = {}
                ps_res = self.exec_command("docker ps -a --format '{{json .}}'", log_error=False)
                if ps_res["success"]:
                    for line in ps_res["stdout"].strip().split("\n"):
                        if not line: continue
                        try:
                            cc = json.loads(line)
                            cli_used.setdefault(cc.get("Image"), []).append(cc.get("Names"))
                        except Exception: continue

                for line in res["stdout"].strip().split("\n"):
                    if not line: continue
                    try:
                        m = json.loads(line)
                    except Exception: continue
                    repo, tag = m.get("Repository", ""), m.get("Tag", "")
                    ref = f"{repo}:{tag}" if repo and repo != "<none>" else "<none>:<none>"
                    used_by = cli_used.get(ref, []) or cli_used.get(m.get("ID"), [])
                    results.append({
                        "id": (m.get("ID") or "")[:12],
                        "full_id": m.get("ID"),
                        "tags": [ref] if repo and repo != "<none>" else [],
                        "repo_tag": ref,
                        "size": m.get("Size"),
                        "created": m.get("CreatedSince"),
                        "in_use": bool(used_by),
                        "used_by": used_by,
                        "dangling": not repo or repo == "<none>",
                    })
                self._images_cache[cache_key] = (results, time.time())
            except Exception as e:
                logger.error(f"Failed to parse docker images output: {e}")
        return results

    def get_image_info(self, image_id: str) -> Dict[str, Any]:
        """获取镜像 inspect 详情，SDK 失败时回退 docker inspect"""
        self._ensure_safe_ref(image_id)
        if self.client:
            try:
                return self.client.images.get(image_id).attrs
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py inspect failed, falling back to CLI: {e}")
        res = self.exec_command(f"docker inspect {image_id}")
        if res["success"]:
            try:
                data = json.loads(res["stdout"])
                if isinstance(data, list) and data:
                    return data[0]
            except Exception:
                pass
        raise Exception(res.get("stderr") or f"无法获取镜像 {image_id[:12]} 详情")

    def remove_image(self, image_id: str, force: bool = False) -> bool:
        """删除镜像，SDK 失败时回退 docker rmi"""
        self._ensure_safe_ref(image_id)
        if self.client:
            try:
                self.client.images.remove(image_id, force=force)
                self._invalidate_images_cache()
                return True
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                if "image is being used" in str(e) or "conflict" in str(e).lower():
                    raise Exception(f"镜像 {image_id[:12]} 正被容器使用，无法删除（可尝试强制删除）")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py remove failed, falling back to CLI: {e}")
        res = self.exec_command(f"docker rmi {'-f ' if force else ''}{image_id}")
        if res["success"]:
            self._invalidate_images_cache()
            return True
        raise Exception(res.get("stderr") or "docker rmi 执行失败")

    def tag_image(self, image_id: str, repo: str, tag: str = "latest") -> bool:
        """为镜像打标签，SDK 失败时回退 docker tag"""
        self._ensure_safe_ref(image_id)
        self._ensure_safe_ref(f"{repo}:{tag}")
        if self.client:
            try:
                image = self.client.images.get(image_id)
                if image.tag(repo, tag):
                    self._invalidate_images_cache()
                    return True
                raise Exception("打标签失败")
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py tag failed, falling back to CLI: {e}")
        res = self.exec_command(f"docker tag {image_id} {repo}:{tag}")
        if res["success"]:
            self._invalidate_images_cache()
            return True
        raise Exception(res.get("stderr") or "docker tag 执行失败")

    @classmethod
    def register_pull_task(cls, host_id: str, image_ref: str) -> str:
        """登记一个拉取任务并返回 task_id，同时清理 1 小时前的已完成任务"""
        now = time.time()
        for tid in list(cls._pull_tasks.keys()):
            t = cls._pull_tasks[tid]
            if t.get("done") and now - (t.get("finished_at") or now) > 3600:
                del cls._pull_tasks[tid]
        task_id = f"{host_id}_{int(now * 1000)}_{uuid.uuid4().hex[:6]}"
        cls._pull_tasks[task_id] = {
            "host_id": host_id, "image": image_ref, "status": "pending",
            "lines": [], "layers": {}, "done": False, "success": False,
            "error": None, "created_at": now, "finished_at": None,
        }
        return task_id

    @classmethod
    def get_pull_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        return cls._pull_tasks.get(task_id)

    def pull_image(self, task_id: str, image_ref: str) -> None:
        """阻塞执行镜像拉取，进度实时写入 _pull_tasks（由 API 层放入后台线程调用）"""
        task = self._pull_tasks.get(task_id)
        if task is None:
            return
        self._ensure_safe_ref(image_ref)
        task["status"] = "running"
        try:
            if self.client:
                repo, tag = self._split_image_tag(image_ref)
                stream = self.client.api.pull(repo, tag=tag, stream=True, decode=True)
                try:
                    for chunk in stream:
                        err = chunk.get("error")
                        if err:
                            raise Exception(err)
                        layer = chunk.get("id")
                        status = chunk.get("status", "")
                        progress = chunk.get("progress", "")
                        if layer and status in ("Downloading", "Extracting", "Waiting", "Verifying Checksum"):
                            task["layers"][layer] = {"status": status, "progress": progress}
                        elif status.startswith(("Status", "Digest")):
                            task["lines"].append(status)
                        elif status in ("Pull complete", "Already exists", "Download complete"):
                            task["lines"].append(f"{layer or ''} {status}".strip())
                        if len(task["lines"]) > 50:
                            task["lines"] = task["lines"][-50:]
                finally:
                    # 显式关闭流，避免 SSH 隧道通道泄漏
                    try:
                        stream.close()
                    except Exception:
                        pass
                task["success"] = True
                task["status"] = "success"
            else:
                res = self.exec_command(f"docker pull {image_ref}", timeout=1800)
                task["lines"] = [l for l in (res.get("stdout") or "").strip().split("\n") if l][-50:]
                if not res["success"]:
                    raise Exception(res.get("stderr") or "docker pull 执行失败")
                task["success"] = True
                task["status"] = "success"
        except Exception as e:
            self._invalidate_client_on_ssh_error(e)
            task["success"] = False
            task["status"] = "failed"
            task["error"] = str(e)
            logger.error(f"[Docker] 拉取镜像失败 {image_ref}: {e}")
        finally:
            task["done"] = True
            task["finished_at"] = time.time()
            self._invalidate_images_cache()

    @staticmethod
    def _spool_to_temp(fileobj) -> str:
        """将上传的文件流分块落盘为临时文件，返回路径"""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".tar")
        with os.fdopen(fd, "wb") as tmp:
            while True:
                chunk = fileobj.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        return path

    def export_image(self, image_id: str, output_path: str) -> bool:
        """导出镜像为 tar 文件（docker save）。SSH 主机走独立连接的 CLI+SFTP，避免长时间占用 docker-py 隧道通道"""
        self._ensure_safe_ref(image_id)

        if self.host_config.get("type") == "ssh":
            remote_tmp = f"/tmp/lens_image_export_{int(time.time())}.tar"
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.host_config.get("ssh_host"),
                port=self.host_config.get("ssh_port", 22),
                username=self.host_config.get("ssh_user", "root"),
                password=self.host_config.get("ssh_pass"),
                timeout=15,
            )
            try:
                _, stdout, stderr = ssh.exec_command(f"docker save -o {remote_tmp} {image_id}", timeout=1800)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    err = stderr.read().decode().strip()
                    raise Exception(err or "docker save 执行失败")
                sftp = ssh.open_sftp()
                try:
                    sftp.get(remote_tmp, output_path)
                finally:
                    sftp.close()
                return True
            finally:
                try:
                    ssh.exec_command(f"rm -f {remote_tmp}", timeout=30)
                except Exception:
                    pass
                ssh.close()

        if self.client:
            try:
                image = self.client.images.get(image_id)
                with open(output_path, "wb") as f:
                    for chunk in image.save():
                        f.write(chunk)
                return True
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py save failed, falling back to CLI: {e}")

        # 本地 CLI 兜底
        res = self.exec_command(f"docker save -o {output_path} {image_id}", timeout=1800)
        if res["success"]:
            return True
        raise Exception(res.get("stderr") or "docker save 执行失败")

    @staticmethod
    def _clean_load_result(result) -> List[str]:
        """整理 docker load 的返回流为纯文本行（只保留末尾若干行，最关键的 Loaded image 信息在末尾）"""
        lines = []
        for item in (result or []):
            if isinstance(item, bytes):
                text = item.decode("utf-8", "replace")
            elif isinstance(item, dict):
                text = item.get("stream") or item.get("error") or ""
                if isinstance(text, bytes):
                    text = text.decode("utf-8", "replace")
                if not text:
                    text = json.dumps(item, ensure_ascii=False, default=str)
            else:
                text = str(item)
            text = text.strip()
            if text:
                lines.append(text)
        return lines[-30:]

    def load_image(self, fileobj) -> List[str]:
        """从 tar 文件导入镜像（docker load），SDK 失败时回退 CLI，返回可读的结果文本行"""
        if self.client:
            try:
                try:
                    fileobj.seek(0)
                except Exception:
                    pass
                # 用底层 API 取原始 JSON 流；高层 images.load() 返回 Image 模型对象，拿不到可读文本
                stream = self.client.api.load_image(fileobj)
                try:
                    raw = list(stream)
                finally:
                    # 显式关闭流，避免 SSH 隧道通道泄漏
                    try:
                        stream.close()
                    except Exception:
                        pass
                self._invalidate_images_cache()
                return self._clean_load_result(raw)
            except Exception as e:
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py load failed, falling back to CLI: {e}")
                try:
                    fileobj.seek(0)
                except Exception:
                    pass

        if self.host_config.get("type") == "ssh":
            # SSH 主机：SFTP 上传到远程临时文件后 docker load
            remote_tmp = f"/tmp/lens_image_load_{int(time.time())}.tar"
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.host_config.get("ssh_host"),
                port=self.host_config.get("ssh_port", 22),
                username=self.host_config.get("ssh_user", "root"),
                password=self.host_config.get("ssh_pass"),
                timeout=15,
            )
            try:
                sftp = ssh.open_sftp()
                try:
                    sftp.putfo(fileobj, remote_tmp)
                finally:
                    sftp.close()
            finally:
                ssh.close()
            try:
                res = self.exec_command(f"docker load -i {remote_tmp}", timeout=1800)
                if not res["success"]:
                    raise Exception(res.get("stderr") or "docker load 执行失败")
                return [(res.get("stdout") or "").strip() or "导入完成"]
            finally:
                self.exec_command(f"rm -f {remote_tmp}", log_error=False)

        # 本地 CLI 兜底
        local_tmp = self._spool_to_temp(fileobj)
        try:
            res = self.exec_command(f"docker load -i {local_tmp}", timeout=1800)
            if not res["success"]:
                raise Exception(res.get("stderr") or "docker load 执行失败")
            return [(res.get("stdout") or "").strip() or "导入完成"]
        finally:
            try:
                os.remove(local_tmp)
            except OSError:
                pass
