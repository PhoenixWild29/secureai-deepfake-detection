#!/usr/bin/env python3
"""
Blockchain Service for SecureAI DeepFake Detection
Service for real-time Solana blockchain verification status checks and network integration.
"""

import asyncio
import logging
import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from uuid import UUID
from dataclasses import dataclass
import aiohttp
import base58

from app.schemas.detection import BlockchainVerificationStatus

logger = logging.getLogger(__name__)


@dataclass
class SolanaConfig:
    """Configuration for Solana network connections"""
    network_url: str = "https://api.mainnet-beta.solana.com"
    rpc_timeout: int = 5  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    cache_ttl_seconds: int = 300  # 5 minutes


class BlockchainService:
    """
    Service for real-time Solana blockchain verification status checks.
    Handles network queries, caching, and verification validation with minimal latency.
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.solana_config = SolanaConfig()
        self._session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.solana_config.rpc_timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()
    
    async def get_blockchain_verification_status(self, analysis_id: UUID, blockchain_hash: Optional[str] = None) -> Optional[BlockchainVerificationStatus]:
        """
        Get real-time blockchain verification status for an analysis.
        
        Args:
            analysis_id: Analysis ID
            blockchain_hash: Optional blockchain hash to verify
            
        Returns:
            BlockchainVerificationStatus or None if not available
        """
        cache_key = f"blockchain_verification:{analysis_id}"
        
        # Try cache first for fast response
        if self.redis_client:
            try:
                cached_data = await self._get_from_cache(cache_key)
                if cached_data:
                    logger.debug(f"Hit blockchain cache for analysis {analysis_id}")
                    cached_status = json.loads(cached_data)
                    
                    # Check if cache is still fresh enough (< 1 minute old)
                    if self._is_cache_fresh(cached_status):
                        return BlockchainVerificationStatus(**cached_status)
            except Exception as e:
                logger.warning(f"Cache read failed for blockchain verification {analysis_id}: {e}")
        
        # Perform real-time verification
        try:
            verification_data = await self._verify_on_blockchain(blockchain_hash)
            
            # Cache the result for next time
            if self.redis_client and verification_data:
                await self._set_cache(cache_key, json.dumps(verification_data.model_dump()))
            
            return verification_data
            
        except Exception as e:
            logger.error(f"Failed to verify blockchain status for analysis {analysis_id}: {e}")
            return None
    
    async def get_solana_network_status(self) -> Dict[str, Any]:
        """
        Get real-time Solana network status for verification context.
        
        Returns:
            Dictionary with network status information
        """
        cache_key = "solana_network_status"
        
        # Try cache first (short TTL for network status)
        if self.redis_client:
            try:
                cached_data = await self._get_from_cache(cache_key)
                if cached_data:
                    network_status = json.loads(cached_data)
                    
                    # Check if cache is fresh (< 30 seconds old)
                    if self._is_cache_fresh(network_status, max_age_seconds=30):
                        return network_status
            except Exception as e:
                logger.warning(f"Cache read failed for Solana network status: {e}")
        
        # Get fresh network status
        try:
            network_status = await self._query_solana_network_status()
            
            # Cache briefly
            if self.redis_client and network_status:
                await self._set_cache(cache_key, json.dumps(network_status), ttl_seconds=60)
            
            return network_status
            
        except Exception as e:
            logger.error(f"Failed to get Solana network status: {e}")
            return {
                'status': 'unknown',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
    
    async def verify_transaction_hash(self, transaction_hash: str) -> Dict[str, Any]:
        """
        Verify blockchain transaction hash against Solana network.
        
        Args:
            transaction_hash: Transaction hash to verify
            
        Returns:
            Dictionary with verification results
        """
        if not transaction_hash:
            return {
                'status': 'invalid',
                'verified': False,
                'error': 'No transaction hash provided'
            }
        
        try:
            # Validate hash format (basic check)
            if not self._is_valid_solana_hash(transaction_hash):
                return {
                    'status': 'invalid',
                    'verified': False,
                    'error': 'Invalid transaction hash format'
                }
            
            # Query Solana network for transaction
            async with self._get_session():
                verification_result = await self._query_transaction_details(transaction_hash)
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Failed to verify transaction hash {transaction_hash}: {e}")
            return {
                'status': 'error',
                'verified': False,
                'error': str(e)
            }
    
    async def submit_to_blockchain(self, analysis_data: Dict[str, Any]) -> Optional[str]:
        """
        Submit analysis data to Solana blockchain for permanent record.
        
        Args:
            analysis_data: Analysis data to submit
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            # Generate blockchain payload
            payload = self._generate_blockchain_payload(analysis_data)
            
            # Submit to blockchain (simplified simulation)
            # In real implementation, this would interact with Solana contract
            transaction_hash = await self._submit_transaction(payload)
            
            if transaction_hash:
                logger.info(f"Successfully submitted analysis {analysis_data.get('analysis_id')} to blockchain: {transaction_hash}")
                
                # Cache the submission
                if self.redis_client:
                    cache_key = f"blockchain_submission:{analysis_data.get('analysis_id')}"
                    await self._set_cache(cache_key, json.dumps({
                        'transaction_hash': transaction_hash,
                        'submitted_at': datetime.now(timezone.utc).isoformat(),
                        'analysis_id': str(analysis_data.get('analysis_id'))
                    }))
            
            return transaction_hash
            
        except Exception as e:
            logger.error(f"Failed to submit analysis to blockchain: {e}")
            return None
    
    async def invalidate_blockchain_cache(self, analysis_id: UUID) -> bool:
        """
        Invalidate cached blockchain verification data for an analysis.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return True  # No cache to invalidate
        
        try:
            cache_keys = [
                f"blockchain_verification:{analysis_id}",
                f"blockchain_submission:{analysis_id}"
            ]
            
            # Delete all related keys
            deleted_count = 0
            for key in cache_keys:
                if await self.redis_client.delete(key):
                    deleted_count += 1
            
            logger.info(f"Invalidated {deleted_count} blockchain cache entries for analysis {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate blockchain cache for analysis {analysis_id}: {e}")
            return False
    
    # Private helper methods
    
    async def _verify_on_blockchain(self, blockchain_hash: Optional[str]) -> Optional[BlockchainVerificationStatus]:
        """Verify analysis on blockchain network"""
        if not blockchain_hash:
            return BlockchainVerificationStatus(
                verification_status="not_available",
                is_tamper_proof=False,
                verification_details={"reason": "No blockchain hash provided"}
            )
        
        try:
            # Verify transaction exists and is valid
            verification_result = await self.verify_transaction_hash(blockchain_hash)
            
            if verification_result.get('verified', False):
                return BlockchainVerificationStatus(
                    verification_status="verified",
                    solana_transaction_hash=blockchain_hash,
                    verification_timestamp=datetime.now(timezone.utc),
                    verification_details=verification_result.get('details', {}),
                    is_tamper_proof=True
                )
            else:
                return BlockchainVerificationStatus(
                    verification_status="failed",
                    verification_details=verification_result,
                    is_tamper_proof=False
                )
                
        except Exception as e:
            logger.error(f"Error verifying blockchain hash {blockchain_hash}: {e}")
            return BlockchainVerificationStatus(
                verification_status="error",
                verification_details={"error": str(e)},
                is_tamper_proof=False
            )
    
    async def _query_solana_network_status(self) -> Dict[str, Any]:
        """Query Solana network for current status"""
        try:
            async with self._get_session():
                # Query Solana RPC for network health
                health_data = await self._query_network_health()
                cluster_info = await self._query_cluster_info()
                
                network_status = {
                    'status': 'healthy' if health_data.get('health') == 'ok' else 'degraded',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'network_health': health_data,
                    'cluster_info': cluster_info,
                    'response_time_ms': health_data.get('response_time_ms', 0)
                }
                
                return network_status
                
        except Exception as e:
            logger.error(f"Error querying Solana network status: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
    
    async def _query_transaction_details(self, transaction_hash: str) -> Dict[str, Any]:
        """Query transaction details from Solana RPC"""
        try:
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    transaction_hash,
                    {
                        "encoding": "json",
                        "maxSupportedTransactionVersion": 0
                    }
                ]
            }
            
            async with self._get_session() as session:
                async with session.post(self.solana_config.network_url, json=rpc_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'result' in result and result['result']:
                            transaction_data = result['result']
                            return {
                                'status': 'verified',
                                'verified': True,
                                'confirmed_at': transaction_data.get('blockTime'),
                                'slot': transaction_data.get('slot'),
                                'details': {
                                    'signature': transaction_hash,
                                    'block_time': transaction_data.get('blockTime'),
                                    'slot': transaction_data.get('slot'),
                                    'confirmation_status': transaction_data.get('confirmationStatus')
                                }
                            }
                        else:
                            return {
                                'status': 'not_found',
                                'verified': False,
                                'error': 'Transaction not found'
                            }
                    else:
                        return {
                            'status': 'error',
                            'verified': False,
                            'error': f'RPC error: {response.status}'
                        }
                        
        except Exception as e:
            logger.error(f"Error querying transaction {transaction_hash}: {e}")
            return {
                'status': 'error',
                'verified': False,
                'error': str(e)
            }
    
    async def _query_network_health(self) -> Dict[str, Any]:
        """Query network health from Solana RPC"""
        try:
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }
            
            start_time = time.time()
            async with self._get_session() as session:
                async with session.post(self.solana_config.network_url, json=rpc_payload) as response:
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            'health': result.get('result', 'ok'),
                            'response_time_ms': round(response_time, 2)
                        }
                    else:
                        return {
                            'health': 'error',
                            'response_time_ms': round(response_time, 2),
                            'error': f'HTTP {response.status}'
                        }
                        
        except Exception as e:
            logger.error(f"Error querying network health: {e}")
            return {
                'health': 'error',
                'error': str(e)
            }
    
    async def _query_cluster_info(self) -> Dict[str, Any]:
        """Query cluster information from Solana RPC"""
        try:
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getClusterNodes"
            }
            
            async with self._get_session() as session:
                async with session.post(self.solana_config.network_url, json=rpc_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        nodes = result.get('result', [])
                        return {
                            'node_count': len(nodes),
                            'active_nodes': len([n for n in nodes if n.get('activatedStake', 0) > 0])
                        }
                    else:
                        return {
                            'node_count': 0,
                            'active_nodes': 0,
                            'error': f'HTTP {response.status}'
                        }
                        
        except Exception as e:
            logger.error(f"Error querying cluster info: {e}")
            return {
                'node_count': 0,
                'active_nodes': 0,
                'error': str(e)
            }
    
    def _generate_blockchain_payload(self, analysis_data: Dict[str, Any]) -> str:
        """Generate blockchain payload from analysis data"""
        # Create a deterministic payload for blockchain submission
        payload_data = {
            'analysis_id': str(analysis_data.get('analysis_id')),
            'overall_confidence': analysis_data.get('overall_confidence'),
            'frame_count': analysis_data.get('total_frames', 0),
            'suspicious_frames': analysis_data.get('suspicious_frames', 0),
            'processing_duration': analysis_data.get('processing_time_seconds', 0),
            'detection_methods': analysis_data.get('detection_methods_used', []),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checksum': hashlib.sha256(json.dumps(analysis_data, sort_keys=True).encode()).hexdigest()[:16]
        }
        
        return json.dumps(payload_data)
    
    async def _submit_transaction(self, payload: str) -> Optional[str]:
        """Submit transaction to blockchain (simulation)"""
        try:
            # In a real implementation, this would:
            # 1. Create a Solana transaction
            # 2. Sign it with private key
            # 3. Submit to network
            # 4. Wait for confirmation
            
            # For simulation, generate a mock transaction hash
            mock_hash = f"tx_{hashlib.sha256(payload.encode()).hexdigest()[:16]}"
            
            # Simulate network delay
            await asyncio.sleep(0.1)
            
            logger.debug(f"Simulated blockchain submission: {mock_hash}")
            return mock_hash
            
        except Exception as e:
            logger.error(f"Failed to submit transaction: {e}")
            return None
    
    def _is_valid_solana_hash(self, hash_str: str) -> bool:
        """Validate Solana transaction hash format"""
        try:
            # Solana transaction signatures are base58-encoded strings, typically 64 chars
            # Basic length check
            if len(hash_str) != 88:
                return False
            
            # Try to decode as base58
            decoded = base58.b58decode(hash_str)
            return len(decoded) == 64  # 64 bytes expected
            
        except Exception:
            return False
    
    def _is_cache_fresh(self, cached_data: Dict[str, Any], max_age_seconds: int = 60) -> bool:
        """Check if cached data is still fresh enough"""
        try:
            timestamp_str = cached_data.get('timestamp')
            if not timestamp_str:
                return False
            
            cached_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - cached_time).total_seconds()
            
            return age <= max_age_seconds
            
        except Exception:
            return False
    
    # Session management
    
    async def _get_session(self):
        """Get or create HTTP session"""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.solana_config.rpc_timeout)
            )
        return self._session
    
    # Cache helper methods
    
    async def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get data from Redis cache"""
        try:
            return await self.redis_client.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache get failed for key {cache_key}: {e}")
            return None
    
    async def _set_cache(self, cache_key: str, data: str, ttl_seconds: int = None) -> bool:
        """Set data in Redis cache"""
        try:
            ttl = ttl_seconds or self.solana_config.cache_ttl_seconds
            await self.redis_client.setex(cache_key, ttl, data)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {cache_key}: {e}")
            return False


# Service factory function
def get_blockchain_service(redis_client=None) -> BlockchainService:
    """
    Factory function to create BlockchainService instance.
    
    Args:
        redis_client: Optional Redis client for caching
        
    Returns:
        BlockchainService instance
    """
    return BlockchainService(redis_client)
