import json
import asyncio
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.session import get_db
from app.models.terminal import TerminalHost, QuickCommand
from app.schemas.terminal import TerminalHostCreate, TerminalHostRead, QuickCommandCreate, QuickCommandRead
from app.services.terminal_service import TerminalService
from app.utils.logger import logger

router = APIRouter()

# --- 主机管理 ---

@router.get("/hosts", response_model=List[TerminalHostRead])
async def get_hosts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TerminalHost))
    return result.scalars().all()

@router.post("/hosts", response_model=TerminalHostRead)
async def create_host(host: TerminalHostCreate, db: AsyncSession = Depends(get_db)):
    new_host = TerminalHost(**host.dict())
    db.add(new_host)
    await db.commit()
    await db.refresh(new_host)
    return new_host

@router.put("/hosts/{host_id}", response_model=TerminalHostRead)
async def update_host(host_id: int, host: TerminalHostCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TerminalHost).where(TerminalHost.id == host_id))
    db_host = result.scalar_one_or_none()
    if not db_host:
        raise HTTPException(status_code=404, detail="Host not found")
    for key, value in host.dict().items():
        setattr(db_host, key, value)
    await db.commit()
    await db.refresh(db_host)
    return db_host

@router.delete("/hosts/{host_id}")
async def delete_host(host_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(TerminalHost).where(TerminalHost.id == host_id))
    await db.commit()
    return {"status": "success"}

# --- 快速命令 ---

@router.get("/commands", response_model=List[QuickCommandRead])
async def get_commands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QuickCommand).order_by(QuickCommand.sort_order.asc(), QuickCommand.id.desc()))
    return result.scalars().all()

@router.post("/commands/reorder")
async def reorder_commands(ids: List[int] = Body(...), db: AsyncSession = Depends(get_db)):
    for index, cmd_id in enumerate(ids):
        await db.execute(
            delete(QuickCommand).where(QuickCommand.id == -1) # dummy to use db
        )
        # Use a more direct update
        from sqlalchemy import update
        await db.execute(
            update(QuickCommand).where(QuickCommand.id == cmd_id).values(sort_order=index)
        )
    await db.commit()
    return {"status": "success"}

@router.post("/commands", response_model=QuickCommandRead)
async def create_command(cmd: QuickCommandCreate, db: AsyncSession = Depends(get_db)):
    new_cmd = QuickCommand(**cmd.dict())
    db.add(new_cmd)
    await db.commit()
    await db.refresh(new_cmd)
    return new_cmd

@router.put("/commands/{cmd_id}", response_model=QuickCommandRead)
async def update_command(cmd_id: int, cmd: QuickCommandCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QuickCommand).where(QuickCommand.id == cmd_id))
    db_cmd = result.scalar_one_or_none()
    if not db_cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    for key, value in cmd.dict().items():
        setattr(db_cmd, key, value)
    await db.commit()
    await db.refresh(db_cmd)
    return db_cmd

@router.delete("/commands/{cmd_id}")
async def delete_command(cmd_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(QuickCommand).where(QuickCommand.id == cmd_id))
    await db.commit()
    return {"status": "success"}

# --- WebSocket 终端连接 ---

from app.core.config_manager import get_config
from app.utils.auth import decode_access_token
from app.services.config_service import ConfigService
from app.services.session_service import get_session_by_id, update_session_activity
from app.utils.time import get_local_time

@router.websocket("/ws/{host_id}")
async def terminal_websocket(websocket: WebSocket, host_id: str, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    # 验证 Token - 使用与 HTTP API 相同的验证逻辑
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.user import User
    
    valid = False
    if token:
        # 检查静态 Token
        static_token = await ConfigService.get("api_token")
        if static_token and token == static_token:
            valid = True
        else:
            # 检查 JWT Token - 完整验证
            payload = decode_access_token(token)
            if payload and payload.get("type") != "2fa_pending":
                session_id = payload.get("sid")
                token_ps = payload.get("ps")
                
                if session_id and token_ps:
                    async with AsyncSessionLocal() as db:
                        session = await get_session_by_id(db, session_id)
                        if session:
                            # 检查会话是否已过期
                            now = get_local_time()
                            if now.tzinfo is not None:
                                now = now.replace(tzinfo=None)
                            
                            if session.expires_at >= now:
                                # 验证密码指纹
                                result = await db.execute(select(User).where(User.id == session.user_id))
                                user = result.scalars().first()
                                if user:
                                    current_ps = user.hashed_password[:16]
                                    if token_ps == current_ps:
                                        # 更新会话最后活动时间
                                        await update_session_activity(db, session_id)
                                        valid = True
    
    if not valid:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await websocket.accept()
    
    term_service = TerminalService()
    
    try:
        # 转换判断
        is_digit = str(host_id).isdigit()
        
        if is_digit and int(host_id) == 0:
            # 连接本机
            term_service.open_terminal()
        elif is_digit:
            # 连接远程终端主机
            result = await db.execute(select(TerminalHost).where(TerminalHost.id == int(host_id)))
            host_info = result.scalar_one_or_none()
            if not host_info:
                await websocket.send_text("\r\n\x1b[31m[Error] Host not found in Terminal registry.\x1b[0m\r\n")
                await websocket.close()
                return
            
            host_dict = {
                "host": host_info.host,
                "port": host_info.port,
                "username": host_info.username,
                "auth_type": host_info.auth_type,
                "password": host_info.password,
                "private_key": host_info.private_key
            }
            await term_service.connect_ssh(host_dict)
        else:
            # 连接 Docker 主机
            config = get_config()
            docker_hosts = config.get("docker_hosts", [])
            docker_host = next((h for h in docker_hosts if h.get("id") == host_id), None)
            
            if not docker_host:
                if host_id == "local":
                    term_service.open_terminal()
                else:
                    await websocket.send_text(f"\r\n\x1b[31m[Error] Docker host {host_id} not found.\x1b[0m\r\n")
                    await websocket.close()
                    return
            elif docker_host.get("type") == "local":
                term_service.open_terminal()
            elif docker_host.get("type") == "ssh":
                host_dict = {
                    "host": docker_host.get("ssh_host"),
                    "port": docker_host.get("ssh_port", 22),
                    "username": docker_host.get("ssh_user", "root"),
                    "auth_type": "password" if docker_host.get("ssh_pass") else "none",
                    "password": docker_host.get("ssh_pass"),
                    "private_key": None
                }
                if "ssh_key" in docker_host:
                    host_dict["auth_type"] = "key"
                    host_dict["private_key"] = docker_host["ssh_key"]
                await term_service.connect_ssh(host_dict)
            else:
                await websocket.send_text("\r\n\x1b[31m[Error] This Docker host type does not support SSH terminal.\x1b[0m\r\n")
                await websocket.close()
                return

        # 异步读取输出
        async def read_from_pty():
            try:
                while True:
                    output = term_service.read_output()
                    if output:
                        await websocket.send_text(output.decode('utf-8', errors='ignore'))
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"[Terminal] Read error: {e}")

        read_task = asyncio.create_task(read_from_pty())
        
        while True:
            message = await websocket.receive_text()
            if message.startswith('{') and 'type' in message:
                try:
                    msg = json.loads(message)
                    if msg.get("type") == "resize":
                        term_service.resize(msg.get("rows", 24), msg.get("cols", 80))
                        continue
                except: pass
            
            term_service.write_input(message)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[Terminal] WS error: {e}")
    finally:
        if 'read_task' in locals():
            read_task.cancel()
        term_service.close()