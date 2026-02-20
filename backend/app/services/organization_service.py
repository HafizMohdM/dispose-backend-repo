from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.organization import Organization
from app.repositories.organization_repo import OrganizationRepository
from app.api.v1.organizations.org_schemas import OrganizationUpdate


class OrganizationService:

    @staticmethod
    def create_organization(db: Session, data):
        existing = OrganizationRepository.get_by_name(db, data.name)
        if existing:
            raise HTTPException(status_code=409, detail="Organization already exists")

        org = Organization(
            name=data.name,
            description=data.description,
            category_id=data.category_id,
            address=data.address,
            city=data.city,
            state=data.state,
            pincode=data.pincode,
            latitude=data.latitude,
            longitude=data.longitude,
            contact_number=data.contact_number,
            email=data.email,
            status="PENDING"
        )


        return OrganizationRepository.create(db, org)

    @staticmethod
    def get_organization(db: Session, org_id: int):
        org = OrganizationRepository.get_by_id(db, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org

    @staticmethod
    def list_organizations(db: Session, page: int, limit: int):
        skip = (page - 1) * limit
        return OrganizationRepository.get_all(db, skip, limit)

    @staticmethod
    def approve_organization(db: Session, org_id: int):
        org = OrganizationRepository.get_by_id(db, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        org.status = "ACTIVE"
        return OrganizationRepository.update(db, org)

    @staticmethod
    def update_organization(db: Session, org_id: int, data: "OrganizationUpdate"):
        org = OrganizationRepository.get_by_id(db, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        update_data = data.model_dump(exclude_unset=True)
        
        if "category_id" in update_data:
            from app.models.organization import OrganizationCategory
            category = db.query(OrganizationCategory).filter(OrganizationCategory.id == update_data["category_id"]).first()
            
            if not category:
                raise HTTPException(status_code=404, detail="Invalid Category")
        return OrganizationRepository.update_fields(db, org, update_data)