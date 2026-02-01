"""
Admin Payment Dashboard Router
Real-time payment status monitoring and management
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Dict, List
import json

from common.database import get_db
from routers.auth import get_current_active_user
from common.database import User

router = APIRouter(prefix="/api/admin/payments", tags=["Admin", "Payments"])


@router.get("/dashboard", response_class=HTMLResponse)
async def payment_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin dashboard showing payment status and gaps.
    """
    # Check if user is admin (you should implement proper admin check)
    # For now, we'll assume the user is authenticated
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Dashboard - Winu Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes pulse-green {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .pulse-green {
            animation: pulse-green 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
    </style>
</head>
<body class="bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 min-h-screen text-white">
    <div class="container mx-auto px-4 py-8">
        <header class="mb-8">
            <h1 class="text-4xl font-bold mb-2">💰 Payment Activation Dashboard</h1>
            <p class="text-blue-200">Real-time payment monitoring and gap detection</p>
            <div class="mt-4 flex items-center">
                <div class="w-3 h-3 bg-green-500 rounded-full pulse-green mr-2"></div>
                <span class="text-sm text-green-300">Live Monitoring Active</span>
            </div>
        </header>

        <!-- Stats Overview -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
                <div class="text-sm text-blue-200 mb-2">Total Payments (24h)</div>
                <div class="text-3xl font-bold" id="total-payments">-</div>
            </div>
            <div class="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
                <div class="text-sm text-green-200 mb-2">Successful</div>
                <div class="text-3xl font-bold text-green-400" id="successful-payments">-</div>
            </div>
            <div class="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
                <div class="text-sm text-red-200 mb-2">Activation Gaps</div>
                <div class="text-3xl font-bold text-red-400" id="gap-count">-</div>
            </div>
            <div class="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
                <div class="text-sm text-yellow-200 mb-2">Pending</div>
                <div class="text-3xl font-bold text-yellow-400" id="pending-payments">-</div>
            </div>
        </div>

        <!-- Activation Gaps Alert -->
        <div id="gaps-section" class="mb-8" style="display:none;">
            <div class="bg-red-500/20 border-2 border-red-500 rounded-lg p-6 mb-4">
                <h2 class="text-2xl font-bold text-red-400 mb-4">🚨 Payment Activation Gaps Detected</h2>
                <p class="text-red-200 mb-4">The following payments have completed but subscriptions were NOT activated:</p>
                <div id="gaps-list" class="space-y-3"></div>
            </div>
        </div>

        <!-- Recent Payments -->
        <div class="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20 mb-8">
            <h2 class="text-2xl font-bold mb-4">Recent Payments (Last 2 Hours)</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="border-b border-white/20">
                            <th class="py-3 px-4">User</th>
                            <th class="py-3 px-4">Plan</th>
                            <th class="py-3 px-4">Amount</th>
                            <th class="py-3 px-4">Status</th>
                            <th class="py-3 px-4">Method</th>
                            <th class="py-3 px-4">Time</th>
                            <th class="py-3 px-4">Subscription</th>
                        </tr>
                    </thead>
                    <tbody id="payments-table" class="divide-y divide-white/10">
                        <tr>
                            <td colspan="7" class="py-8 text-center text-gray-400">
                                Loading payments...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Recent Webhook Logs -->
        <div class="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20 mb-8">
            <h2 class="text-2xl font-bold mb-4">Recent Webhook Activity (Last 30 min)</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="border-b border-white/20">
                            <th class="py-3 px-4">Method</th>
                            <th class="py-3 px-4">Type</th>
                            <th class="py-3 px-4">User</th>
                            <th class="py-3 px-4">Status</th>
                            <th class="py-3 px-4">Signature</th>
                            <th class="py-3 px-4">Time</th>
                        </tr>
                    </thead>
                    <tbody id="webhooks-table" class="divide-y divide-white/10">
                        <tr>
                            <td colspan="6" class="py-8 text-center text-gray-400">
                                Loading webhooks...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="text-center text-sm text-gray-400 mt-8">
            <p>Auto-refreshing every 10 seconds</p>
            <p class="mt-2">Last updated: <span id="last-updated">Never</span></p>
        </div>
    </div>

    <script>
        async function fetchDashboardData() {
            try {
                const response = await fetch('/api/admin/payments/data');
                const data = await response.json();
                
                // Update stats
                document.getElementById('total-payments').textContent = data.stats.total_payments;
                document.getElementById('successful-payments').textContent = data.stats.successful_payments;
                document.getElementById('gap-count').textContent = data.stats.activation_gaps;
                document.getElementById('pending-payments').textContent = data.stats.pending_payments;
                
                // Update gaps
                if (data.gaps.length > 0) {
                    document.getElementById('gaps-section').style.display = 'block';
                    const gapsList = document.getElementById('gaps-list');
                    gapsList.innerHTML = data.gaps.map(gap => `
                        <div class="bg-red-900/30 border border-red-500/50 rounded p-4">
                            <div class="flex justify-between items-start">
                                <div>
                                    <div class="font-bold">User: ${gap.username} (ID: ${gap.user_id})</div>
                                    <div class="text-sm text-red-200">Plan: ${gap.plan_id} | Payment: ${gap.payment_status}</div>
                                    <div class="text-sm text-red-200">User Status: ${gap.subscription_status} / ${gap.subscription_tier}</div>
                                    <div class="text-xs text-gray-400 mt-2">${gap.payment_created}</div>
                                </div>
                                <button onclick="manualActivate(${gap.user_id}, '${gap.plan_id}')"
                                        class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm font-semibold">
                                    Manual Activate
                                </button>
                            </div>
                        </div>
                    `).join('');
                } else {
                    document.getElementById('gaps-section').style.display = 'none';
                }
                
                // Update recent payments
                const paymentsTable = document.getElementById('payments-table');
                if (data.recent_payments.length > 0) {
                    paymentsTable.innerHTML = data.recent_payments.map(payment => {
                        const statusColor = payment.payment_status === 'completed' ? 'text-green-400' : 'text-yellow-400';
                        const subStatusColor = payment.subscription_status === 'active' ? 'text-green-400' : 'text-red-400';
                        return `
                            <tr>
                                <td class="py-3 px-4">${payment.username || 'N/A'} (${payment.user_id})</td>
                                <td class="py-3 px-4">${payment.plan_id}</td>
                                <td class="py-3 px-4">$${payment.amount_usd || '0.00'}</td>
                                <td class="py-3 px-4 ${statusColor}">${payment.payment_status}</td>
                                <td class="py-3 px-4">${payment.payment_method}</td>
                                <td class="py-3 px-4 text-sm text-gray-400">${payment.created_at}</td>
                                <td class="py-3 px-4 ${subStatusColor}">${payment.subscription_status}</td>
                            </tr>
                        `;
                    }).join('');
                } else {
                    paymentsTable.innerHTML = `
                        <tr>
                            <td colspan="7" class="py-8 text-center text-gray-400">
                                No recent payments
                            </td>
                        </tr>
                    `;
                }
                
                // Update webhook logs
                const webhooksTable = document.getElementById('webhooks-table');
                if (data.recent_webhooks.length > 0) {
                    webhooksTable.innerHTML = data.recent_webhooks.map(webhook => {
                        const statusColor = webhook.processing_status === 'completed' ? 'text-green-400' : 
                                          webhook.processing_status === 'failed' ? 'text-red-400' : 'text-yellow-400';
                        const sigColor = webhook.signature_valid === true ? 'text-green-400' : 
                                       webhook.signature_valid === false ? 'text-red-400' : 'text-gray-400';
                        const sigText = webhook.signature_valid === true ? '✓ Valid' : 
                                      webhook.signature_valid === false ? '✗ Invalid' : '-';
                        return `
                            <tr>
                                <td class="py-3 px-4">${webhook.payment_method}</td>
                                <td class="py-3 px-4">${webhook.webhook_type || '-'}</td>
                                <td class="py-3 px-4">${webhook.user_id || '-'}</td>
                                <td class="py-3 px-4 ${statusColor}">${webhook.processing_status}</td>
                                <td class="py-3 px-4 ${sigColor}">${sigText}</td>
                                <td class="py-3 px-4 text-sm text-gray-400">${webhook.created_at}</td>
                            </tr>
                        `;
                    }).join('');
                } else {
                    webhooksTable.innerHTML = `
                        <tr>
                            <td colspan="6" class="py-8 text-center text-gray-400">
                                No recent webhooks
                            </td>
                        </tr>
                    `;
                }
                
                document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error fetching dashboard data:', error);
            }
        }
        
        async function manualActivate(userId, planId) {
            if (!confirm(`Manually activate subscription for user ${userId} with plan ${planId}?`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/admin/subscriptions/activate-manual', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: userId,
                        plan_id: planId,
                        reason: 'Manual activation from dashboard - webhook failure'
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('Subscription activated successfully!');
                    fetchDashboardData(); // Refresh
                } else {
                    alert('Failed to activate: ' + (result.message || 'Unknown error'));
                }
            } catch (error) {
                alert('Error activating subscription: ' + error.message);
            }
        }
        
        // Initial load
        fetchDashboardData();
        
        // Auto-refresh every 10 seconds
        setInterval(fetchDashboardData, 10000);
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/data")
async def payment_dashboard_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard data as JSON.
    """
    try:
        # Get stats
        stats_query = text("""
            SELECT 
                COUNT(*) as total_payments,
                COUNT(CASE WHEN status IN ('completed', 'confirmed', 'finished', 'paid') THEN 1 END) as successful_payments,
                COUNT(CASE WHEN status IN ('pending', 'waiting') THEN 1 END) as pending_payments
            FROM payment_transactions
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.fetchone()
        
        # Get activation gaps
        gaps_query = text("""
            SELECT 
                pt.id as payment_id,
                pt.user_id,
                pt.plan_id,
                pt.status as payment_status,
                pt.transaction_id,
                pt.created_at as payment_created,
                u.username,
                u.email,
                u.subscription_status,
                u.subscription_tier
            FROM payment_transactions pt
            JOIN users u ON pt.user_id = u.id
            WHERE pt.status IN ('completed', 'confirmed', 'finished', 'paid')
            AND pt.created_at >= NOW() - INTERVAL '2 hours'
            AND (u.subscription_status != 'active' OR u.subscription_tier != pt.plan_id)
            ORDER BY pt.created_at DESC
        """)
        gaps_result = await db.execute(gaps_query)
        gaps_rows = gaps_result.fetchall()
        
        # Get recent payments
        payments_query = text("""
            SELECT 
                pt.id,
                pt.user_id,
                pt.plan_id,
                pt.amount_usd,
                pt.status as payment_status,
                pt.payment_method,
                pt.created_at,
                u.username,
                u.subscription_status
            FROM payment_transactions pt
            JOIN users u ON pt.user_id = u.id
            WHERE pt.created_at >= NOW() - INTERVAL '2 hours'
            ORDER BY pt.created_at DESC
            LIMIT 20
        """)
        payments_result = await db.execute(payments_query)
        payments_rows = payments_result.fetchall()
        
        # Get recent webhooks
        webhooks_query = text("""
            SELECT 
                id,
                payment_method,
                webhook_type,
                user_id,
                processing_status,
                signature_valid,
                created_at
            FROM webhook_logs
            WHERE created_at >= NOW() - INTERVAL '30 minutes'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        webhooks_result = await db.execute(webhooks_query)
        webhooks_rows = webhooks_result.fetchall()
        
        return {
            "stats": {
                "total_payments": stats_row[0],
                "successful_payments": stats_row[1],
                "pending_payments": stats_row[2],
                "activation_gaps": len(gaps_rows)
            },
            "gaps": [
                {
                    "payment_id": row[0],
                    "user_id": row[1],
                    "plan_id": row[2],
                    "payment_status": row[3],
                    "transaction_id": row[4],
                    "payment_created": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                    "username": row[6],
                    "email": row[7],
                    "subscription_status": row[8],
                    "subscription_tier": row[9]
                }
                for row in gaps_rows
            ],
            "recent_payments": [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "plan_id": row[2],
                    "amount_usd": str(row[3]) if row[3] else "0.00",
                    "payment_status": row[4],
                    "payment_method": row[5],
                    "created_at": row[6].strftime("%H:%M:%S") if row[6] else None,
                    "username": row[7],
                    "subscription_status": row[8]
                }
                for row in payments_rows
            ],
            "recent_webhooks": [
                {
                    "id": row[0],
                    "payment_method": row[1],
                    "webhook_type": row[2],
                    "user_id": row[3],
                    "processing_status": row[4],
                    "signature_valid": row[5],
                    "created_at": row[6].strftime("%H:%M:%S") if row[6] else None
                }
                for row in webhooks_rows
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")

