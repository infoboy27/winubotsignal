'use client';

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: string[];
}

const MCP_API_URL = process.env.NEXT_PUBLIC_MCP_API_URL || (typeof window !== 'undefined' ? window.location.origin.replace('chat.winu.app', 'mcp-api.winu.app') : 'http://mcp-server:8003');

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize with welcome message
    setMessages([{
      role: 'assistant',
      content: `🤖 Welcome to **Winu Bot Market Intelligence**!\n\nI'm your AI-powered cryptocurrency market analyst, powered by Llama 3.1 and integrated with real-time market data.\n\n**I can help you with:**\n\n📊 **Market Analysis**\n• Current market conditions and trends\n• Price analysis and predictions\n• Volume and liquidity insights\n\n💰 **Trading Intelligence**\n• Trading signals and opportunities\n• Entry/exit recommendations\n• Risk assessment\n\n📈 **Cryptocurrency Research**\n• Specific coins (BTC, ETH, ADA, SOL, DOT, etc.)\n• Historical performance analysis\n• Technical indicator explanations\n\n🔍 **Data-Driven Insights**\n• Real-time data from Binance\n• Market intelligence from CoinMarketCap\n• Historical data from Winu Bot database\n\n**Try asking:**\n• "What's the current market sentiment for Bitcoin?"\n• "Analyze ADA/USDT trading opportunities"\n• "What are the best performing coins today?"\n• "Explain the recent signals for SOL/USDT"`,
      timestamp: new Date().toISOString()
    }]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Use Next.js API route as proxy
      const apiUrl = typeof window !== 'undefined' 
        ? '/api/proxy' 
        : `${MCP_API_URL}/api/chat`;
      
      const response = await axios.post(apiUrl, {
        message: input,
        conversation_id: conversationId
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        sources: response.data.sources
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (!conversationId && response.data.conversation_id) {
        setConversationId(response.data.conversation_id);
      }
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.response?.data?.detail || error.message}. Please try again.`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex flex-col">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-sm border-b border-blue-500/20 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-green-400 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">W</span>
            </div>
            <div>
              <h1 className="text-white font-bold text-xl">Winu Bot</h1>
              <p className="text-gray-400 text-sm">Market Intelligence Chat</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span>Connected</span>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-4 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-green-400 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-bold text-sm">W</span>
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800/50 text-gray-100 border border-blue-500/20'
                }`}
              >
                <div className="whitespace-pre-wrap break-words">{message.content}</div>
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-700/50">
                    <p className="text-xs text-gray-400">
                      Sources: {message.sources.join(', ')}
                    </p>
                  </div>
                )}
                <p className="text-xs text-gray-400 mt-2">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
              {message.role === 'user' && (
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-bold text-sm">U</span>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-green-400 rounded-full flex items-center justify-center">
                <span className="text-white font-bold text-sm">W</span>
              </div>
              <div className="bg-gray-800/50 rounded-2xl px-4 py-3 border border-blue-500/20">
                <div className="flex gap-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input */}
      <footer className="bg-gray-800/50 backdrop-blur-sm border-t border-blue-500/20 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about markets, cryptocurrencies, trading signals..."
              className="flex-1 bg-gray-700/50 border border-blue-500/20 rounded-xl px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="bg-gradient-to-r from-blue-500 to-green-500 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-600 hover:to-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Send
            </button>
          </div>
          <div className="flex items-center justify-center gap-4 mt-2">
            <p className="text-xs text-gray-400">
              Powered by <span className="text-blue-400 font-semibold">Llama 3.1</span>
            </p>
            <span className="text-gray-600">•</span>
            <p className="text-xs text-gray-400">
              Data: <span className="text-green-400">Binance</span>, <span className="text-blue-400">CoinMarketCap</span>, <span className="text-purple-400">Winu Database</span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

