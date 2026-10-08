from typing import Any
import httpx
from app.core.config import settings
class FHIRClient:
    def __init__(self,base_url:str|None=None): self.base_url=(base_url or settings.HAPI_FHIR_BASE_URL).rstrip("/")
    async def _request(self,method:str,path:str,**kwargs)->dict[str,Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            response=await client.request(method,f"{self.base_url}/{path.lstrip('/')}",**kwargs)
            response.raise_for_status()
            return response.json()
    async def get_metadata(self)->dict[str,Any]: return await self._request("GET","metadata")
    async def get_resource(self,resource_type:str,resource_id:str)->dict[str,Any]: return await self._request("GET",f"{resource_type}/{resource_id}")
    async def search(self,resource_type:str,params:dict[str,Any])->dict[str,Any]: return await self._request("GET",resource_type,params=params)
    async def create_resource(self,resource_type:str,resource:dict[str,Any])->dict[str,Any]: return await self._request("POST",resource_type,json=resource,headers={"Content-Type":"application/fhir+json"})
    async def put_resource(self,resource_type:str,resource_id:str,resource:dict[str,Any])->dict[str,Any]:
        return await self._request("PUT",f"{resource_type}/{resource_id}",json=resource,headers={"Content-Type":"application/fhir+json"})
    async def health_check(self)->bool:
        try: await self.get_metadata(); return True
        except Exception: return False
