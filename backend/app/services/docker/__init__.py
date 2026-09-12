from ._compat import *  # noqa: F401,F403  应用 paramiko 补丁（副作用导入）
from .base import DockerServiceBase
from .containers import ContainerOpsMixin
from .images import ImageOpsMixin
from .auto_update import AutoUpdateMixin


class DockerService(ContainerOpsMixin, ImageOpsMixin, AutoUpdateMixin):
    """聚合门面：对外接口与拆分前完全一致。"""

    # Compose 项目列表缓存 { host_id: (projects, timestamp) }，由 api/docker_compose.py 读写
    _projects_cache = {}
