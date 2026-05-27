from abc import ABC, abstractmethod
from ..models.runs import RawInputCandidate, IngestionContext, IngestionResult
class BaseIngestionAdapter(ABC):
    name='base'
    @abstractmethod
    def can_handle(self,candidate:RawInputCandidate)->float:...
    @abstractmethod
    def ingest(self,candidate:RawInputCandidate, context:IngestionContext)->IngestionResult:...
