from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from provider_mock.simulation.engine import ProviderSimulationEngine
from shared.constants import provider_slug_for_method
from shared.contracts import PaymentMethod, ProviderRequest, ProviderResponse

router = APIRouter(prefix="/providers", tags=["providers"])
PROVIDER_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    503: {"description": "Provider unavailable"},
    504: {"description": "Provider timeout"},
}


def get_engine(request: Request) -> ProviderSimulationEngine:
    return request.app.state.engine


@router.post("/pix/confirm", responses=PROVIDER_ERROR_RESPONSES)
async def confirm_pix(
    payload: ProviderRequest,
    engine: Annotated[ProviderSimulationEngine, Depends(get_engine)],
) -> ProviderResponse:
    return await _confirm(PaymentMethod.PIX, payload, engine)


@router.post("/boleto/confirm", responses=PROVIDER_ERROR_RESPONSES)
async def confirm_boleto(
    payload: ProviderRequest,
    engine: Annotated[ProviderSimulationEngine, Depends(get_engine)],
) -> ProviderResponse:
    return await _confirm(PaymentMethod.BOLETO, payload, engine)


@router.post("/ted/confirm", responses=PROVIDER_ERROR_RESPONSES)
async def confirm_ted(
    payload: ProviderRequest,
    engine: Annotated[ProviderSimulationEngine, Depends(get_engine)],
) -> ProviderResponse:
    return await _confirm(PaymentMethod.TED, payload, engine)


@router.post("/card/confirm", responses=PROVIDER_ERROR_RESPONSES)
async def confirm_card(
    payload: ProviderRequest,
    engine: Annotated[ProviderSimulationEngine, Depends(get_engine)],
) -> ProviderResponse:
    return await _confirm(PaymentMethod.CARD, payload, engine)


async def _confirm(
    method: PaymentMethod, payload: ProviderRequest, engine: ProviderSimulationEngine
) -> ProviderResponse:
    provider_slug = provider_slug_for_method(method)
    return await _simulate_provider(provider_slug, payload, engine)


async def _simulate_provider(
    provider_slug: str, payload: ProviderRequest, engine: ProviderSimulationEngine
) -> ProviderResponse:
    try:
        return await engine.simulate(provider_slug, payload)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Provider timeout") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Provider unavailable") from exc
