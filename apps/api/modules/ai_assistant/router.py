from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from core.tenancy import get_tenant_db
from modules.ai_assistant.schemas import AIQueryRequest, AIQueryResponse
from modules.ai_assistant.service import AIAssistantService
from modules.auth.dependencies import get_current_user
from modules.auth.models import User

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

@router.post("/query", response_model=AIQueryResponse)
async def query_assistant(
    payload: AIQueryRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Parse natural language intent + slots
    intent_info = await AIAssistantService.classify_intent(payload.message, payload.context)
    intent = intent_info.get("intent", "unknown")
    
    # 2. Execute SQL/services tool matching intent
    tool_data = await AIAssistantService.route_and_execute(db, intent_info, current_user)
    
    # 3. Ground and narrate response using Composer & Hallucination Gate check
    answer = await AIAssistantService.compose_response(intent, tool_data)
    
    return AIQueryResponse(
        intent=intent,
        confidence=intent_info.get("confidence", 1.0),
        data=tool_data if "error" not in tool_data else None,
        answer=answer
    )
