from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.schemas.access_evidence import AccessEvidenceResponse
from app.services.access_evidence_service import build_access_evidence_report
from app.services.authz import OrganizationAccessError
from app.services.patient_service import PatientNotFoundError, get_patient_by_id

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/access-evidence/{patient_id}", response_model=AccessEvidenceResponse)
def get_access_evidence_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessEvidenceResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return AccessEvidenceResponse(
        **build_access_evidence_report(db=db, context=context, patient=patient)
    )
