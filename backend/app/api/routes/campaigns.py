import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.api.review_gate import device_names, needs_review, park, playlist_names
from app.models import ReviewKind
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
            start_date=r.start_date, end_date=r.end_date,
            start_time=r.start_time, end_time=r.end_time,
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
                start_date=r.start_date, end_date=r.end_date,
                start_time=r.start_time, end_time=r.end_time,
            )
            for r in campaign_service.rules_for(session, campaign_id=campaign.id)
        ],
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _summarize(session: DbSession, campaign) -> CampaignSummary:
    device_ids = campaign_service.device_ids_for(session, campaign_id=campaign.id)
    rules = campaign_service.rules_for(session, campaign_id=campaign.id)
    return CampaignSummary(
        id=campaign.id,
        name=campaign.name,
        device_ids=device_ids,
        device_count=len(device_ids),
        rule_count=len(rules),
        playlist_count=len({r.playlist_id for r in rules}),
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("/campaigns", response_model=list[CampaignSummary])
def list_campaigns(user: CurrentUser, session: DbSession) -> list[CampaignSummary]:
    return [_summarize(session, c) for c in campaign_service.list_campaigns(session, user=user)]


def _as_written(session: DbSession, campaign) -> dict:
    """The campaign as saved now, in the shape a save sends it — what a review keeps as Before."""
    read = _read(session, campaign)
    return {
        "name": read.name,
        "device_ids": [str(i) for i in read.device_ids],
        "rules": [r.model_dump(mode="json") for r in read.rules],
    }


def _campaign_summary(body: CampaignWrite, session: DbSession, user) -> tuple[str, list[str]]:
    screens = device_names(
        session, account_id=user.account_id,
        device_ids=campaign_service.reachable_device_ids(session, user=user, device_ids=body.device_ids),
    )
    # Each rule is a playlist in a time slot, and that is what the Reviews page calls them — a
    # "rule" is our word, not the owner's.
    slots = len(body.rules)
    return (
        f"Campaign “{body.name.strip()}”: {len(screens)} screen{'' if len(screens) == 1 else 's'}, "
        f"{slots} playlist{'' if slots == 1 else 's'}",
        screens,
    )


@router.post("/campaigns", response_model=CampaignSaveResult, status_code=status.HTTP_201_CREATED, responses={202: {"description": "Sent for review"}})
def create_campaign(body: CampaignWrite, user: CurrentUser, session: DbSession):
    if needs_review(user):
        summary, screens = _campaign_summary(body, session, user)
        if not screens:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "none of the selected screens are available")
        return park(
            session, user=user, kind=ReviewKind.CAMPAIGN_CREATE, target_id=None,
            target_name=body.name.strip(), summary="New " + summary[0].lower() + summary[1:],
            screens=screens,
            screen_ids=campaign_service.reachable_device_ids(session, user=user, device_ids=body.device_ids),
            playlists=playlist_names(session, account_id=user.account_id, playlist_ids=[r.playlist_id for r in body.rules]),
            payload=body.model_dump(mode="json"),
        )
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


@router.put("/campaigns/{campaign_id}", response_model=CampaignSaveResult, responses={202: {"description": "Sent for review"}})
def update_campaign(
    campaign_id: uuid.UUID, body: CampaignWrite, user: CurrentUser, session: DbSession
):
    """Full replace, not a patch — a campaign's device list and rules are edited as one set,
    not field by field, so there is no partial-update shape worth having here."""
    try:
        campaign = campaign_service.get(session, user=user, campaign_id=campaign_id)
        if needs_review(user):
            summary, screens = _campaign_summary(body, session, user)
            # Screens leaving the campaign change too.
            leaving = device_names(
                session, account_id=user.account_id,
                device_ids=campaign_service.device_ids_for(session, campaign_id=campaign_id),
            )
            return park(
                session, user=user, kind=ReviewKind.CAMPAIGN_UPDATE, target_id=campaign_id,
                target_name=campaign.name, summary=summary,
                screens=list(dict.fromkeys(screens + leaving)),
                before=_as_written(session, campaign),
                screen_ids=[
                    *campaign_service.reachable_device_ids(session, user=user, device_ids=body.device_ids),
                    *campaign_service.device_ids_for(session, campaign_id=campaign_id),
                ],
                playlists=playlist_names(
                    session, account_id=user.account_id,
                    playlist_ids=[r.playlist_id for r in body.rules]
                    + [r.playlist_id for r in campaign_service.rules_for(session, campaign_id=campaign_id)],
                ),
                payload=body.model_dump(mode="json"),
            )
        campaign, skipped = campaign_service.update(
            session, user=user, campaign=campaign, name=body.name,
            device_ids=body.device_ids, rules=_rule_inputs(body),
        )
    except CampaignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found") from None
    except InvalidCampaign as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    return CampaignSaveResult(campaign=_read(session, campaign), skipped_device_ids=skipped)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, responses={202: {"description": "Sent for review"}})
def delete_campaign(campaign_id: uuid.UUID, user: CurrentUser, session: DbSession):
    try:
        campaign = campaign_service.get(session, user=user, campaign_id=campaign_id)
    except CampaignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found") from None
    if needs_review(user):
        screens = device_names(
            session, account_id=user.account_id,
            device_ids=campaign_service.device_ids_for(session, campaign_id=campaign_id),
        )
        return park(
            session, user=user, kind=ReviewKind.CAMPAIGN_DELETE, target_id=campaign_id,
            target_name=campaign.name, summary=f"Delete campaign “{campaign.name}”",
            screens=screens,
            screen_ids=campaign_service.device_ids_for(session, campaign_id=campaign_id),
            before=_as_written(session, campaign),
            playlists=playlist_names(
                session, account_id=user.account_id,
                playlist_ids=[r.playlist_id for r in campaign_service.rules_for(session, campaign_id=campaign_id)],
            ),
            payload={},
        )
    campaign_service.remove(session, campaign=campaign)
