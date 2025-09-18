import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from models.latency_metric import LatencyMetric
from config.database import get_db

logger = logging.getLogger(__name__)

class LatencyMetricService:
    """Service for managing latency metrics in the database."""

    @staticmethod
    def record_latency(
        db: Session,
        endpoint: str,
        latency_ms: float,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        latency_metadata: Optional[dict] = None
    ) -> bool:
        """
        Record an individual latency measurement in the database.
        
        Args:
            db: Database session
            endpoint: The endpoint name
            latency_ms: Latency in milliseconds
            user_id: Optional user ID
            request_id: Optional request ID for correlation
            latency_metadata: Optional additional metadata
            
        Returns:
            bool: Success status
        """
        try:
            metric = LatencyMetric.create_individual_measurement(
                endpoint=endpoint,
                latency_ms=latency_ms,
                user_id=user_id,
                request_id=request_id,
                latency_metadata=latency_metadata
            )
            
            db.add(metric)
            db.commit()
            
            logger.debug(f"Recorded latency metric: {endpoint} - {latency_ms}ms")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record latency metric: {e}")
            db.rollback()
            return False

    @staticmethod
    def store_aggregated_stats(
        db: Session,
        endpoint: str,
        stats: Dict[str, float],
        user_id: Optional[str] = None,
        latency_metadata: Optional[dict] = None
    ) -> bool:
        """
        Store aggregated latency statistics in the database.
        
        Args:
            db: Database session
            endpoint: The endpoint name
            stats: Statistics dictionary with p95_ms, p99_ms, etc.
            user_id: Optional user ID
            latency_metadata: Optional additional metadata
            
        Returns:
            bool: Success status
        """
        try:
            metric = LatencyMetric.create_aggregated_stats(
                endpoint=endpoint,
                stats=stats,
                user_id=user_id,
                latency_metadata=latency_metadata
            )
            
            db.add(metric)
            db.commit()
            
            logger.debug(f"Stored aggregated stats for {endpoint}: p95={stats.get('p95_ms')}ms, p99={stats.get('p99_ms')}ms")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store aggregated stats: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_recent_stats(
        db: Session,
        endpoint: str,
        user_id: Optional[str] = None,
        hours_back: int = 24
    ) -> Optional[Dict]:
        """
        Get the most recent aggregated statistics for an endpoint.
        
        Args:
            db: Database session
            endpoint: The endpoint name
            user_id: Optional user ID filter
            hours_back: How many hours back to look
            
        Returns:
            Dict with latest stats or None
        """
        try:
            cutoff_time = int((datetime.utcnow() - timedelta(hours=hours_back)).timestamp() * 1000)
            
            query = db.query(LatencyMetric).filter(
                and_(
                    LatencyMetric.endpoint == endpoint,
                    LatencyMetric.measurement_type == "aggregated",
                    LatencyMetric.timestamp >= cutoff_time
                )
            )
            
            if user_id:
                query = query.filter(LatencyMetric.user_id == user_id)
            
            latest_metric = query.order_by(desc(LatencyMetric.timestamp)).first()
            
            if latest_metric:
                return latest_metric.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get recent stats: {e}")
            return None

    @staticmethod
    def get_individual_measurements(
        db: Session,
        endpoint: str,
        user_id: Optional[str] = None,
        hours_back: int = 1,
        limit: int = 1000,
        exclude_cache: bool = False
    ) -> List[Dict]:
        """
        Get individual latency measurements for an endpoint.
        
        Args:
            db: Database session
            endpoint: The endpoint name
            user_id: Optional user ID filter
            hours_back: How many hours back to look
            limit: Maximum number of measurements to return
            exclude_cache: If True, exclude cache hits from results
            
        Returns:
            List of measurement dictionaries
        """
        try:
            cutoff_time = int((datetime.utcnow() - timedelta(hours=hours_back)).timestamp() * 1000)
            
            query = db.query(LatencyMetric).filter(
                and_(
                    LatencyMetric.endpoint == endpoint,
                    LatencyMetric.measurement_type == "individual",
                    LatencyMetric.timestamp >= cutoff_time
                )
            )
            
            if user_id:
                query = query.filter(LatencyMetric.user_id == user_id)
            
            if exclude_cache:
                # Exclude cache hits by checking metadata
                query = query.filter(
                    ~LatencyMetric.latency_metadata.op('->>')('from_cache').cast(db.String) == 'true'
                )
            
            measurements = query.order_by(desc(LatencyMetric.timestamp)).limit(limit).all()
            
            return [measurement.to_dict() for measurement in measurements]
            
        except Exception as e:
            logger.error(f"Failed to get individual measurements: {e}")
            return []

    @staticmethod
    def calculate_stats_from_db(
        db: Session,
        endpoint: str,
        user_id: Optional[str] = None,
        hours_back: int = 1,
        exclude_cache: bool = False
    ) -> Optional[Dict[str, float]]:
        """
        Calculate statistics from individual measurements stored in database.
        
        Args:
            db: Database session
            endpoint: The endpoint name
            user_id: Optional user ID filter
            hours_back: How many hours back to analyze
            exclude_cache: If True, exclude cache hits from calculations
            
        Returns:
            Statistics dictionary or None
        """
        try:
            measurements = LatencyMetricService.get_individual_measurements(
                db, endpoint, user_id, hours_back, limit=10000, exclude_cache=exclude_cache
            )
            
            if not measurements:
                return None
                
            latencies = [m["latency_ms"] for m in measurements if m.get("latency_ms") is not None]
            
            if not latencies:
                return None
                
            # Use the existing compute_latency_stats function
            from evaluation.rag_evaluator import compute_latency_stats
            import statistics
            import numpy as np
            
            stats = compute_latency_stats(latencies)
            
            # Add additional statistics
            stats.update({
                "count": float(len(latencies)),
                "min_ms": float(min(latencies)),
                "max_ms": float(max(latencies)),
                "mean_ms": float(statistics.mean(latencies)),
                "p99_ms": float(np.percentile(latencies, 99))
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate stats from DB: {e}")
            return None

    @staticmethod
    def cleanup_old_measurements(
        db: Session,
        days_to_keep: int = 7
    ) -> int:
        """
        Clean up old individual measurements to prevent database bloat.
        
        Args:
            db: Database session
            days_to_keep: Number of days of measurements to keep
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_time = int((datetime.utcnow() - timedelta(days=days_to_keep)).timestamp() * 1000)
            
            deleted_count = db.query(LatencyMetric).filter(
                and_(
                    LatencyMetric.measurement_type == "individual",
                    LatencyMetric.timestamp < cutoff_time
                )
            ).delete()
            
            db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old latency measurements")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old measurements: {e}")
            db.rollback()
            return 0

    @staticmethod
    def get_endpoint_summary(
        db: Session,
        hours_back: int = 24
    ) -> Dict[str, Dict]:
        """
        Get a summary of latency stats for all endpoints.
        
        Args:
            db: Database session
            hours_back: Hours back to analyze
            
        Returns:
            Dictionary mapping endpoint names to their stats
        """
        try:
            cutoff_time = int((datetime.utcnow() - timedelta(hours=hours_back)).timestamp() * 1000)
            
            # Get unique endpoints that have recent measurements
            endpoints = db.query(LatencyMetric.endpoint).filter(
                and_(
                    LatencyMetric.measurement_type == "individual",
                    LatencyMetric.timestamp >= cutoff_time
                )
            ).distinct().all()
            
            summary = {}
            for (endpoint,) in endpoints:
                stats = LatencyMetricService.calculate_stats_from_db(
                    db, endpoint, hours_back=hours_back
                )
                if stats:
                    summary[endpoint] = stats
                    
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get endpoint summary: {e}")
            return {}

    @staticmethod
    def get_endpoint_summary_no_cache(
        db: Session,
        hours_back: int = 24
    ) -> Dict[str, Dict]:
        """
        Get a summary of latency stats for all endpoints, excluding cache hits.
        
        Args:
            db: Database session
            hours_back: Hours back to analyze
            
        Returns:
            Dictionary mapping endpoint names to their stats (non-cache only)
        """
        try:
            cutoff_time = int((datetime.utcnow() - timedelta(hours=hours_back)).timestamp() * 1000)
            
            # Get unique endpoints that have recent non-cache measurements
            endpoints = db.query(LatencyMetric.endpoint).filter(
                and_(
                    LatencyMetric.measurement_type == "individual",
                    LatencyMetric.timestamp >= cutoff_time,
                    # Exclude cache hits by checking metadata
                    ~LatencyMetric.latency_metadata.op('->>')('from_cache').cast(db.String) == 'true'
                )
            ).distinct().all()
            
            summary = {}
            for (endpoint,) in endpoints:
                # Get stats excluding cache hits
                stats = LatencyMetricService.calculate_stats_from_db(
                    db, endpoint, hours_back=hours_back, exclude_cache=True
                )
                if stats:
                    summary[endpoint] = stats
                    
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get endpoint summary (no cache): {e}")
            return {}
