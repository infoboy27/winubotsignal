'use client';

import { useState, useEffect } from 'react';
import './landing.css';

interface TradingSignal {
  symbol: string;
  direction: 'LONG' | 'SHORT';
  score: number;
  price: number;
  change: number;
  timestamp: string;
}

export default function LandingPage() {
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [currentSignalIndex, setCurrentSignalIndex] = useState(0);

  // Event handlers
  const handleStartFreeTrial = () => {
    window.location.href = '/register';
  };

  const handleLogin = () => {
    window.location.href = '/login';
  };

  const handleWatchDemo = () => {
    scrollToSection('demo');
  };

  const handleViewLiveDemo = () => {
    scrollToSection('demo');
  };

  const handleGetStarted = () => {
    window.location.href = '/register';
  };

  const handleGoVIP = () => {
    window.location.href = '/register';
  };

  // Mock trading signals data
  const mockSignals: TradingSignal[] = [
    { symbol: 'BTC/USDT', direction: 'LONG', score: 87, price: 43250.50, change: 2.3, timestamp: '14:32' },
    { symbol: 'ETH/USDT', direction: 'SHORT', score: 92, price: 2650.75, change: -1.8, timestamp: '14:28' },
    { symbol: 'SOL/USDT', direction: 'LONG', score: 78, price: 98.45, change: 4.2, timestamp: '14:25' },
    { symbol: 'ADA/USDT', direction: 'LONG', score: 85, price: 0.485, change: 3.1, timestamp: '14:22' },
    { symbol: 'DOT/USDT', direction: 'SHORT', score: 89, price: 7.85, change: -2.5, timestamp: '14:18' },
    { symbol: 'SYRUP/USDT', direction: 'LONG', score: 94, price: 0.125, change: 8.7, timestamp: '14:15' },
  ];

  useEffect(() => {
    setSignals(mockSignals);
    
    // Rotate signals every 3 seconds
    const interval = setInterval(() => {
      setCurrentSignalIndex((prev) => (prev + 1) % mockSignals.length);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="nav-logo">
            <span className="logo-icon">🚀</span>
            <span className="logo-text">Winu</span>
          </div>
          <div className="nav-menu">
            <button onClick={() => scrollToSection('features')} className="nav-link">Features</button>
            <button onClick={() => scrollToSection('pricing')} className="nav-link">Pricing</button>
            <button onClick={() => scrollToSection('demo')} className="nav-link">Demo</button>
            <div className="nav-social">
              <a href="https://t.me/winuapcom" target="_blank" rel="noopener noreferrer" className="nav-social-link" aria-label="Telegram">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                </svg>
              </a>
              <a href="https://discord.gg/5dZcxqsM" target="_blank" rel="noopener noreferrer" className="nav-social-link" aria-label="Discord">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
                </svg>
              </a>
              <a href="https://x.com/winuapp" target="_blank" rel="noopener noreferrer" className="nav-social-link" aria-label="Twitter">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
              </a>
              <a href="https://www.instagram.com/winuapp" target="_blank" rel="noopener noreferrer" className="nav-social-link" aria-label="Instagram">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                </svg>
              </a>
            </div>
            <button onClick={handleLogin} className="btn-brand">
              <span>Login</span>
            </button>
            <button onClick={handleStartFreeTrial} className="btn-primary">Start Free Trial</button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-container">
          <div className="hero-content">
            <div className="hero-badge">
              <span className="badge-icon">⚡</span>
              <span>AI-Powered Trading Signals</span>
            </div>
            
            <h1 className="hero-title">
              Master the Crypto Markets with
              <span className="gradient-text"> Professional Trading Signals</span>
            </h1>
            
            <p className="hero-description">
              Get real-time alerts for trending coins with advanced technical analysis, 
              smart money insights, and multi-source data validation. Join thousands of 
              traders making informed decisions with our AI-powered platform.
            </p>
            
            <div className="hero-actions">
              <button onClick={handleStartFreeTrial} className="btn-primary btn-large">
                <span>Start Free 7-Day Trial</span>
                <span className="btn-icon">→</span>
              </button>
              <button onClick={handleWatchDemo} className="btn-secondary btn-large">
                <span className="play-icon">▶</span>
                <span>Watch Demo</span>
              </button>
            </div>
            
            <div className="hero-stats">
              <div className="stat">
                <span className="stat-number">10,000+</span>
                <span className="stat-label">Active Traders</span>
              </div>
              <div className="stat">
                <span className="stat-number">85%</span>
                <span className="stat-label">Success Rate</span>
              </div>
              <div className="stat">
                <span className="stat-number">24/7</span>
                <span className="stat-label">Market Monitoring</span>
              </div>
            </div>
          </div>
          
          <div className="hero-visual">
            <div className="trading-bot-container">
              <div className="laptop-screen">
                <div className="screen-header">
                  <div className="screen-dots">
                    <span className="dot red"></span>
                    <span className="dot yellow"></span>
                    <span className="dot green"></span>
                  </div>
                  <div className="screen-title">Winu Trading Bot</div>
                </div>
                <div className="screen-content">
                  <div className="bot-status">
                    <div className="status-indicator active">
                      <div className="pulse-ring"></div>
                    </div>
                    <span>Bot Active - Analyzing Markets</span>
                  </div>
                  
                  <div className="trading-dashboard">
                    <div className="dashboard-header">
                      <h3>Live Trading Signals</h3>
                      <div className="live-indicator">
                        <span className="pulse"></span>
                        <span>LIVE</span>
                      </div>
                    </div>
                    
                    <div className="signals-list">
                      <div className="signal-item">
                        <div className="signal-symbol">{signals[currentSignalIndex]?.symbol}</div>
                        <div className={`signal-direction ${signals[currentSignalIndex]?.direction.toLowerCase()}`}>
                          {signals[currentSignalIndex]?.direction}
                        </div>
                        <div className="signal-score">{signals[currentSignalIndex]?.score}%</div>
                        <div className="signal-price">${signals[currentSignalIndex]?.price.toFixed(2)}</div>
                        <div className={`signal-change ${signals[currentSignalIndex]?.change > 0 ? 'positive' : 'negative'}`}>
                          {signals[currentSignalIndex]?.change > 0 ? '+' : ''}{signals[currentSignalIndex]?.change}%
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="profit-display">
                    <div className="profit-item">
                      <span className="profit-label">Today's P&L</span>
                      <span className="profit-value positive">+$2,847.32</span>
                    </div>
                    <div className="profit-item">
                      <span className="profit-label">Win Rate</span>
                      <span className="profit-value positive">87.5%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="laptop-base"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Advanced Analysis Engine</h2>
            <p className="section-description">
              Our AI-powered system performs comprehensive market analysis using multiple data sources and advanced algorithms.
            </p>
          </div>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3>Technical Analysis</h3>
              <p>20+ Professional Indicators</p>
              <ul className="feature-list">
                <li>Momentum: RSI, Stochastic, Williams %R, CCI</li>
                <li>Trend: MACD, EMA/SMA, ADX, Ichimoku Cloud</li>
                <li>Volatility: Bollinger Bands, ATR, VWAP</li>
                <li>Volume: OBV, Volume Profile, Volume Anomalies</li>
              </ul>
            </div>
            
            <div className="feature-card">
              <div className="feature-icon">🧠</div>
              <h3>Smart Money Analysis</h3>
              <p>Institutional Trading Insights</p>
              <ul className="feature-list">
                <li>Order Blocks - Institutional zones</li>
                <li>Fair Value Gaps - Price inefficiencies</li>
                <li>Liquidity Zones - High probability areas</li>
                <li>Stop Hunts - Liquidity sweep detection</li>
                <li>Volume Flow - Institutional vs retail</li>
              </ul>
            </div>
            
            <div className="feature-card">
              <div className="feature-icon">🔗</div>
              <h3>Multi-Source Integration</h3>
              <p>Cross-Exchange Validation</p>
              <ul className="feature-list">
                <li>Binance - Primary price and volume data</li>
                <li>Gate.io - Cross-exchange validation</li>
                <li>CoinMarketCap - Market cap and sentiment</li>
                <li>Real-time news impact analysis</li>
              </ul>
            </div>
            
            <div className="feature-card">
              <div className="feature-icon">🛡️</div>
              <h3>Risk Management</h3>
              <p>Professional Risk Controls</p>
              <ul className="feature-list">
                <li>Position Sizing - Kelly Criterion</li>
                <li>Volatility Analysis - ATR-based stops</li>
                <li>Risk/Reward Ratios - Minimum 1.5:1</li>
                <li>Portfolio Heat - Maximum exposure limits</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Section */}
      <section id="demo" className="demo">
        <div className="container">
          <div className="demo-content">
            <div className="demo-text">
              <h2>See the Bot in Action</h2>
              <p>Watch our AI analyze real market data and generate professional trading signals in real-time.</p>
              <div className="demo-features">
                <div className="demo-feature">
                  <span className="check-icon">✓</span>
                  <span>Real-time market scanning</span>
                </div>
                <div className="demo-feature">
                  <span className="check-icon">✓</span>
                  <span>Multi-timeframe analysis</span>
                </div>
                <div className="demo-feature">
                  <span className="check-icon">✓</span>
                  <span>Instant Telegram & Discord alerts</span>
                </div>
              </div>
            </div>
            <div className="demo-visual">
              <div className="demo-screen">
                <div className="demo-header">
                  <div className="demo-dots">
                    <span className="dot red"></span>
                    <span className="dot yellow"></span>
                    <span className="dot green"></span>
                  </div>
                  <span>Live Demo - Winu Trading Bot</span>
                </div>
                <div className="demo-content-area">
                  <div className="demo-chart">
                    <div className="chart-header">
                      <span>BTC/USDT - 1H Chart</span>
                      <span className="chart-status positive">+3.2%</span>
                    </div>
                    <div className="chart-area">
                      <div className="chart-line"></div>
                      <div className="chart-signals">
                        <div className="signal-marker long">LONG</div>
                        <div className="signal-marker short">SHORT</div>
                      </div>
                    </div>
                  </div>
                  <div className="demo-alerts">
                    <div className="alert-item">
                      <span className="alert-time">14:32</span>
                      <span className="alert-symbol">ETH/USDT</span>
                      <span className="alert-action long">LONG</span>
                      <span className="alert-score">87%</span>
                    </div>
                    <div className="alert-item">
                      <span className="alert-time">14:28</span>
                      <span className="alert-symbol">SOL/USDT</span>
                      <span className="alert-action short">SHORT</span>
                      <span className="alert-score">92%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="pricing">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Choose Your Plan</h2>
            <p className="section-description">
              Start with our free trial and upgrade when you're ready to maximize your trading potential.
            </p>
          </div>
          <div className="pricing-grid">
            <div className="pricing-card">
              <div className="pricing-header">
                <h3>Free Trial</h3>
                <div className="pricing-badge">7 Days Free</div>
                <div className="pricing-price">
                  <span className="price-currency">$</span>
                  <span className="price-amount">0</span>
                  <span className="price-period">/month</span>
                </div>
              </div>
              <ul className="pricing-features">
                <li>✓ Basic trading signals</li>
                <li>✓ 3 trending coins</li>
                <li>✓ Telegram alerts</li>
                <li>✓ Basic technical analysis</li>
                <li>✓ 24/7 support</li>
              </ul>
              <button onClick={handleStartFreeTrial} className="btn-outline">Start Free Trial</button>
            </div>
            
            <div className="pricing-card featured">
              <div className="pricing-badge popular">Most Popular</div>
              <div className="pricing-header">
                <h3>Professional</h3>
                <div className="pricing-price">
                  <span className="price-original">$39</span>
                  <span className="price-currency">$</span>
                  <span className="price-amount">15</span>
                  <span className="price-period">/month</span>
                </div>
              </div>
              <ul className="pricing-features">
                <li>✓ Advanced trading signals</li>
                <li>✓ 10 trending coins</li>
                <li>✓ Telegram & Discord alerts</li>
                <li>✓ Smart money analysis</li>
                <li>✓ Risk management tools</li>
                <li>✓ Multi-timeframe analysis</li>
                <li>✓ Priority support</li>
              </ul>
              <button onClick={handleGetStarted} className="btn-primary">Get Started</button>
            </div>
            
            <div className="pricing-card">
              <div className="pricing-header">
                <h3>VIP Elite</h3>
                <div className="pricing-price">
                  <span className="price-currency">$</span>
                  <span className="price-amount">50</span>
                  <span className="price-period">/month</span>
                </div>
              </div>
              <ul className="pricing-features">
                <li>✓ Premium trading signals</li>
                <li>✓ Unlimited trending coins</li>
                <li>✓ All alert channels</li>
                <li>✓ Advanced risk management</li>
                <li>✓ Airdrop notifications</li>
                <li>✓ VIP community access</li>
                <li>✓ Personal account manager</li>
                <li>✓ Custom strategies</li>
              </ul>
              <button onClick={handleGoVIP} className="btn-outline">Go VIP</button>
            </div>
          </div>
          <div className="pricing-note">
            <p>💳 We accept cryptocurrency payments (BTC, ETH, USDT) • All plans include 7-day free trial</p>
          </div>
        </div>
      </section>

      {/* Partners Section */}
      <section className="partners">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Trusted by Leading Exchanges</h2>
            <p className="section-description">
              We integrate with the most reliable cryptocurrency exchanges and data providers.
            </p>
          </div>
          <div className="partners-grid">
            <div className="partner-item">
              <div className="partner-logo">
                <img src="/logos/binance.svg" alt="Binance" className="partner-logo-img" />
              </div>
              <span>Primary Data Source</span>
            </div>
            <div className="partner-item">
              <div className="partner-logo">
                <img src="/logos/gateio.svg" alt="Gate.io" className="partner-logo-img" />
              </div>
              <span>Cross-Exchange Validation</span>
            </div>
            <div className="partner-item">
              <div className="partner-logo">
                <img src="/logos/coinmarketcap.svg" alt="CoinMarketCap" className="partner-logo-img" />
              </div>
              <span>Market Intelligence</span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <div className="container">
          <div className="cta-content">
            <h2>Ready to Transform Your Trading?</h2>
            <p>Join thousands of successful traders who trust Winu for their crypto trading decisions.</p>
            <div className="cta-actions">
              <button onClick={handleStartFreeTrial} className="btn-primary btn-large">
                <span>Start Free Trial</span>
                <span className="btn-icon">→</span>
              </button>
              <button onClick={handleViewLiveDemo} className="btn-secondary btn-large">
                <span>View Live Demo</span>
              </button>
            </div>
            <div className="cta-guarantee">
              <span className="guarantee-icon">🛡️</span>
              <span>7-day free trial • No credit card required • Cancel anytime</span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer Section */}
      <footer className="footer">
        <div className="container">
          <div className="footer-content">
            <div className="footer-main">
              <div className="footer-brand">
                <div className="footer-logo">
                  <span className="logo-icon">🚀</span>
                  <span className="logo-text">Winu</span>
                </div>
                <p className="footer-description">
                  AI-powered cryptocurrency trading signals and alerts system. 
                  Your money works while you sleep.
                </p>
                <div className="footer-stats">
                  <div className="footer-stat">
                    <span className="stat-icon">⚡</span>
                    <span>94.7% precision signals</span>
                  </div>
                  <div className="footer-stat">
                    <span className="stat-icon">💎</span>
                    <span>1K+ successful traders</span>
                  </div>
                </div>
              </div>

              <div className="footer-links">
                <div className="footer-column">
                  <h4>Product</h4>
                  <ul>
                    <li><button onClick={() => scrollToSection('features')} className="footer-link">Features</button></li>
                    <li><button onClick={() => scrollToSection('pricing')} className="footer-link">Pricing</button></li>
                    <li><button onClick={() => scrollToSection('demo')} className="footer-link">Demo</button></li>
                    <li><button onClick={handleStartFreeTrial} className="footer-link">Free Trial</button></li>
                  </ul>
                </div>

                <div className="footer-column">
                  <h4>Resources</h4>
                  <ul>
                    <li><a href="/dashboard" className="footer-link">Dashboard</a></li>
                    <li><a href="/login" className="footer-link">Login</a></li>
                    <li><a href="/register" className="footer-link">Sign Up</a></li>
                  </ul>
                </div>

                <div className="footer-column">
                  <h4>Connect With Us</h4>
                  <ul>
                    <li>
                      <a href="https://t.me/winuapcom" target="_blank" rel="noopener noreferrer" className="footer-link">
                        <span className="social-icon">📱</span>
                        Telegram Community
                      </a>
                    </li>
                    <li>
                      <a href="https://discord.gg/5dZcxqsM" target="_blank" rel="noopener noreferrer" className="footer-link">
                        <span className="social-icon">💬</span>
                        Discord Server
                      </a>
                    </li>
                    <li>
                      <a href="https://x.com/winuapp" target="_blank" rel="noopener noreferrer" className="footer-link">
                        <span className="social-icon">𝕏</span>
                        Twitter/X
                      </a>
                    </li>
                    <li>
                      <a href="https://www.instagram.com/winuapp" target="_blank" rel="noopener noreferrer" className="footer-link">
                        <span className="social-icon">📸</span>
                        Instagram
                      </a>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="footer-social">
              <div className="social-links">
                <a 
                  href="https://t.me/winuapcom" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="social-link telegram"
                  aria-label="Join us on Telegram"
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                  </svg>
                </a>
                <a 
                  href="https://discord.gg/5dZcxqsM" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="social-link discord"
                  aria-label="Join us on Discord"
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
                  </svg>
                </a>
                <a 
                  href="https://x.com/winuapp" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="social-link twitter"
                  aria-label="Follow us on Twitter/X"
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                  </svg>
                </a>
                <a 
                  href="https://www.instagram.com/winuapp" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="social-link instagram"
                  aria-label="Follow us on Instagram"
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                  </svg>
                </a>
              </div>
            </div>

            <div className="footer-bottom">
              <p className="footer-copyright">
                © {new Date().getFullYear()} Winu. All rights reserved.
              </p>
              <div className="footer-legal">
                <span>Made with ❤️ for crypto traders</span>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}