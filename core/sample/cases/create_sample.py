from sqlalchemy.ext.asyncio import AsyncSession

from core.sample.dto.create_sample import CreateSampleDTO
from core.sample.models.sample import SampleModel


class CreateSampleCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, dto: CreateSampleDTO) -> SampleModel:
        sample = SampleModel(name=dto.name, description=dto.description)
        self.session.add(sample)
        await self.session.commit()
        await self.session.refresh(sample)
        return sample
