'use client';

import { useState, useEffect } from 'react';
import { 
  MessageCircle, 
  Check, 
  X, 
  Clock, 
  ExternalLink,
  Copy,
  RefreshCw
} from 'lucide-react';
import toast from 'react-hot-toast';

interface TelegramStatus {
  is_linked: boolean;
  telegram_user_id: string | null;
  telegram_username: string | null;
  linked_at: string | null;
}

interface VerificationData {
  verification_code: string;
  instructions: string;
  expires_at: string;
}

export default function TelegramLink() {
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [verification, setVerification] = useState<VerificationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [telegramUsername, setTelegramUsername] = useState('');

  useEffect(() => {
    fetchTelegramStatus();
  }, []);

  const fetchTelegramStatus = async () => {
    try {
      const response = await fetch('/api/telegram/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Error fetching Telegram status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLinkTelegram = async () => {
    if (!telegramUsername.trim()) {
      toast.error('Please enter your Telegram username');
      return;
    }

    setProcessing(true);
    try {
      const response = await fetch('/api/telegram/link', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          telegram_username: telegramUsername.trim()
        })
      });

      if (response.ok) {
        const data = await response.json();
        setVerification(data);
        toast.success('Verification code generated! Check the instructions below.');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to generate verification code');
      }
    } catch (error) {
      console.error('Error linking Telegram:', error);
      toast.error('Failed to link Telegram account');
    } finally {
      setProcessing(false);
    }
  };

  const handleVerifyCode = async (code: string) => {
    try {
      const response = await fetch(`/api/telegram/verify?code=${code}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        toast.success('Telegram account linked successfully!');
        setVerification(null);
        fetchTelegramStatus();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to verify code');
      }
    } catch (error) {
      console.error('Error verifying code:', error);
      toast.error('Failed to verify code');
    }
  };

  const handleUnlink = async () => {
    try {
      const response = await fetch('/api/telegram/unlink', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        toast.success('Telegram account unlinked');
        fetchTelegramStatus();
      } else {
        toast.error('Failed to unlink Telegram account');
      }
    } catch (error) {
      console.error('Error unlinking Telegram:', error);
      toast.error('Failed to unlink Telegram account');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-8 h-8 bg-gradient-to-r from-blue-400 to-blue-500 rounded-lg flex items-center justify-center">
          <MessageCircle className="w-4 h-4 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Telegram Integration</h3>
      </div>

      {status?.is_linked ? (
        <div className="space-y-4">
          <div className="flex items-center space-x-3 p-4 bg-green-50 rounded-lg">
            <Check className="w-5 h-5 text-green-500" />
            <div>
              <p className="font-medium text-green-900">Telegram Account Linked</p>
              <p className="text-sm text-green-700">@{status.telegram_username}</p>
            </div>
          </div>

          <div className="text-sm text-gray-600">
            <p>Your Telegram account is connected and you'll receive trading signals in our private group.</p>
          </div>

          <button
            onClick={handleUnlink}
            className="text-red-600 hover:text-red-700 text-sm font-medium"
          >
            Unlink Telegram Account
          </button>
        </div>
      ) : verification ? (
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">Link Your Telegram Account</h4>
            <p className="text-sm text-blue-700 mb-4">
              Follow these steps to link your Telegram account:
            </p>
            <ol className="text-sm text-blue-700 space-y-2 list-decimal list-inside">
              <li>Open Telegram and search for @WinuBotSignal</li>
              <li>Start a conversation with the bot</li>
              <li>Send the command: <code className="bg-blue-100 px-2 py-1 rounded">/link {verification.verification_code}</code></li>
              <li>The bot will verify your account and link it</li>
            </ol>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex-1 bg-gray-100 p-3 rounded-lg font-mono text-sm">
              /link {verification.verification_code}
            </div>
            <button
              onClick={() => copyToClipboard(`/link ${verification.verification_code}`)}
              className="p-2 text-gray-500 hover:text-gray-700"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <Clock className="w-4 h-4" />
            <span>Code expires at {new Date(verification.expires_at).toLocaleTimeString()}</span>
          </div>

          <div className="flex space-x-2">
            <button
              onClick={() => setVerification(null)}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              onClick={() => fetchTelegramStatus()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Check Status</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-sm text-gray-600">
            <p>Link your Telegram account to receive trading signals directly in our private group.</p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Telegram Username
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={telegramUsername}
                  onChange={(e) => setTelegramUsername(e.target.value)}
                  placeholder="Enter your Telegram username (without @)"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleLinkTelegram}
                  disabled={processing || !telegramUsername.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {processing ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <>
                      <MessageCircle className="w-4 h-4" />
                      <span>Link</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          <div className="text-xs text-gray-500">
            <p>You'll receive a verification code to confirm your Telegram account.</p>
          </div>
        </div>
      )}
    </div>
  );
}
