from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..services import wallet_service

router = APIRouter()


@router.get("/getsms.Php")
def receive_sms_webhook(
    request: Request,
    to: str | None = Query(default=None),
    body: str = Query(...),
    from_number: str = Query(..., alias="from"),
    db: Session = Depends(get_db),
):
    raw_query = request.url.query or ""
    if ";http" in raw_query:
        # Provider occasionally appends a second callback URL after ';'.
        # Keep only the first URL query so parameters are parsed correctly.
        raw_query = raw_query.split(";http", 1)[0]
        qs = parse_qs(raw_query, keep_blank_values=True)
        to = (qs.get("to") or [to])[0]
        body = (qs.get("body") or [body])[0]
        from_number = (qs.get("from") or [from_number])[0]

    sms = wallet_service.ingest_incoming_sms(
        db=db,
        sender=from_number,
        receiver=to,
        body=body,
    )
    return {"ok": True, "stored": bool(sms), "id": sms.id if sms else None}
