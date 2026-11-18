from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.jurisdiction_policy.models import Jurisdiction, PolicyRule
from app.jurisdiction_policy.schemas import PolicyEvaluationRequest, PolicyRuleCreate

class JurisdictionPolicyService:
    def __init__(self,session:AsyncSession): self.session=session
    async def evaluate_policy(self, request: PolicyEvaluationRequest):
        source = request.source_jurisdiction.strip().upper()
        destination = request.destination_jurisdiction.strip().upper()

        if source == destination:
            return True, f"Same-jurisdiction access permitted ({source})", None

        # HealthNet currently uses a strict same-jurisdiction access model.
        # Consent does not override this boundary. Cross-jurisdiction policy
        # rules are intentionally not consulted until that model is changed.
        return (
            False,
            (
                "Access denied: same-jurisdiction access only. "
                f"The patient's current repository is in {source}, but this "
                f"provider is registered in {destination}. "
                "The patient must be assigned to a repository in the provider's "
                "jurisdiction, or the provider must be registered in the patient's "
                "current jurisdiction. Patient consent alone cannot override this restriction."
            ),
            None,
        )
    async def get_rules(self): 
        result=await self.session.execute(select(PolicyRule).where(PolicyRule.active.is_(True)).order_by(PolicyRule.name)); return list(result.scalars())
    async def add_rule(self,request:PolicyRuleCreate):
        jurisdiction=await self.session.scalar(select(Jurisdiction).where(Jurisdiction.code==request.jurisdiction_code))
        if jurisdiction is None: raise ValueError("Jurisdiction not found")
        rule=PolicyRule(jurisdiction_id=jurisdiction.id,**request.model_dump(exclude={"jurisdiction_code"}))
        self.session.add(rule); await self.session.flush(); return rule
