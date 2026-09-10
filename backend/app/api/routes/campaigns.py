import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.campaigns import (
    CampaignRead,
    CampaignRuleRead,
    CampaignSaveResult,
    CampaignSummary,
    CampaignWrite,
)
from app.services import campaigns as campaign_service
from app.services.campaigns import CampaignNotFound, CampaignRuleInput, InvalidCampaign

router = APIRouter(tags=["campaigns"])


def _rule_inputs(body: CampaignWrite) -> list[CampaignRuleInput]:
    return [
        CampaignRuleInput(
            playlist_id=r.playlist_id, name=r.name, days_of_week=r.days_of_week,
            starts_at=r.starts_at, ends_at=r.ends_at, priority=r.priority,
        )
        for r in body.rules
    ]


def _read(session: DbSession, campaign) -> CampaignRead:
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
        device_ids=campaign_service.device_ids_for(session, campaign_id=campaign.id),
        rules=[
            CampaignRuleRead(
                playlist_id=r.playlist_id, name=r.name, days_of_week=r.days_of_week,
                starts_at=r.starts_at, ends_at=r.ends_at, priority=r.priority,
            )
            for r in campaign_service.rules_for(session, campaign_id=campaign.id)
        ],
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _summarize(session: DbSession, campaign) -> CampaignSummary:
    return CampaignSummary(
        id=campaign.id,
        name=campaign.name,
        device_count=len(campaign_service.device_ids_for(session, campaign_id=campaign.id)),
        rule_count=len(campaign_service.rules_for(session, campaign_id=campaign.id)),
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("/campaigns", response_model=list[CampaignSummary])
def list_campaigns(user: CurrentUser, session: DbSession) -> list[CampaignSummary]:
    return [_summarize(session, c) for c in campaign_service.list_campaigns(session, user=user)]


@router.post("/campaigns", response_model=CampaignSaveResult, status_code=status.HTTP_201_CREATED)
def create_campaign(body: CampaignWrite, user: CurrentUser, session: DbSession) -> CampaignSaveResult:
    try:
        campaign, skipped = campaign_service.create(
            session, user=user, name=body.name,
            device_ids=body.device_ids, rules=_rule_inputs(body),
        )
    except InvalidCampaign as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return CampaignSaveResult(campaign=_read(session, campaign), skipped_device_ids=skipped)


@router.get("/campaigns/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: uuid.UUID, user: CurrentUser, session: DbSession) -> CampaignRead:
    try:
        campaign = campaign_service.get(session, user=user, campaign_id=campaign_id)
    except CampaignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found") from None
    return _read(session, campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignSaveResult)
def update_campaign(
    campaign_id: uuid.UUID, body: CampaignWrite, user: CurrentUser, session: DbSession
) -> CampaignSaveResult:
    """Full replace, not a patch — a campaign's device list and rules are edited as one set,
    not field by field, so there is no partial-update shape worth having here."""
    try:
        campaign = campaign_service.get(session, user=user, campaign_id=campaign_id)
        campaign, skipped = campaign_service.update(
            session, user=user, campaign=campaign, name=body.name,
            device_ids=body.device_ids, rules=_rule_inputs(body),
        )
    except CampaignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found") from None
    except InvalidCampaign as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return CampaignSaveResult(campaign=_read(session, campaign), skipped_device_ids=skipped)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: uuid.UUID, user: CurrentUser, session: DbSession) -> None:
    try:
        campaign = campaign_service.get(session, user=user, campaign_id=campaign_id)
    except CampaignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found") from None
    campaign_service.remove(session, campaign=campaign)
