from datetime import datetime
import json

from sqlalchemy import Column, Integer, String, Text, BigInteger
from config.database import Base

class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    created_by = Column(String(100), nullable=True)
    created_ts = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp() * 1000))
    # store JSON as text for SQLite portability
    metrics = Column(Text, nullable=True)
    samples = Column(Text, nullable=True)
    meta = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_by": self.created_by,
            "created_ts": self.created_ts,
            "metrics": json.loads(self.metrics) if self.metrics else {},
            "samples": json.loads(self.samples) if self.samples else [],
            "meta": json.loads(self.meta) if self.meta else {},
        }