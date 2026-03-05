from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models.medercon import Medicine

router = APIRouter()

@router.get('/medicines')
def get_medicines(db: Session = Depends(get_db)):
    """Get all medicines """
    stmt = select(Medicine)
    result = db.execute(stmt)
    medicines = result.scalars().all()
    return medicines