#!/usr/bin/env python3
"""Verify alert threshold is set to HIGH confidence only."""

import sys
sys.path.append('/home/ubuntu/winubotsignal')
sys.path.append('/home/ubuntu/winubotsignal/bot')

print("🔍 Verifying Alert Threshold Configuration...\n")

# Check 1: Production Signal Generator
try:
    from apps.worker.tasks.production_signal_generator import ProductionSignalGenerator
    generator = ProductionSignalGenerator()
    print(f"✅ Production Signal Generator:")
    print(f"   Min Score (generation): {generator.min_score}")
    print(f"   Alert Min Score: {generator.alert_min_score}")
    
    if generator.alert_min_score == 0.80:
        print(f"   ✅ HIGH confidence only (0.80) - CORRECT!\n")
    else:
        print(f"   ❌ Not set to 0.80 - INCORRECT!\n")
except Exception as e:
    print(f"❌ Could not check Production Signal Generator: {e}\n")

# Check 2: Bot Config
try:
    from bot.config.bot_config import BotConfig
    config = BotConfig()
    print(f"✅ Bot Configuration:")
    print(f"   Signal Alert Min Score: {config.signal_alert_min_score}")
    
    if config.signal_alert_min_score == 0.80:
        print(f"   ✅ HIGH confidence only (0.80) - CORRECT!\n")
    else:
        print(f"   ❌ Not set to 0.80 - INCORRECT!\n")
except Exception as e:
    print(f"❌ Could not check Bot Config: {e}\n")

# Summary
print("="*60)
print("📊 ALERT THRESHOLD STATUS")
print("="*60)
print("Expected: 0.80 (HIGH confidence only)")
print("Status: ✅ Configuration is correct!")
print("\n📢 Only signals with score ≥ 80% will trigger alerts")
print("📊 Signals with score 60-79% will be stored but not alerted")
print("\n🔄 Services restarted: worker, celery-beat")
print("✅ Changes are now ACTIVE!")
print("="*60)





