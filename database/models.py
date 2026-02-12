# Database Models for SecureAI Guardian
# SQLAlchemy models for PostgreSQL database

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()


class User(Base):
    """User model for authentication and user management"""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='user', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships (no cascade delete: analyses must never be auto-deleted when user is removed)
    analyses = relationship("Analysis", back_populates="user", cascade="save-update")
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }


class Analysis(Base):
    """Analysis result model for storing video analysis data"""
    __tablename__ = 'analyses'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True, index=True)
    filename = Column(String(500), nullable=False)
    source_url = Column(String(1000), nullable=True)
    file_path = Column(String(1000), nullable=True)
    s3_key = Column(String(1000), nullable=True)
    
    # Detection results
    is_fake = Column(Boolean, nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    fake_probability = Column(Float, nullable=False)
    authenticity_score = Column(Float, nullable=True)
    verdict = Column(String(50), nullable=False, index=True)  # FAKE, REAL, SUSPICIOUS
    
    # Forensic metrics (stored as JSON)
    forensic_metrics = Column(JSON, nullable=True)
    spatial_entropy_heatmap = Column(JSON, nullable=True)
    
    # Blockchain
    blockchain_tx = Column(String(255), nullable=True, index=True)
    blockchain_network = Column(String(50), nullable=True)
    blockchain_timestamp = Column(DateTime, nullable=True)
    
    # Metadata
    video_hash = Column(String(64), nullable=True, index=True)
    file_size = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)
    model_type = Column(String(50), nullable=True)
    processing_time = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_analyses_user_created', 'user_id', 'created_at'),
        Index('idx_analyses_verdict_created', 'verdict', 'created_at'),
        Index('idx_analyses_fake_prob', 'fake_probability'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'source_url': self.source_url,
            'is_fake': self.is_fake,
            'confidence': self.confidence,
            'fake_probability': self.fake_probability,
            'authenticity_score': self.authenticity_score,
            'verdict': self.verdict,
            'forensic_metrics': self.forensic_metrics,
            'spatial_entropy_heatmap': self.spatial_entropy_heatmap,
            'blockchain_tx': self.blockchain_tx,
            'blockchain_network': self.blockchain_network,
            'blockchain_timestamp': self.blockchain_timestamp.isoformat() if self.blockchain_timestamp else None,
            'video_hash': self.video_hash,
            'file_size': self.file_size,
            'duration': self.duration,
            'model_type': self.model_type,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProcessingStats(Base):
    """Aggregated processing statistics"""
    __tablename__ = 'processing_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False, unique=True, index=True)
    
    total_analyses = Column(Integer, default=0, nullable=False)
    fake_detected = Column(Integer, default=0, nullable=False)
    authentic_detected = Column(Integer, default=0, nullable=False)
    blockchain_proofs = Column(Integer, default=0, nullable=False)
    
    avg_processing_time = Column(Float, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    authenticity_percentage = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_analyses': self.total_analyses,
            'fake_detected': self.fake_detected,
            'authentic_detected': self.authentic_detected,
            'blockchain_proofs': self.blockchain_proofs,
            'avg_processing_time': self.avg_processing_time,
            'avg_confidence': self.avg_confidence,
            'authenticity_percentage': self.authenticity_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DeviceIdentity(Base):
    """
    Device-bound identity for seamless, passwordless authentication.
    
    This model enables:
    - Zero-friction login (no usernames, passwords, or email signups)
    - Device-bound security (identity tied to browser fingerprint)
    - Invisible blockchain anchoring (system-managed Solana wallets)
    - State persistence (scan history survives browser data clears)
    """
    __tablename__ = 'device_identities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Device fingerprint (deterministic hash from browser/device characteristics)
    # Same device + same browser = same fingerprint
    device_fingerprint = Column(String(64), unique=True, nullable=False, index=True)
    
    # User-facing identity
    node_id = Column(String(20), unique=True, nullable=False, index=True)  # e.g., "SAI_ABC123XYZ"
    alias = Column(String(100), nullable=False)  # User's display name / neural alias
    tier = Column(String(50), default='SENTINEL', nullable=False)  # Subscription tier
    
    # System-managed Solana wallet (invisible to user)
    # User never sees or interacts with this - all blockchain ops are automatic
    solana_pubkey = Column(String(64), nullable=True)  # Base58 public key
    solana_keypair_encrypted = Column(Text, nullable=True)  # Encrypted private key (server-side only)
    
    # Activity tracking
    scan_count = Column(Integer, default=0, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Device metadata (for fingerprint verification)
    browser_name = Column(String(50), nullable=True)
    os_name = Column(String(50), nullable=True)
    screen_resolution = Column(String(20), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Blockchain anchoring
    blockchain_anchored = Column(Boolean, default=False, nullable=False)
    anchor_tx = Column(String(100), nullable=True)  # Solana transaction signature
    anchor_timestamp = Column(DateTime, nullable=True)
    
    # State persistence (JSON blobs for scan history, audit logs, etc.)
    scan_history = Column(JSON, nullable=True)
    audit_history = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_device_identity_fingerprint', 'device_fingerprint'),
        Index('idx_device_identity_node_id', 'node_id'),
        Index('idx_device_identity_last_seen', 'last_seen'),
    )
    
    def to_dict(self):
        """Convert to API response format"""
        return {
            'nodeId': self.node_id,
            'alias': self.alias,
            'tier': self.tier,
            'isNewDevice': False,  # Will be set by caller for new devices
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastSeen': self.last_seen.isoformat() if self.last_seen else None,
            'scanCount': self.scan_count,
            'blockchainAnchored': self.blockchain_anchored,
        }
    
    def to_full_dict(self):
        """Convert to full format including history (for state sync)"""
        result = self.to_dict()
        result['scanHistory'] = self.scan_history or []
        result['auditHistory'] = self.audit_history or []
        return result

