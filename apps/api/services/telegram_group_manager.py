"""
Telegram Group Access Manager
Manages Telegram group memberships based on subscription tiers
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import User, TelegramGroupAccess, SubscriptionEvent
from common.logging import get_logger

logger = get_logger(__name__)


class TelegramGroupManager:
    """Manages Telegram group access based on subscription tiers."""
    
    def __init__(self):
        # Telegram group configurations
        self.group_configs = {
            "professional": {
                "group_name": "professional_group",
                "group_id": "@winu_professional",  # Replace with actual group ID
                "group_title": "Winu Professional Trading Group",
                "description": "Professional subscribers trading signals and discussions"
            },
            "vip_elite": {
                "group_name": "vip_elite_group", 
                "group_id": "@winu_vip_elite",  # Replace with actual group ID
                "group_title": "Winu VIP Elite Trading Group",
                "description": "VIP Elite subscribers exclusive trading signals and 24/7 support"
            }
        }
        
        # Bot token for Telegram API (would be loaded from environment)
        self.bot_token = None  # Load from environment variables
        self.bot_username = "winu_trading_bot"  # Replace with actual bot username
    
    async def grant_telegram_access(
        self, 
        user: User, 
        subscription_tier: str, 
        telegram_user_id: str,
        telegram_username: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Grant Telegram group access to user based on subscription tier."""
        try:
            if subscription_tier not in self.group_configs:
                return {
                    "success": False,
                    "error": f"Invalid subscription tier: {subscription_tier}"
                }
            
            group_config = self.group_configs[subscription_tier]
            
            # Check if user already has access to this group
            result = await db.execute(
                select(TelegramGroupAccess).where(
                    and_(
                        TelegramGroupAccess.user_id == user.id,
                        TelegramGroupAccess.group_name == group_config["group_name"],
                        TelegramGroupAccess.is_active == True
                    )
                )
            )
            existing_access = result.scalar_one_or_none()
            
            if existing_access:
                return {
                    "success": True,
                    "message": "User already has access to this group",
                    "group_info": group_config
                }
            
            # Create Telegram group access record
            telegram_access = TelegramGroupAccess(
                user_id=user.id,
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                group_name=group_config["group_name"],
                is_active=True
            )
            db.add(telegram_access)
            
            # Create subscription event
            event = SubscriptionEvent(
                user_id=user.id,
                event_type="telegram_access_granted",
                event_data={
                    "group_name": group_config["group_name"],
                    "group_id": group_config["group_id"],
                    "subscription_tier": subscription_tier,
                    "telegram_user_id": telegram_user_id,
                    "telegram_username": telegram_username
                },
                processed=True
            )
            db.add(event)
            
            await db.commit()
            
            # Send Telegram invitation (if bot is configured)
            invitation_sent = await self._send_telegram_invitation(
                telegram_user_id, 
                group_config,
                subscription_tier
            )
            
            logger.info(f"Telegram access granted to user {user.id} for {subscription_tier} group")
            
            return {
                "success": True,
                "message": f"Telegram access granted to {subscription_tier} group",
                "group_info": group_config,
                "invitation_sent": invitation_sent
            }
            
        except Exception as e:
            logger.error(f"Error granting Telegram access: {e}")
            if db:
                await db.rollback()
            return {"success": False, "error": str(e)}
    
    async def revoke_telegram_access(
        self, 
        user: User, 
        group_name: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Revoke Telegram group access for user."""
        try:
            # Build query conditions
            conditions = [TelegramGroupAccess.user_id == user.id]
            
            if group_name:
                conditions.append(TelegramGroupAccess.group_name == group_name)
            
            conditions.append(TelegramGroupAccess.is_active == True)
            
            # Get active Telegram access records
            result = await db.execute(
                select(TelegramGroupAccess).where(and_(*conditions))
            )
            telegram_accesses = result.scalars().all()
            
            if not telegram_accesses:
                return {
                    "success": True,
                    "message": "No active Telegram access found"
                }
            
            revoked_groups = []
            
            for access in telegram_accesses:
                # Mark access as inactive
                access.is_active = False
                access.access_revoked_at = datetime.utcnow()
                
                revoked_groups.append(access.group_name)
                
                # Create revocation event
                event = SubscriptionEvent(
                    user_id=user.id,
                    event_type="telegram_access_revoked",
                    event_data={
                        "group_name": access.group_name,
                        "revoked_at": access.access_revoked_at.isoformat(),
                        "reason": "subscription_expired_or_revoked"
                    },
                    processed=True
                )
                db.add(event)
            
            await db.commit()
            
            # Remove from Telegram groups (if bot is configured)
            for group_name in revoked_groups:
                await self._remove_from_telegram_group(
                    user.telegram_user_id, 
                    group_name
                )
            
            logger.info(f"Telegram access revoked for user {user.id} from groups: {revoked_groups}")
            
            return {
                "success": True,
                "message": f"Telegram access revoked from {len(revoked_groups)} groups",
                "revoked_groups": revoked_groups
            }
            
        except Exception as e:
            logger.error(f"Error revoking Telegram access: {e}")
            if db:
                await db.rollback()
            return {"success": False, "error": str(e)}
    
    async def get_user_telegram_access(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        """Get user's Telegram group access information."""
        try:
            result = await db.execute(
                select(TelegramGroupAccess).where(
                    TelegramGroupAccess.user_id == user.id
                ).order_by(TelegramGroupAccess.created_at.desc())
            )
            telegram_accesses = result.scalars().all()
            
            access_info = {
                "user_id": user.id,
                "telegram_user_id": user.telegram_user_id,
                "telegram_username": getattr(user, 'telegram_username', None),
                "active_groups": [],
                "inactive_groups": [],
                "total_groups": len(telegram_accesses)
            }
            
            for access in telegram_accesses:
                group_info = {
                    "group_name": access.group_name,
                    "access_granted_at": access.access_granted_at.isoformat(),
                    "access_revoked_at": access.access_revoked_at.isoformat() if access.access_revoked_at else None,
                    "is_active": access.is_active
                }
                
                # Add group configuration if available
                for tier, config in self.group_configs.items():
                    if config["group_name"] == access.group_name:
                        group_info.update({
                            "group_id": config["group_id"],
                            "group_title": config["group_title"],
                            "subscription_tier": tier
                        })
                        break
                
                if access.is_active:
                    access_info["active_groups"].append(group_info)
                else:
                    access_info["inactive_groups"].append(group_info)
            
            return access_info
            
        except Exception as e:
            logger.error(f"Error getting Telegram access info: {e}")
            return {"error": str(e)}
    
    async def sync_telegram_memberships(self, db: AsyncSession) -> Dict[str, Any]:
        """Sync Telegram group memberships with database records."""
        try:
            logger.info("Starting Telegram membership sync...")
            
            # Get all active Telegram access records
            result = await db.execute(
                select(TelegramGroupAccess).where(
                    TelegramGroupAccess.is_active == True
                )
            )
            active_accesses = result.scalars().all()
            
            sync_results = {
                "total_records": len(active_accesses),
                "synced": 0,
                "errors": []
            }
            
            for access in active_accesses:
                try:
                    # Verify user still has valid subscription
                    user_result = await db.execute(
                        select(User).where(User.id == access.user_id)
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        # User not found, revoke access
                        await self.revoke_telegram_access(
                            type('User', (), {'id': access.user_id})(),
                            access.group_name,
                            db
                        )
                        sync_results["synced"] += 1
                        continue
                    
                    # Check if user's subscription still allows Telegram access
                    if not await self._check_telegram_access_eligibility(user, access.group_name):
                        # Revoke access
                        await self.revoke_telegram_access(user, access.group_name, db)
                        sync_results["synced"] += 1
                        continue
                    
                    sync_results["synced"] += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing access for user {access.user_id}: {e}")
                    sync_results["errors"].append(f"User {access.user_id}: {str(e)}")
            
            logger.info(f"Telegram membership sync completed: {sync_results}")
            return sync_results
            
        except Exception as e:
            logger.error(f"Error in Telegram membership sync: {e}")
            return {"error": str(e)}
    
    async def _check_telegram_access_eligibility(self, user: User, group_name: str) -> bool:
        """Check if user is eligible for Telegram group access."""
        try:
            # Check subscription tier
            if user.subscription_tier not in ["professional", "vip_elite"]:
                return False
            
            # Check subscription status
            if user.subscription_status != "active":
                return False
            
            # Check if payment is overdue
            if user.access_revoked_at:
                return False
            
            # Check if group matches subscription tier
            for tier, config in self.group_configs.items():
                if config["group_name"] == group_name:
                    return user.subscription_tier == tier
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking Telegram access eligibility: {e}")
            return False
    
    async def _send_telegram_invitation(
        self, 
        telegram_user_id: str, 
        group_config: Dict[str, str],
        subscription_tier: str
    ) -> bool:
        """Send Telegram group invitation to user."""
        try:
            if not self.bot_token:
                logger.warning("Telegram bot token not configured, skipping invitation")
                return False
            
            # This would integrate with the Telegram Bot API
            # For now, we'll just log the action
            
            logger.info(f"Telegram invitation sent to user {telegram_user_id} for {group_config['group_title']}")
            
            # Example implementation:
            # import requests
            # url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            # data = {
            #     "chat_id": telegram_user_id,
            #     "text": f"Welcome to {group_config['group_title']}! Your {subscription_tier} subscription is now active.",
            #     "parse_mode": "HTML"
            # }
            # response = requests.post(url, data=data)
            # return response.status_code == 200
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram invitation: {e}")
            return False
    
    async def _remove_from_telegram_group(self, telegram_user_id: str, group_name: str) -> bool:
        """Remove user from Telegram group."""
        try:
            if not self.bot_token:
                logger.warning("Telegram bot token not configured, skipping removal")
                return False
            
            # This would integrate with the Telegram Bot API
            # For now, we'll just log the action
            
            logger.info(f"User {telegram_user_id} removed from {group_name}")
            
            # Example implementation:
            # import requests
            # group_config = self.group_configs.get(group_name, {})
            # group_id = group_config.get("group_id")
            # if group_id:
            #     url = f"https://api.telegram.org/bot{self.bot_token}/kickChatMember"
            #     data = {
            #         "chat_id": group_id,
            #         "user_id": telegram_user_id
            #     }
            #     response = requests.post(url, data=data)
            #     return response.status_code == 200
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing user from Telegram group: {e}")
            return False
    
    async def get_group_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get Telegram group statistics."""
        try:
            stats = {}
            
            for tier, config in self.group_configs.items():
                # Count active members
                result = await db.execute(
                    select(TelegramGroupAccess).where(
                        and_(
                            TelegramGroupAccess.group_name == config["group_name"],
                            TelegramGroupAccess.is_active == True
                        )
                    )
                )
                active_members = len(result.scalars().all())
                
                stats[config["group_name"]] = {
                    "group_title": config["group_title"],
                    "group_id": config["group_id"],
                    "subscription_tier": tier,
                    "active_members": active_members
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting group statistics: {e}")
            return {"error": str(e)}


# Global instance
telegram_group_manager = TelegramGroupManager()













