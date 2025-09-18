from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, Float, BigInteger, Text, Index
from config.database import Base

class LatencyMetric(Base):
    """
    Database model for storing latency metrics.
    Stores both individual measurements and aggregated statistics.
    """
    __tablename__ = "latency_metrics"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    
    # Individual measurement fields
    latency_ms = Column(Float, nullable=True)  # For individual measurements
    timestamp = Column(BigInteger, nullable=False, index=True)  # Unix timestamp in milliseconds
    request_id = Column(String(100), nullable=True, index=True)  # Optional request ID for correlation
    
    # Aggregated statistics fields (for periodic aggregations)
    measurement_type = Column(String(20), nullable=False, default="individual")  # "individual" or "aggregated"
    sample_count = Column(Integer, nullable=True)  # Number of samples in aggregation
    min_ms = Column(Float, nullable=True)
    max_ms = Column(Float, nullable=True)
    mean_ms = Column(Float, nullable=True)
    median_ms = Column(Float, nullable=True)
    p95_ms = Column(Float, nullable=True)
    p99_ms = Column(Float, nullable=True)
    
    # Additional metadata
    latency_metadata = Column(Text, nullable=True)  # JSON string for additional context
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_endpoint_timestamp', 'endpoint', 'timestamp'),
        Index('idx_user_endpoint_timestamp', 'user_id', 'endpoint', 'timestamp'),
        Index('idx_measurement_type_timestamp', 'measurement_type', 'timestamp'),
    )

    def to_dict(self):
        """Convert model to dictionary."""
        result = {
            "id": self.id,
            "endpoint": self.endpoint,
            "user_id": self.user_id,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "measurement_type": self.measurement_type,
            "sample_count": self.sample_count,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
        }
        
        # Parse metadata if it exists
        if self.latency_metadata:
            try:
                result["latency_metadata"] = json.loads(self.latency_metadata)
            except (json.JSONDecodeError, TypeError):
                result["latency_metadata"] = self.latency_metadata
        else:
            result["latency_metadata"] = {}

        return result

    @classmethod
    def create_individual_measurement(
        cls, 
        endpoint: str, 
        latency_ms: float, 
        user_id: str = None, 
        request_id: str = None,
        latency_metadata: dict = None
    ):
        """Create an individual latency measurement record."""
        return cls(
            endpoint=endpoint,
            user_id=user_id,
            latency_ms=latency_ms,
            timestamp=int(datetime.utcnow().timestamp() * 1000),
            request_id=request_id,
            measurement_type="individual",
            latency_metadata=json.dumps(latency_metadata) if latency_metadata else None
        )

    @classmethod
    def create_aggregated_stats(
        cls,
        endpoint: str,
        stats: dict,
        user_id: str = None,
        latency_metadata: dict = None
    ):
        """Create an aggregated statistics record."""
        return cls(
            endpoint=endpoint,
            user_id=user_id,
            timestamp=int(datetime.utcnow().timestamp() * 1000),
            measurement_type="aggregated",
            sample_count=int(stats.get("count", 0)),
            min_ms=stats.get("min_ms"),
            max_ms=stats.get("max_ms"),
            mean_ms=stats.get("mean_ms"),
            median_ms=stats.get("median_ms"),
            p95_ms=stats.get("p95_ms"),
            p99_ms=stats.get("p99_ms"),
            latency_metadata=json.dumps(latency_metadata) if latency_metadata else None
        )

    def __repr__(self):
        if self.measurement_type == "individual":
            return f"<LatencyMetric(endpoint='{self.endpoint}', latency_ms={self.latency_ms}, timestamp={self.timestamp})>"
        else:
            return f"<LatencyMetric(endpoint='{self.endpoint}', p95_ms={self.p95_ms}, p99_ms={self.p99_ms}, samples={self.sample_count})>"
