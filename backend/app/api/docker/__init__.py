from fastapi import APIRouter

from . import containers, hosts, images, maintenance, settings

# 聚合子路由，注册顺序与拆分前保持一致
router = APIRouter()
router.include_router(containers.router)
router.include_router(hosts.router)
router.include_router(images.router)
router.include_router(maintenance.router)
router.include_router(settings.router)
