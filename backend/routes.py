import time
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse

from .schemas import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    HealthResponse,
    MessageItem,
    PersonaResponse,
    QuotaExceededResponse,
    QuotaStatusResponse,
    UsageInfo,
)
from conversation import ConversationMemory
from jester_core import ContextBuilder, OutputFilter, PersonaManager
from jester_core.observability import log_request_audit
from jester_core.quota import EntitlementService
from llm_provider import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponseMalformedError,
    LLMTimeoutError,
)


def create_api_router(
    persona_manager: PersonaManager,
    context_builder: ContextBuilder,
    llm_provider: LLMProvider,
    memory: ConversationMemory,
    output_filter: OutputFilter,
    quota_service: EntitlementService,
    api_key: Optional[str] = "",
    require_auth: bool = False,
) -> APIRouter:
    # Fail fast at startup if authentication is required but no key is configured
    if require_auth and not (api_key and api_key.strip()):
        raise ValueError(
            "Security configuration error: require_auth=True requires a non-empty JESTER_API_KEY. "
            "Refusing to start in an insecure or misconfigured state."
        )

    router = APIRouter(prefix="/api")

    def verify_auth(x_jester_api_key: Optional[str] = None):
        if not require_auth:
            return
        if not api_key or not api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "CONFIG_ERROR", "message": "სერვისის ავტორიზაციის გასაღები კონფიგურირებული არაა."},
            )
        if not x_jester_api_key or x_jester_api_key != api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "UNAUTHORIZED", "message": "ავტორიზაცია ვერ მოხერხდა: არასწორი ან არარსებული API გასაღები."},
            )

    def auth_guard(x_jester_api_key: Optional[str] = Header(default=None, alias="X-Jester-API-Key")):
        verify_auth(x_jester_api_key)
        return x_jester_api_key

    @router.post(
        "/chat",
        response_model=ChatResponse,
        responses={402: {"model": QuotaExceededResponse}},
        dependencies=[Depends(auth_guard)],
    )
    async def chat_endpoint(payload: ChatRequest):
        user_message = payload.message.strip()
        if not user_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "BAD_REQUEST", "message": "Message cannot be empty."},
            )

        user_id = payload.user_id.strip()
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "BAD_REQUEST", "message": "user_id cannot be empty."},
            )

        conv_id = payload.conversation_id or str(uuid.uuid4())
        req_id = str(uuid.uuid4())[:8]

        # 1. ATOMIC PRE-INFERENCE QUOTA RESERVATION (Race-free reservation)
        decision = await quota_service.reserve_quota(user_id)
        if not decision.allowed:
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=0.0,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="blocked_paywall",
                remaining_free_questions=0,
                http_status=402,
                error="QUOTA_EXCEEDED",
            )
            paywall_response = QuotaExceededResponse(
                error="QUOTA_EXCEEDED",
                message=decision.rejection_message
                or "თქვენ ამოწურეთ 3 უფასო შეკითხვა. მასხარასთან საუბრის გასაგრძელებლად საჭიროა წვდომის განახლება.",
                user_id=user_id,
                remaining_free_questions=0,
                upgrade_url="/billing/plans",
            )
            return JSONResponse(status_code=402, content=paywall_response.model_dump())

        # 2. Retrieve conversation history
        history = memory.get_history(conv_id)

        # 3. Assemble prompt context (System + Sovereign UserContext + Examples + History + Query)
        llm_messages = context_builder.build_llm_messages(
            current_message=user_message,
            history=history,
            include_examples=True,
            user_context=payload.user_context,
        )

        llm_request = LLMRequest(messages=llm_messages)

        # 4. Invoke LLM Provider with Failure Observability and Automatic Quota Release
        start_inference_time = time.perf_counter()
        try:
            llm_response = await llm_provider.chat(llm_request)
        except LLMConnectionError as e:
            await quota_service.release_quota(user_id)
            elapsed_ms = round((time.perf_counter() - start_inference_time) * 1000, 2)
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=elapsed_ms,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="reservation_released",
                remaining_free_questions=decision.remaining_free_questions + 1,
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                error="PROVIDER_UNAVAILABLE",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "PROVIDER_UNAVAILABLE",
                    "message": "სააზროვნო ძრავთან კავშირი შეწყდა.",
                    "provider": llm_provider.provider_name,
                    "retryable": True,
                },
            )
        except LLMTimeoutError as e:
            await quota_service.release_quota(user_id)
            elapsed_ms = round((time.perf_counter() - start_inference_time) * 1000, 2)
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=elapsed_ms,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="reservation_released",
                remaining_free_questions=decision.remaining_free_questions + 1,
                http_status=status.HTTP_504_GATEWAY_TIMEOUT,
                error="PROVIDER_TIMEOUT",
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "error": "PROVIDER_TIMEOUT",
                    "message": "პასუხის მოლოდინის დრო ამოიწურა.",
                    "provider": llm_provider.provider_name,
                },
            )
        except LLMAuthenticationError as e:
            await quota_service.release_quota(user_id)
            elapsed_ms = round((time.perf_counter() - start_inference_time) * 1000, 2)
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=elapsed_ms,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="reservation_released",
                remaining_free_questions=decision.remaining_free_questions + 1,
                http_status=status.HTTP_502_BAD_GATEWAY,
                error="PROVIDER_AUTH_ERROR",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "PROVIDER_AUTH_ERROR",
                    "message": "სააზროვნო ძრავის ავტორიზაციის შეცდომა.",
                    "provider": llm_provider.provider_name,
                },
            )
        except LLMRateLimitError as e:
            await quota_service.release_quota(user_id)
            elapsed_ms = round((time.perf_counter() - start_inference_time) * 1000, 2)
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=elapsed_ms,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="reservation_released",
                remaining_free_questions=decision.remaining_free_questions + 1,
                http_status=status.HTTP_429_TOO_MANY_REQUESTS,
                error="PROVIDER_RATE_LIMIT",
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "PROVIDER_RATE_LIMIT",
                    "message": "სააზროვნო ძრავის ლიმიტი ამოიწურა.",
                    "provider": llm_provider.provider_name,
                },
            )
        except LLMResponseMalformedError as e:
            await quota_service.release_quota(user_id)
            elapsed_ms = round((time.perf_counter() - start_inference_time) * 1000, 2)
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=elapsed_ms,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="reservation_released",
                remaining_free_questions=decision.remaining_free_questions + 1,
                http_status=status.HTTP_502_BAD_GATEWAY,
                error="PROVIDER_MALFORMED_RESPONSE",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "PROVIDER_MALFORMED_RESPONSE",
                    "message": "დაზიანებული პასუხი სააზროვნო ძრავიდან.",
                    "provider": llm_provider.provider_name,
                },
            )
        except LLMProviderError as e:
            await quota_service.release_quota(user_id)
            elapsed_ms = round((time.perf_counter() - start_inference_time) * 1000, 2)
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=elapsed_ms,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="reservation_released",
                remaining_free_questions=decision.remaining_free_questions + 1,
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error="PROVIDER_ERROR",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "PROVIDER_ERROR",
                    "message": "სააზროვნო შეცდომა მოხდა.",
                    "provider": llm_provider.provider_name,
                },
            )
        except Exception as e:
            await quota_service.release_quota(user_id)
            elapsed_ms = round((time.perf_counter() - start_inference_time) * 1000, 2)
            log_request_audit(
                request_id=req_id,
                user_id=user_id,
                conversation_id=conv_id,
                provider=llm_provider.provider_name,
                model=llm_provider.model_name,
                latency_ms=elapsed_ms,
                prompt_tokens=0,
                completion_tokens=0,
                quota_status="reservation_released",
                remaining_free_questions=decision.remaining_free_questions + 1,
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error="INTERNAL_ERROR",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "INTERNAL_ERROR",
                    "message": "შიდა სერვერული შეცდომა მოხდა დამუშავებისას.",
                },
            )

        # 5. Sanitize stage directions (*laughs*, *(იცინის)*)
        sanitized_response = output_filter.sanitize(llm_response.content)

        # 6. Finalize atomic consumption
        await quota_service.commit_quota(user_id)
        post_decision = await quota_service.check_access(user_id)

        # 7. Commit interaction turn to Conversation Memory
        memory.add_message(conv_id, "user", user_message)
        memory.add_message(conv_id, "assistant", sanitized_response)

        # 8. Audit Logging for success turn
        prompt_tokens = llm_response.usage.prompt_tokens if llm_response.usage else None
        completion_tokens = llm_response.usage.completion_tokens if llm_response.usage else None
        log_request_audit(
            request_id=req_id,
            user_id=user_id,
            conversation_id=conv_id,
            provider=llm_response.provider,
            model=llm_response.model,
            latency_ms=llm_response.latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            quota_status="active" if post_decision.allowed else "exhausted",
            remaining_free_questions=post_decision.remaining_free_questions,
            http_status=200,
        )

        # 9. Return clean structured response
        return ChatResponse(
            conversation_id=conv_id,
            response=sanitized_response,
            model=llm_response.model,
            provider=llm_response.provider,
            usage=UsageInfo(
                remaining_free_questions=post_decision.remaining_free_questions,
                is_paid_user=post_decision.is_subscribed,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=llm_response.latency_ms,
            ),
        )

    @router.get(
        "/quota/{user_id}",
        response_model=QuotaStatusResponse,
        dependencies=[Depends(auth_guard)],
    )
    async def get_user_quota(user_id: str):
        decision = await quota_service.check_access(user_id)
        return QuotaStatusResponse(
            user_id=user_id,
            remaining_free_questions=decision.remaining_free_questions,
            is_paid_user=decision.is_subscribed,
            allowed=decision.allowed,
        )

    @router.get(
        "/conversations/{conversation_id}",
        response_model=ConversationHistoryResponse,
        dependencies=[Depends(auth_guard)],
    )
    async def get_conversation(conversation_id: str):
        history = memory.get_history(conversation_id)
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=[MessageItem(role=m["role"], content=m["content"]) for m in history],
        )

    @router.delete(
        "/conversations/{conversation_id}",
        dependencies=[Depends(auth_guard)],
    )
    async def clear_conversation(conversation_id: str):
        memory.clear(conversation_id)
        return {"status": "cleared", "conversation_id": conversation_id}

    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        meta = await llm_provider.health_check()
        return HealthResponse(
            status="healthy" if meta.healthy else "degraded",
            model=meta.current_model,
            provider=meta.name,
            provider_details=meta.details,
        )

    @router.get("/persona", response_model=PersonaResponse)
    async def get_persona_details():
        return PersonaResponse(
            system_prompt=persona_manager.get_compiled_system_prompt(),
            rules_summary=persona_manager.get_rules_summary(),
        )

    @router.post(
        "/persona/reload",
        dependencies=[Depends(auth_guard)],
    )
    async def reload_persona():
        persona_manager.reload()
        return {
            "status": "reloaded",
            "message": "Persona configuration files reloaded successfully from disk.",
        }

    return router
