# -*- coding: utf-8 -*-
"""识别词生成器 API 路由。"""

from fastapi import APIRouter

from .schemas import GenerateRequest, GenerateResponse
from .service import generate_rules

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse, summary="生成识别词规则")
async def generate(req: GenerateRequest):
    return generate_rules(req)
