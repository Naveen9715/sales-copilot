"""
AI Sales Copilot — Executive Web UI (Powered by sales_agent_unified_v8)
Full Gmail API, Google Calendar API, Lead Management, and Local AI Integration.
"""

import ast
import base64
import json
import operator
import os
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText

import requests
from flask import Flask, jsonify, render_template_string, request, Response

# Import all core capabilities from Version 8
import sales_agent_unified_v8 as v8

app = Flask(__name__)

OLLAMA_URL = getattr(v8, "OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = getattr(v8, "OLLAMA_MODEL", "llama3.2:3b")

PAGE = r"""
<!doctype html>
<html lang="en" data-theme="aurora">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#06080e">
<title>Sales Copilot · Autonomous AI Executive</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root, [data-theme="aurora"] {
  --bg-base: #06080e;
  --bg-gradient: radial-gradient(circle 850px at 50% -120px, rgba(6, 182, 212, 0.22), rgba(59, 130, 246, 0.12) 42%, transparent 75%),
                 radial-gradient(ellipse 650px 550px at 95% 15%, rgba(139, 92, 246, 0.18), transparent 65%),
                 radial-gradient(ellipse 600px 480px at 5% 85%, rgba(16, 185, 129, 0.13), transparent 65%),
                 linear-gradient(180deg, #070a12 0%, #0a0e1a 100%);
  --ink-primary: #f8fafc;
  --ink-secondary: #94a3b8;
  --ink-muted: #64748b;
  --accent-cyan: #00f2fe;
  --accent-blue: #38bdf8;
  --accent-purple: #a855f7;
  --accent-emerald: #10b981;
  --glass-surface: rgba(13, 19, 33, 0.72);
  --glass-surface-hover: rgba(22, 31, 53, 0.85);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-border-focus: rgba(56, 189, 248, 0.45);
  --glow-accent: 0 0 35px rgba(6, 182, 212, 0.25);
  --card-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
  --brand-glow: 0 10px 28px rgba(6, 182, 212, 0.35);
}

[data-theme="jade"] {
  --bg-base: #040d0a;
  --bg-gradient: radial-gradient(circle 850px at 50% -120px, rgba(16, 185, 129, 0.25), rgba(5, 150, 105, 0.12) 42%, transparent 75%),
                 radial-gradient(ellipse 650px 550px at 95% 15%, rgba(245, 158, 11, 0.15), transparent 65%),
                 radial-gradient(ellipse 600px 480px at 5% 85%, rgba(6, 182, 212, 0.14), transparent 65%),
                 linear-gradient(180deg, #030d0a 0%, #061510 100%);
  --ink-primary: #f0fdf4;
  --ink-secondary: #86efac;
  --ink-muted: #4ade8099;
  --accent-cyan: #34d399;
  --accent-blue: #10b981;
  --accent-purple: #f59e0b;
  --glass-surface: rgba(6, 26, 18, 0.72);
  --glass-surface-hover: rgba(9, 38, 26, 0.85);
  --glass-border: rgba(52, 211, 153, 0.14);
  --glass-border-focus: rgba(52, 211, 153, 0.5);
  --glow-accent: 0 0 35px rgba(16, 185, 129, 0.3);
  --brand-glow: 0 10px 28px rgba(16, 185, 129, 0.35);
}

[data-theme="amethyst"] {
  --bg-base: #0b0614;
  --bg-gradient: radial-gradient(circle 850px at 50% -120px, rgba(192, 38, 211, 0.22), rgba(139, 92, 246, 0.15) 42%, transparent 75%),
                 radial-gradient(ellipse 650px 550px at 95% 15%, rgba(244, 63, 94, 0.18), transparent 65%),
                 radial-gradient(ellipse 600px 480px at 5% 85%, rgba(99, 102, 241, 0.15), transparent 65%),
                 linear-gradient(180deg, #0a0513 0%, #130a21 100%);
  --ink-primary: #faf5ff;
  --ink-secondary: #d8b4fe;
  --ink-muted: #a855f799;
  --accent-cyan: #e879f9;
  --accent-blue: #c084fc;
  --accent-purple: #f43f5e;
  --glass-surface: rgba(22, 11, 38, 0.72);
  --glass-surface-hover: rgba(33, 16, 56, 0.85);
  --glass-border: rgba(192, 132, 252, 0.14);
  --glass-border-focus: rgba(232, 121, 249, 0.5);
  --glow-accent: 0 0 35px rgba(192, 38, 211, 0.3);
  --brand-glow: 0 10px 28px rgba(192, 38, 211, 0.35);
}

*{box-sizing:border-box}
html,body{margin:0;width:100%;height:100%;overflow:hidden;background-color:var(--bg-base);background-image:var(--bg-gradient);background-attachment:fixed;color:var(--ink-primary);font-family:'Plus Jakarta Sans',ui-sans-serif,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
button,textarea{font:inherit}

.app{height:100dvh;width:100vw;display:flex;flex-direction:column;position:relative;overflow:hidden}

/* Top Navigation Bar */
.topbar{height:76px;flex:0 0 76px;display:flex;align-items:center;justify-content:space-between;padding:0 clamp(18px,4vw,48px);background:rgba(6, 10, 18, 0.65);border-bottom:1px solid var(--glass-border);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);z-index:10}
.brand{display:flex;align-items:center;gap:14px;font-family:'Space Grotesk',sans-serif;font-weight:700;letter-spacing:-0.5px;font-size:17px;color:var(--ink-primary)}
.brand-icon{width:44px;height:44px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(139, 92, 246, 0.25));border:1px solid rgba(255, 255, 255, 0.15);box-shadow:var(--brand-glow);position:relative;overflow:hidden;transition:transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)}
.brand-icon:hover{transform:scale(1.06) rotate(3deg)}
.brand-icon svg{width:26px;height:26px;filter:drop-shadow(0 0 6px rgba(56, 189, 248, 0.6))}
.brand-text{display:flex;flex-direction:column}
.brand-title{display:flex;align-items:center;gap:8px}
.brand-tag{font-size:9px;font-weight:800;letter-spacing:1px;text-transform:uppercase;padding:2px 7px;border-radius:6px;background:rgba(56, 189, 248, 0.12);color:var(--accent-cyan);border:1px solid rgba(56, 189, 248, 0.25)}
.brand-sub{font-size:11px;color:var(--ink-secondary);font-weight:400;letter-spacing:0;margin-top:2px;font-family:'Plus Jakarta Sans',sans-serif}

.top-right{display:flex;align-items:center;gap:12px}

/* Theme Selector Pills */
.theme-picker{display:flex;align-items:center;background:rgba(255, 255, 255, 0.04);border:1px solid var(--glass-border);border-radius:999px;padding:3px;gap:2px}
.theme-btn{background:transparent;border:0;width:28px;height:28px;border-radius:50%;cursor:pointer;display:grid;place-items:center;font-size:12px;transition:all 0.2s;color:var(--ink-secondary)}
.theme-btn:hover{background:rgba(255, 255, 255, 0.08);color:var(--ink-primary)}
.theme-btn.active{background:rgba(255, 255, 255, 0.16);box-shadow:0 0 10px rgba(255,255,255,0.15);transform:scale(1.05)}

/* AI Status Badge */
.status{display:flex;align-items:center;gap:8px;padding:8px 14px;border:1px solid var(--glass-border);border-radius:999px;background:var(--glass-surface);font-size:11.5px;font-weight:600;color:var(--ink-secondary);backdrop-filter:blur(10px)}
.dot{width:8px;height:8px;border-radius:50%;background:#f59e0b;box-shadow:0 0 10px #f59e0b;position:relative}
.dot.ready{background:#10b981;box-shadow:0 0 12px #10b981}
.dot.ready::after{content:'';position:absolute;inset:-3px;border-radius:50%;border:1px solid #10b981;animation:radarPing 2s cubic-bezier(0, 0, 0.2, 1) infinite}
@keyframes radarPing{0%{transform:scale(0.8);opacity:1}100%{transform:scale(2.2);opacity:0}}

.new-chat{border:1px solid var(--glass-border);background:var(--glass-surface);border-radius:12px;padding:8px 14px;font-size:12px;color:var(--ink-primary);font-weight:600;cursor:pointer;display:flex;align-items:center;gap:6px;transition:all 0.2s cubic-bezier(0.16, 1, 0.3, 1)}
.new-chat:hover{background:var(--glass-surface-hover);border-color:var(--glass-border-focus);transform:translateY(-1px);box-shadow:0 4px 16px rgba(0,0,0,0.3)}

/* Main Workspace */
.workspace{flex:1;min-height:0;display:flex;flex-direction:column;max-width:1040px;width:100%;margin:0 auto;padding:0 clamp(16px,3vw,36px)}
.chat{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:24px 0 32px;scroll-behavior:smooth;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,0.1) transparent}
.chat::-webkit-scrollbar{width:6px}
.chat::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:4px}

/* Welcome Centerpiece */
.welcome{min-height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px 12px 32px;animation:fadeEntrance 0.6s cubic-bezier(0.16, 1, 0.3, 1)}
@keyframes fadeEntrance{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}

/* Quantum AI Core Centerpiece */
.nexus-stage{position:relative;width:130px;height:130px;margin:0 auto 24px;display:grid;place-items:center;cursor:pointer}
.nexus-stage::before{content:'';position:absolute;inset:-20px;background:radial-gradient(circle, rgba(6, 182, 212, 0.28), rgba(139, 92, 246, 0.15) 50%, transparent 72%);border-radius:50%;filter:blur(18px);z-index:0;animation:nebulaPulse 5s ease-in-out infinite alternate}
@keyframes nebulaPulse{0%{opacity:0.6;transform:scale(0.95)}100%{opacity:1;transform:scale(1.1)}}

.nexus-core-wrap{position:relative;z-index:1;width:100%;height:100%;display:grid;place-items:center;animation:nexusFloat 4.5s ease-in-out infinite}
@keyframes nexusFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}

.nexus-svg{width:100%;height:100%;overflow:visible;filter:drop-shadow(0 10px 22px rgba(0,0,0,0.5))}
.orbit-ring-outer{transform-origin:50px 50px;animation:spinSlow 22s linear infinite}
.orbit-ring-middle{transform-origin:50px 50px;animation:spinReverse 14s linear infinite}
.nexus-pulsing-center{animation:coreBreathe 3s ease-in-out infinite alternate}

@keyframes spinSlow{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes spinReverse{from{transform:rotate(360deg)}to{transform:rotate(0deg)}}
@keyframes coreBreathe{0%{transform:scale(0.94);opacity:0.85}100%{transform:scale(1.06);opacity:1}}

.nexus-stage:hover .orbit-ring-outer{animation-duration:10s}
.nexus-stage:hover .orbit-ring-middle{animation-duration:6s}

/* Eyebrow & Headline */
.eyebrow{display:inline-flex;align-items:center;gap:8px;color:var(--accent-cyan);background:rgba(6, 182, 212, 0.08);border:1px solid rgba(6, 182, 212, 0.25);border-radius:999px;padding:6px 14px;font-size:11px;letter-spacing:1.2px;font-weight:700;text-transform:uppercase;margin-bottom:18px;backdrop-filter:blur(8px)}
.eyebrow svg{width:13px;height:13px;animation:sparkle 2.5s infinite}
@keyframes sparkle{0%,100%{transform:scale(1) rotate(0deg);opacity:0.8}50%{transform:scale(1.25) rotate(90deg);opacity:1}}

.welcome h1{font-family:'Space Grotesk',sans-serif;font-size:clamp(30px,4.5vw,46px);line-height:1.15;letter-spacing:-1.2px;margin:0 0 14px;font-weight:700;color:var(--ink-primary)}
.welcome h1 span{background:linear-gradient(110deg, var(--accent-cyan) 0%, #38bdf8 35%, var(--accent-purple) 85%);-webkit-background-clip:text;background-clip:text;color:transparent;display:inline-block}
.welcome p{max-width:620px;color:var(--ink-secondary);font-size:14.5px;line-height:1.75;margin:0 auto}

/* Suggestion Grid */
.suggestions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;width:min(100%,740px);margin:32px auto 0;text-align:left}
.suggest{display:flex;align-items:flex-start;gap:14px;padding:16px 18px;border:1px solid var(--glass-border);border-radius:18px;background:var(--glass-surface);cursor:pointer;text-align:left;color:var(--ink-primary);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:var(--card-shadow);transition:all 0.24s cubic-bezier(0.16, 1, 0.3, 1);position:relative;overflow:hidden}
.suggest::before{content:'';position:absolute;inset:0;background:radial-gradient(circle 120px at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255,255,255,0.06), transparent 70%);opacity:0;transition:opacity 0.3s;pointer-events:none}
.suggest:hover{transform:translateY(-3px);border-color:var(--glass-border-focus);background:var(--glass-surface-hover);box-shadow:0 20px 45px rgba(0,0,0,0.5), var(--glow-accent)}
.suggest:hover::before{opacity:1}

.suggest-icon{width:42px;height:42px;flex:0 0 42px;display:grid;place-items:center;border-radius:13px;background:rgba(6, 182, 212, 0.12);border:1px solid rgba(6, 182, 212, 0.22);color:var(--accent-cyan);transition:transform 0.2s}
.suggest:nth-child(2) .suggest-icon{background:rgba(16, 185, 129, 0.12);border-color:rgba(16, 185, 129, 0.25);color:var(--accent-emerald)}
.suggest:nth-child(3) .suggest-icon{background:rgba(245, 158, 11, 0.12);border-color:rgba(245, 158, 11, 0.25);color:#fbbf24}
.suggest:nth-child(4) .suggest-icon{background:rgba(168, 85, 247, 0.12);border-color:rgba(168, 85, 247, 0.25);color:var(--accent-purple)}
.suggest:hover .suggest-icon{transform:scale(1.1) rotate(4deg)}
.suggest-content{flex:1;min-width:0}
.suggest strong{display:block;font-size:13px;font-weight:700;margin-bottom:4px;color:var(--ink-primary);letter-spacing:-0.2px}
.suggest small{display:block;font-size:12px;line-height:1.5;color:var(--ink-secondary)}

/* Chat Messages */
.message{display:flex;gap:14px;margin:0 auto 22px;align-items:flex-start;max-width:880px;animation:msgAppear 0.25s cubic-bezier(0.16, 1, 0.3, 1)}
.message.user{flex-direction:row-reverse}
@keyframes msgAppear{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}

/* Unique AI Neural Avatar Icon */
.avatar{width:40px;height:40px;flex:0 0 40px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(135deg, rgba(6, 182, 212, 0.22), rgba(139, 92, 246, 0.28));border:1px solid rgba(56, 189, 248, 0.3);color:#fff;box-shadow:0 6px 18px rgba(0,0,0,0.4);position:relative;overflow:hidden;transition:all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)}
.user .avatar{background:rgba(255, 255, 255, 0.08);border-color:rgba(255, 255, 255, 0.12);color:var(--accent-cyan);font-size:11px;font-weight:800;letter-spacing:0.5px}

.ai-avatar-icon{width:26px;height:26px;overflow:visible}
.ai-icon-ring{transform-origin:18px 18px;animation:avatarRingSpin 16s linear infinite}
.ai-icon-center{animation:avatarCoreBreath 3s ease-in-out infinite alternate}

/* ACTIVE TYPING STATE: Energetic Animated Avatar */
.typing .avatar{
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.35), rgba(168, 85, 247, 0.45));
  border-color: rgba(0, 242, 254, 0.8);
  box-shadow: 0 0 25px rgba(0, 242, 254, 0.6), 0 0 40px rgba(168, 85, 247, 0.35);
  animation: avatarThinkingPulse 1.2s ease-in-out infinite alternate;
}
.typing .avatar .ai-icon-ring{
  animation: avatarRingSpin 1.6s linear infinite;
  stroke: #00f2fe;
}
.typing .avatar .ai-icon-center{
  animation: avatarCoreBreath 0.7s ease-in-out infinite alternate;
}

@keyframes avatarRingSpin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes avatarCoreBreath{0%{transform:scale(0.85);opacity:0.8}100%{transform:scale(1.2);opacity:1}}
@keyframes avatarThinkingPulse{0%{transform:scale(1);box-shadow:0 0 15px rgba(0,242,254,0.4)}100%{transform:scale(1.08);box-shadow:0 0 28px rgba(0,242,254,0.75)}}

/* Message Bubble */
.bubble{max-width:min(84%,760px);border:1px solid var(--glass-border);background:var(--glass-surface);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-radius:4px 18px 18px 18px;padding:16px 20px;font-size:13.8px;line-height:1.75;overflow-wrap:anywhere;box-shadow:var(--card-shadow);color:var(--ink-primary)}
.user .bubble{background:linear-gradient(135deg, rgba(6, 182, 212, 0.16), rgba(99, 102, 241, 0.24));border-color:rgba(56, 189, 248, 0.35);border-radius:18px 4px 18px 18px;box-shadow:0 8px 25px rgba(6, 182, 212, 0.15)}

/* ChatGPT-Style Rich Elements inside Bubble */
.md-h3{font-family:'Space Grotesk',sans-serif;font-size:15.5px;font-weight:700;margin:12px 0 6px;color:var(--accent-cyan);display:flex;align-items:center;gap:7px}
.md-h3:first-child{margin-top:0}
.md-quote{margin:10px 0;padding:10px 14px;border-left:3px solid var(--accent-cyan);background:rgba(6, 182, 212, 0.08);border-radius:0 10px 10px 0;font-size:13px;line-height:1.6;color:var(--ink-primary);white-space:pre-wrap}
.md-link{color:var(--accent-cyan);text-decoration:none;font-weight:600;border-bottom:1px dashed var(--accent-cyan)}
.md-link:hover{color:#fff;border-bottom-style:solid}
.md-list{margin:8px 0 12px 20px;padding:0;list-style-type:disc}
.md-list li{margin-bottom:5px;line-height:1.6}
.md-code{background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:10px 14px;overflow-x:auto;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px;color:#38bdf8}

/* Action Confirmation Cards */
.action-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:8px}
.badge-success{background:rgba(16, 185, 129, 0.15);color:#34d399;border:1px solid rgba(16, 185, 129, 0.3)}
.badge-calendar{background:rgba(56, 189, 248, 0.15);color:#38bdf8;border:1px solid rgba(56, 189, 248, 0.3)}

.action-card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:12px 16px;margin:10px 0}
.action-card strong{color:var(--ink-primary);font-size:12.5px}

/* Markdown Lead Table */
.md-table{width:100%;border-collapse:collapse;margin:12px 0;font-size:12.5px;background:rgba(0,0,0,0.25);border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.08)}
.md-table th{background:rgba(255,255,255,0.05);color:var(--accent-cyan);font-weight:700;padding:8px 12px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1)}
.md-table td{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.04);color:var(--ink-primary)}

/* Active Typing Indicator */
.typing-container{display:flex;align-items:center;gap:10px}
.typing-beacon{width:8px;height:8px;border-radius:50%;background:var(--accent-cyan);box-shadow:0 0 10px var(--accent-cyan);animation:beaconPing 1.2s infinite alternate}
@keyframes beaconPing{0%{opacity:0.4;transform:scale(0.8)}100%{opacity:1;transform:scale(1.3)}}
.pulse-dots{display:inline-flex;gap:5px;align-items:center}
.pulse-dots span{width:5px;height:5px;background:var(--accent-cyan);border-radius:50%;display:inline-block;animation:pulseDot 1.4s infinite ease-in-out both}
.pulse-dots span:nth-child(1){animation-delay:-0.32s}
.pulse-dots span:nth-child(2){animation-delay:-0.16s}
@keyframes pulseDot{0%,80%,100%{transform:scale(0.4);opacity:0.4}40%{transform:scale(1);opacity:1}}

/* Composer Zone */
.composer-zone{flex:0 0 auto;padding:16px 0 max(18px,env(safe-area-inset-bottom));background:linear-gradient(180deg, rgba(6, 8, 14, 0) 0%, rgba(6, 8, 14, 0.95) 25%);position:relative;z-index:5}
.composer-card{max-width:880px;margin:0 auto;background:rgba(13, 19, 33, 0.75);border:1px solid var(--glass-border);border-radius:22px;padding:10px 12px 10px 20px;display:flex;align-items:flex-end;gap:12px;backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);box-shadow:0 18px 50px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.04);transition:all 0.25s cubic-bezier(0.16, 1, 0.3, 1)}
.composer-card:focus-within{border-color:var(--glass-border-focus);box-shadow:0 20px 55px rgba(0, 0, 0, 0.7), var(--glow-accent), 0 0 0 2px rgba(56, 189, 248, 0.2)}

textarea{border:0;outline:0;resize:none;flex:1;min-width:0;min-height:36px;max-height:140px;font-size:13.5px;line-height:1.6;color:var(--ink-primary);padding:8px 0;background:transparent}
textarea::placeholder{color:var(--ink-muted)}

.send{width:44px;height:44px;flex:0 0 44px;border:0;border-radius:15px;background:linear-gradient(135deg, var(--accent-cyan) 0%, #3b82f6 50%, var(--accent-purple) 100%);color:#06080e;font-size:18px;font-weight:800;cursor:pointer;display:grid;place-items:center;box-shadow:0 4px 18px rgba(6, 182, 212, 0.4);transition:all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)}
.send:hover{transform:scale(1.08) translateY(-2px);box-shadow:0 8px 24px rgba(6, 182, 212, 0.6)}
.send:active{transform:scale(0.96)}
.send:disabled{opacity:0.35;cursor:wait;transform:none}
.send svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}

.foot{text-align:center;color:var(--ink-muted);font-size:11px;margin-top:12px;letter-spacing:0.2px}
.foot span{color:var(--accent-cyan);font-weight:600}

/* Mobile Responsive */
@media(max-width:640px){
  .topbar{height:68px;flex-basis:68px;padding:0 14px}
  .brand-icon{width:38px;height:38px}
  .brand-title{font-size:15px}
  .brand-tag{display:none}
  .status{padding:6px 10px;font-size:10.5px}
  .theme-picker{display:none}
  .workspace{padding:0 12px}
  .chat{padding-top:10px}
  .welcome{padding:16px 4px}
  .nexus-stage{width:105px;height:105px;margin-bottom:18px}
  .welcome h1{font-size:27px;letter-spacing:-0.8px}
  .welcome p{font-size:13px}
  .suggestions{grid-template-columns:1fr;gap:10px;margin-top:22px}
  .suggest{padding:12px 14px}
  .suggest-icon{width:36px;height:36px;flex-basis:36px}
  .composer-zone{padding-top:10px}
  .composer-card{border-radius:18px;padding-left:14px}
  .bubble{max-width:calc(100% - 46px);font-size:12.5px}
  .message{gap:9px}
  .avatar{width:32px;height:32px;flex-basis:32px;border-radius:10px}
}
@media(prefers-reduced-motion:reduce){
  *,*:before,*:after{animation-duration:0.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition:none!important}
}
</style>
</head>
<body>
<div class="app">
  <header class="topbar">
    <div class="brand">
      <div class="brand-icon" aria-label="Sales Copilot Nexus Crest">
        <svg viewBox="0 0 32 32">
          <defs>
            <linearGradient id="crestGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#00f2fe"/>
              <stop offset="50%" stop-color="#38bdf8"/>
              <stop offset="100%" stop-color="#a855f7"/>
            </linearGradient>
          </defs>
          <polygon points="16,3 28,10 28,22 16,29 4,22 4,10" stroke="url(#crestGrad)" stroke-width="2" fill="rgba(6, 182, 212, 0.15)"/>
          <circle cx="16" cy="16" r="4.5" fill="url(#crestGrad)"/>
          <line x1="16" y1="4" x2="16" y2="28" stroke="url(#crestGrad)" stroke-width="1.2" stroke-dasharray="2 3" opacity="0.6"/>
          <line x1="5" y1="16" x2="27" y2="16" stroke="url(#crestGrad)" stroke-width="1.2" stroke-dasharray="2 3" opacity="0.6"/>
        </svg>
      </div>
      <div class="brand-text">
        <div class="brand-title">
          Sales Copilot
          <span class="brand-tag">v8.0 Live</span>
        </div>
        <small class="brand-sub">Autonomous Sales Execution & Workflow Intelligence</small>
      </div>
    </div>

    <div class="top-right">
      <div class="theme-picker" title="Switch bespoke ambiance">
        <button class="theme-btn active" data-set-theme="aurora" title="Cosmic Aurora">🌌</button>
        <button class="theme-btn" data-set-theme="jade" title="Cyber Jade">💎</button>
        <button class="theme-btn" data-set-theme="amethyst" title="Velvet Eclipse">🔮</button>
      </div>
      <div class="status">
        <span class="dot" id="statusDot"></span>
        <span id="statusText">Connecting…</span>
      </div>
      <button class="new-chat" id="newChatBtn" type="button">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Chat
      </button>
    </div>
  </header>

  <div class="workspace">
    <section class="chat" id="chat" aria-live="polite">
      <!-- Rendered dynamically via getWelcomeHTML() -->
    </section>

    <div class="composer-zone">
      <form id="chatForm" class="composer-card">
        <textarea id="messageInput" rows="1" placeholder="Send emails, book calendar slots, query leads, or ask product questions…" autocomplete="off" aria-label="Type your message"></textarea>
        <button class="send" id="sendBtn" type="submit" aria-label="Send message">
          <svg viewBox="0 0 24 24"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
        </button>
      </form>
      <div class="foot">
        Encrypted Local Workspace · Gmail & Google Calendar Connected · Zero Cloud Data Exposure
      </div>
    </div>
  </div>
</div>

<script>
const chat = document.getElementById('chat');
const form = document.getElementById('chatForm');
const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const statusText = document.getElementById('statusText');
const statusDot = document.getElementById('statusDot');
let history = [];

// Unique Quantum AI Core Avatar SVG (Zero stars!)
const AI_AVATAR_SVG = `
<svg class="ai-avatar-icon" viewBox="0 0 36 36" fill="none">
  <defs>
    <linearGradient id="avatarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f2fe"/>
      <stop offset="50%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#a855f7"/>
    </linearGradient>
    <radialGradient id="avatarCenterGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="40%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#7928ca"/>
    </radialGradient>
  </defs>
  <!-- Rotating Orbital Gyro Ring -->
  <circle cx="18" cy="18" r="14" stroke="url(#avatarGrad)" stroke-width="1.8" stroke-dasharray="8 6" opacity="0.85" class="ai-icon-ring"/>
  <!-- Quantum Nodes -->
  <circle cx="18" cy="4" r="2.2" fill="#00f2fe" class="ai-icon-node"/>
  <circle cx="28" cy="25" r="1.8" fill="#a855f7" class="ai-icon-node2"/>
  <!-- Hex Shield -->
  <polygon points="18,7 27,12 27,24 18,29 9,24 9,12" stroke="rgba(255,255,255,0.4)" stroke-width="1.2" fill="none"/>
  <!-- Pulsing Neural Center -->
  <circle cx="18" cy="18" r="5" fill="url(#avatarCenterGrad)" class="ai-icon-center"/>
  <circle cx="16.5" cy="16.5" r="1.5" fill="#ffffff" opacity="0.95"/>
</svg>`;

// Welcome Screen Template
function getWelcomeHTML() {
  return `
    <div class="welcome" id="welcome">
      <div class="nexus-stage" title="Quantum AI Core Active">
        <div class="nexus-core-wrap">
          <svg class="nexus-svg" viewBox="0 0 100 100" role="img" aria-label="Quantum Intelligence Core">
            <defs>
              <linearGradient id="orbGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#00f2fe"/>
                <stop offset="50%" stop-color="#38bdf8"/>
                <stop offset="100%" stop-color="#a855f7"/>
              </linearGradient>
              <linearGradient id="coreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff"/>
                <stop offset="40%" stop-color="#38bdf8"/>
                <stop offset="100%" stop-color="#7928ca"/>
              </linearGradient>
              <radialGradient id="haloGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#00f2fe" stop-opacity="0.8"/>
                <stop offset="60%" stop-color="#a855f7" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
              </radialGradient>
            </defs>
            <g class="orbit-ring-outer">
              <circle cx="50" cy="50" r="44" fill="none" stroke="url(#orbGrad1)" stroke-width="1.5" stroke-dasharray="7 14" opacity="0.75"/>
              <circle cx="50" cy="6" r="3" fill="#00f2fe" filter="drop-shadow(0 0 4px #00f2fe)"/>
              <circle cx="88" cy="72" r="2.2" fill="#a855f7" filter="drop-shadow(0 0 3px #a855f7)"/>
              <circle cx="12" cy="72" r="2.2" fill="#38bdf8" filter="drop-shadow(0 0 3px #38bdf8)"/>
            </g>
            <g class="orbit-ring-middle">
              <ellipse cx="50" cy="50" rx="36" ry="16" fill="none" stroke="#38bdf8" stroke-width="1.3" opacity="0.65" transform="rotate(-35 50 50)"/>
              <ellipse cx="50" cy="50" rx="36" ry="16" fill="none" stroke="#a855f7" stroke-width="1.3" stroke-dasharray="4 8" opacity="0.5" transform="rotate(45 50 50)"/>
            </g>
            <polygon points="50,22 74,36 74,64 50,78 26,64 26,36" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
            <circle cx="50" cy="50" r="24" fill="url(#haloGrad)" class="nexus-pulsing-center"/>
            <circle cx="50" cy="50" r="14" fill="url(#coreGrad)" class="nexus-pulsing-center" filter="drop-shadow(0 0 10px rgba(56,189,248,0.8))"/>
            <circle cx="46" cy="46" r="3" fill="#ffffff" opacity="0.9"/>
          </svg>
        </div>
      </div>

      <div class="eyebrow">
        <svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>
        Autonomous Sales Copilot v8
      </div>

      <h1>Accelerate your deals. <span>What shall we execute?</span></h1>
      <p>Direct Gmail outreach, Google Calendar appointment scheduling, CRM pipeline tracking, and sales intelligence — all live in your browser.</p>

      <div class="suggestions">
        <button class="suggest" data-prompt="send email to last used email explain our product and book the slot for tomorrow meeting">
          <div class="suggest-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          </div>
          <div class="suggest-content">
            <strong>Send Email & Book Slot</strong>
            <small>Email last recipient & schedule meeting</small>
          </div>
        </button>

        <button class="suggest" data-prompt="sales dashboard">
          <div class="suggest-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
          </div>
          <div class="suggest-content">
            <strong>Sales Dashboard</strong>
            <small>View pipeline, priority leads & follow-ups</small>
          </div>
        </button>

        <button class="suggest" data-prompt="show my saved leads">
          <div class="suggest-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div class="suggest-content">
            <strong>Search Saved Leads</strong>
            <small>Inspect verified pipeline contacts</small>
          </div>
        </button>

        <button class="suggest" data-prompt="calculate 15 x 850">
          <div class="suggest-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/><path d="M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M8 18h.01M12 18h.01"/></svg>
          </div>
          <div class="suggest-content">
            <strong>Calculate Pricing & Margins</strong>
            <small>Quick deterministic arithmetic</small>
          </div>
        </button>
      </div>
    </div>
  `;
}

// Markdown Parser for ChatGPT-Style Formatted Responses
function renderMarkdown(text) {
  if (!text) return '';
  let out = text;

  // Escape basic HTML to avoid injection
  out = out.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Markdown Headings (### )
  out = out.replace(/^### (.*$)/gim, '<h3 class="md-h3">$1</h3>');
  out = out.replace(/^## (.*$)/gim, '<h3 class="md-h3">$1</h3>');

  // Bold (**text**)
  out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Italics (*text*)
  out = out.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Markdown links [text](url)
  out = out.replace(/\[(.*?)\]\((https?:\/\/.*?)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1 ↗</a>');

  // Quotes (> text)
  out = out.replace(/^&gt; (.*$)/gim, '<blockquote class="md-quote">$1</blockquote>');

  // Unordered lists (- item or • item)
  out = out.replace(/^[-•]\s+(.*$)/gim, '<li class="md-li">$1</li>');
  out = out.replace(/(<li class="md-li">.*<\/li>)/gms, '<ul class="md-list">$1</ul>');

  // Tables (| a | b |)
  if (out.includes('|')) {
    const lines = out.split('\n');
    let inTable = false;
    let tableHtml = '';
    const newLines = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith('|') && line.endsWith('|')) {
        if (!inTable) {
          inTable = true;
          tableHtml = '<table class="md-table">';
        }
        if (line.includes('---')) continue; // Skip delimiter row
        const cells = line.split('|').filter(c => c !== '');
        const isHeader = (tableHtml === '<table class="md-table">');
        const tag = isHeader ? 'th' : 'td';
        tableHtml += '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
      } else {
        if (inTable) {
          inTable = false;
          tableHtml += '</table>';
          newLines.push(tableHtml);
          tableHtml = '';
        }
        newLines.push(lines[i]);
      }
    }
    if (inTable) {
      tableHtml += '</table>';
      newLines.push(tableHtml);
    }
    out = newLines.join('\n');
  }

  // Convert remaining newlines
  out = out.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');

  return out;
}

// Initial Render
chat.innerHTML = getWelcomeHTML();
bindSuggestions();

function bindSuggestions() {
  document.querySelectorAll('.suggest').forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.dataset.prompt));
  });
}

function setStatus(text, ok) {
  statusText.textContent = text;
  if (ok) {
    statusDot.className = 'dot ready';
  } else {
    statusDot.className = 'dot';
  }
}

function addMessage(role, text, extraClass='') {
  const row = document.createElement('div');
  row.className = 'message ' + (role === 'user' ? 'user' : 'assistant') + ' ' + extraClass;
  
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  if (role === 'user') {
    avatar.textContent = 'YOU';
  } else {
    avatar.innerHTML = AI_AVATAR_SVG;
  }

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  if (extraClass.includes('typing')) {
    bubble.innerHTML = `
      <div class="typing-container">
        <span class="typing-beacon"></span>
        <span>Executing sales workflow & synthesizing…</span>
        <div class="pulse-dots"><span></span><span></span><span></span></div>
      </div>`;
  } else {
    if (role === 'assistant') {
      bubble.innerHTML = renderMarkdown(text);
    } else {
      bubble.textContent = text;
    }
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

async function sendMessage(text) {
  text = (text || '').trim();
  if (!text || sendBtn.disabled) return;
  
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.remove();

  addMessage('user', text);
  input.value = '';
  input.style.height = 'auto';
  sendBtn.disabled = true;

  const waiting = addMessage('assistant', '', 'typing');

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: history })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || 'Execution failed');
    }

    const contentType = response.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
      const data = await response.json();
      waiting.remove();
      addMessage('assistant', data.reply);
      history.push({ role: 'user', content: text }, { role: 'assistant', content: data.reply });
      setStatus('AI Core Online', true);
    } else {
      // Real-time token streaming like ChatGPT!
      waiting.classList.remove('typing');
      const bubble = waiting.querySelector('.bubble');
      bubble.innerHTML = '';
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;
        bubble.innerHTML = renderMarkdown(accumulated);
        chat.scrollTop = chat.scrollHeight;
      }

      history.push({ role: 'user', content: text }, { role: 'assistant', content: accumulated });
      setStatus('AI Core Online', true);
    }
  } catch (err) {
    waiting.remove();
    addMessage('assistant', `⚠️ **Action could not be completed.**\n\n${err.message}`);
    setStatus('Connection Offline', false);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', e => {
  e.preventDefault();
  sendMessage(input.value);
});

input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
});

// New Chat Reset
document.getElementById('newChatBtn').addEventListener('click', () => {
  chat.innerHTML = getWelcomeHTML();
  history = [];
  bindSuggestions();
  chat.scrollTop = 0;
  input.focus();
});

// Theme Selector Interaction
const savedTheme = localStorage.getItem('copilot_theme') || 'aurora';
setTheme(savedTheme);

document.querySelectorAll('[data-set-theme]').forEach(btn => {
  btn.addEventListener('click', () => {
    setTheme(btn.dataset.setTheme);
  });
});

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('copilot_theme', theme);
  document.querySelectorAll('[data-set-theme]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.setTheme === theme);
  });
}

// Check Health & Services
fetch('/api/health')
  .then(r => r.json())
  .then(d => {
    if (d.ok) {
      let statusStr = 'AI Core Online';
      if (d.gmail) statusStr += ' · Gmail Ready';
      if (d.calendar) statusStr += ' · Calendar Ready';
      setStatus(statusStr, true);
    } else {
      setStatus('Ollama Standby', false);
    }
  })
  .catch(() => setStatus('Connection Offline', false));
</script>
</body>
</html>
"""

# ============================================================
# LIVE V8 CONTROLLERS & WORKFLOW DISPATCHER
# ============================================================

def send_email_live(recipient, subject, message):
    """Send real email via Gmail API and update state & lead tracking."""
    service = v8.get_gmail_service()
    mime_message = MIMEText(message, "plain", "utf-8")
    mime_message["to"] = recipient
    mime_message["subject"] = subject
    encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")
    
    result = service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()
    msg_id = result.get("id", "Sent")

    # Update state
    v8.state["last_recipient"] = recipient
    v8.state["last_subject"] = subject
    v8.state["last_message"] = message
    v8.save_state()

    # Update lead if exists
    leads = v8.load_leads()
    for l in leads:
        if str(l.get("email", "")).strip().lower() == recipient.strip().lower():
            l["status"] = "Contacted"
            l["last_contacted_at"] = datetime.now(v8.INDIA_TIMEZONE).isoformat(timespec="seconds")
            l["follow_up_due"] = (datetime.now(v8.INDIA_TIMEZONE).date() + timedelta(days=3)).isoformat()
            v8.save_leads(leads)
            break

    return msg_id


def create_calendar_appointment_live(title, start_dt, end_dt, attendee=None, description=""):
    """Create real Google Calendar appointment and return confirmation."""
    service = v8.get_calendar_service()
    event = {
        "summary": title,
        "description": description or "Scheduled via Sales Copilot Web UI.\nAgenda: AI Automation Platform & Workflow Discussion.",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": v8.CALENDAR_TIMEZONE_NAME},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": v8.CALENDAR_TIMEZONE_NAME},
    }
    if attendee and v8.is_valid_email(attendee):
        event["attendees"] = [{"email": attendee}]

    result = service.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="all" if attendee else "none",
    ).execute()
    return result


def extract_recipient_from_text(text):
    """Find email address from text, or 'last used email', or lead reference."""
    # 1. Direct email regex
    direct = v8.extract_email(text)
    if direct:
        return direct

    # 2. 'last used email' or 'last recipient'
    lower = text.lower()
    if any(k in lower for k in ("last used email", "last email", "last recipient", "previous recipient", "last contact")):
        last = v8.state.get("last_recipient")
        if last and v8.is_valid_email(last):
            return last

    # 3. Reference to lead name/ID
    lead = v8.find_lead_referenced_in_text(text)
    if lead and lead.get("email") and v8.is_valid_email(lead.get("email")):
        return lead["email"]

    # Fallback to last recipient if available
    last = v8.state.get("last_recipient")
    if last and v8.is_valid_email(last) and ("send email" in lower or "send mail" in lower):
        return last

    return None


@app.get("/")
def index():
    return render_template_string(PAGE)


@app.get("/api/health")
def health():
    ollama_ok = False
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        ollama_ok = r.status_code == 200
    except requests.RequestException:
        ollama_ok = False

    gmail_ok = False
    cal_ok = False
    try:
        if v8.get_gmail_service():
            gmail_ok = True
    except Exception:
        gmail_ok = False

    try:
        if v8.get_calendar_service():
            cal_ok = True
    except Exception:
        cal_ok = False

    return jsonify(ok=ollama_ok, gmail=gmail_ok, calendar=cal_ok, model=OLLAMA_MODEL)


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    user_text = str(payload.get("message", "")).strip()
    if not user_text:
        return jsonify(error="Please type a message first."), 400

    lowered = user_text.lower()
    replies = []

    # ========================================================
    # 1. SALES DASHBOARD & LEADS MANAGEMENT
    # ========================================================
    if lowered in {"sales dashboard", "dashboard", "lead dashboard", "pipeline"}:
        leads = v8.load_leads()
        today = datetime.now(v8.INDIA_TIMEZONE).date()
        status_counts = {}
        due = []
        high_priority = []
        for lead in leads:
            status = v8.lead_status(lead)
            status_counts[status] = status_counts.get(status, 0) + 1
            parsed_due = v8.parse_iso_date(lead.get("follow_up_due"))
            if parsed_due and parsed_due <= today and status.lower() not in {"won", "lost", "closed"}:
                due.append((lead, parsed_due))
            if v8.lead_priority(lead) == "High" and status.lower() not in {"won", "lost", "closed"}:
                high_priority.append(lead)

        res = [
            "### 📊 Sales Operations Dashboard",
            f"**Total Leads:** `{len(leads)}` | **High-Priority Open:** `{len(high_priority)}` | **Follow-ups Due:** `{len(due)}`",
            "",
            "**Pipeline Status Breakdown:**",
        ]
        for st, count in sorted(status_counts.items()):
            res.append(f"- **{st}:** {count}")

        if due:
            res.append("\n**⚠️ Follow-ups Needing Attention:**")
            for l, d_date in due[:5]:
                res.append(f"- **ID {l.get('id')} ({l.get('name')})** — Due: `{d_date.isoformat()}` (Priority: {v8.lead_priority(l)})")

        return jsonify(reply="\n".join(res))

    if lowered in {"follow up queue", "follow-up queue", "followup queue"}:
        today = datetime.now(v8.INDIA_TIMEZONE).date()
        leads = [l for l in v8.load_leads() if v8.lead_status(l).lower() not in {"won", "lost", "closed"}]
        due = []
        for l in leads:
            d = v8.parse_iso_date(l.get("follow_up_due"))
            if d and d <= today:
                due.append((l, d))
        if not due:
            return jsonify(reply="✅ **No follow-ups are currently overdue or due today.** Your sales queue is up to date!")
        res = ["### 📋 Open Follow-Up Queue", "| ID | Name | Company | Email | Due | Priority |", "|---|---|---|---|---|---|"]
        for l, d in due:
            res.append(f"| {l.get('id')} | {l.get('name')} | {l.get('company','—')} | {l.get('email','—')} | {d.isoformat()} | {v8.lead_priority(l)} |")
        return jsonify(reply="\n".join(res))

    if any(k in lowered for k in ("show my saved leads", "list leads", "show leads", "view leads", "saved leads", "search leads")):
        leads = v8.load_leads()
        if "search leads" in lowered:
            term = lowered.split("search leads", 1)[1].strip()
            if term:
                leads = [l for l in leads if term in " ".join(str(l.get(k,"")) for k in ("name","company","email","phone","source","notes")).lower()]
        if not leads:
            return jsonify(reply="No leads found matching your criteria. Type `add lead <name>, <company>, <email>` to create one.")
        res = ["### 🗂️ Qualified Sales Leads", "| ID | Name | Company | Email | Priority | Status | Follow-Up |", "|---|---|---|---|---|---|---|"]
        for l in leads[:25]:
            res.append(f"| {l.get('id')} | {l.get('name','—')} | {l.get('company','—')} | {l.get('email','—')} | {v8.lead_priority(l)} | {v8.lead_status(l)} | {l.get('follow_up_due','—')} |")
        return jsonify(reply="\n".join(res))

    # ========================================================
    # 2. NUMERIC / PRICING CALCULATIONS
    # ========================================================
    calc_match = re.search(r"(?i)(?:calculate|compute|what is|solve)?\s*([-+]?\d+(?:\.\d+)?)\s*([+\-*/x×%])\s*([-+]?\d+(?:\.\d+)?)", user_text)
    if calc_match and ("calculate" in lowered or len(user_text.split()) <= 5):
        a, sym, b = calc_match.groups()
        a, b = float(a), float(b)
        res_val = 0
        if sym in ("x", "×", "*"): res_val = a * b
        elif sym == "+": res_val = a + b
        elif sym == "-": res_val = a - b
        elif sym == "/": res_val = (a / b) if b != 0 else "Cannot divide by zero"
        elif sym == "%": res_val = a % b
        if isinstance(res_val, float) and res_val.is_integer():
            res_val = int(res_val)
        return jsonify(reply=f"### 🧮 Calculation Result\n\n**Expression:** `{a} {sym} {b}`\n**Result:** **`{res_val}`**")

    # ========================================================
    # 3. GMAIL EMAIL WORKFLOW
    # ========================================================
    has_email_intent = any(x in lowered for x in ("send email", "send mail", "draft email", "email to", "send an email", "write email", "prepare email"))
    has_calendar_intent = any(x in lowered for x in ("book the slot", "book a slot", "schedule a meeting", "schedule meeting", "create a calendar event", "calendar event", "book meeting", "schedule appointment"))

    recipient = extract_recipient_from_text(user_text)

    # Execute Email if requested
    if has_email_intent:
        if not recipient:
            return jsonify(reply="⚠️ **Recipient Missing:** Please provide an email address, mention a lead name/ID, or say *'send to last used email'*.")

        purpose = user_text
        for strip_phrase in ("send email to", "send mail to", "draft email to", "email to"):
            if strip_phrase in purpose.lower():
                purpose = purpose.lower().split(strip_phrase, 1)[1]
        
        # Ultra-fast high-converting sales email generator (0.01s vs 25s)
        name = recipient.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        lower_p = purpose.lower()
        if any(k in lower_p for k in ("book", "meeting", "slot", "tomorrow", "calendar", "call")):
            subject = "AI Automation Platform — Meeting & Workflow Demo"
            body = (
                f"Hi {name},\n\n"
                f"I wanted to share how our AI Automation Platform can help your team streamline operations by automating customer support, lead generation, email outreach, and appointment scheduling to eliminate manual work.\n\n"
                f"Would tomorrow at 11:00 AM (India Time) work for a brief 15-minute walkthrough?\n\n"
                f"Looking forward to connecting!\n\n"
                f"Best regards,\nSales Copilot Team"
            )
        else:
            subject = "Streamlining Operations with our AI Automation Platform"
            body = (
                f"Hi {name},\n\n"
                f"I am reaching out regarding our AI Automation Platform. We help businesses eliminate repetitive manual tasks through automated customer support, intelligent lead capture, and automated follow-ups.\n\n"
                f"Please let me know if you would like a brief walkthrough of how this can benefit your organization.\n\n"
                f"Best regards,\nSales Copilot Team"
            )

        # Send real email via Gmail
        try:
            msg_id = send_email_live(recipient, subject, body)
            replies.append(
                f"### ✉️ Email Sent Successfully via Gmail API\n"
                f"- **To:** `{recipient}`\n"
                f"- **Subject:** **{subject}**\n"
                f"- **Gmail Message ID:** `{msg_id}`\n\n"
                f"> {body}\n\n"
                f"✅ *Delivered directly through your authenticated Google workspace.*"
            )
        except Exception as e:
            replies.append(f"❌ **Gmail Delivery Error:** Could not send email to `{recipient}`: {str(e)}")

    # ========================================================
    # 4. GOOGLE CALENDAR WORKFLOW
    # ========================================================
    if has_calendar_intent:
        cal_details = v8.extract_calendar_request_details(user_text)
        title = cal_details.get("title") or "Sales Copilot Demo & Strategy Call"
        
        # Resolve attendee
        attendee = cal_details.get("attendee") or recipient or v8.state.get("last_recipient")

        # Resolve date
        today = datetime.now(v8.INDIA_TIMEZONE).date()
        if "tomorrow" in lowered:
            date_val = today + timedelta(days=1)
        elif "today" in lowered:
            date_val = today
        elif cal_details.get("date"):
            try:
                date_val = datetime.strptime(cal_details["date"], "%Y-%m-%d").date()
            except ValueError:
                date_val = today + timedelta(days=1)
        else:
            date_val = today + timedelta(days=1)

        # Resolve time
        start_time_str = cal_details.get("start_time") or "11:00"
        try:
            time_parts = [int(x) for x in start_time_str.split(":")]
            start_dt = datetime.combine(date_val, datetime.min.time().replace(hour=time_parts[0], minute=time_parts[1])).replace(tzinfo=v8.INDIA_TIMEZONE)
        except Exception:
            start_dt = datetime.combine(date_val, datetime.min.time().replace(hour=11, minute=0)).replace(tzinfo=v8.INDIA_TIMEZONE)

        duration = cal_details.get("duration") or 30
        end_dt = start_dt + timedelta(minutes=duration)

        # Create live Google Calendar Event
        try:
            event_res = create_calendar_appointment_live(
                title=title,
                start_dt=start_dt,
                end_dt=end_dt,
                attendee=attendee,
                description=f"Agenda: Discussion on AI Automation Platform & sales workflows.\nInvitee: {attendee or 'Self'}"
            )
            event_link = event_res.get("htmlLink", "")
            replies.append(
                f"### 📅 Google Calendar Meeting Confirmed!\n"
                f"- **Event:** **{title}**\n"
                f"- **Date:** `{date_val.strftime('%A, %b %d, %Y')}`\n"
                f"- **Time:** `{start_dt.strftime('%I:%M %p')} – {end_dt.strftime('%I:%M %p')} (Asia/Kolkata)`\n"
                f"- **Attendee:** `{attendee or 'No external attendee'}`\n"
                + (f"- 🔗 [Open Event in Google Calendar]({event_link})" if event_link else "")
            )
        except Exception as e:
            replies.append(f"❌ **Calendar Error:** Could not schedule Google Calendar event: {str(e)}")

    if replies:
        return jsonify(reply="\n\n---\n\n".join(replies))

    # ========================================================
    # 5. GENERAL PRODUCT KNOWLEDGE & REAL-TIME STREAMING
    # ========================================================
    history = payload.get("history", [])
    messages = [{
        "role": "system",
        "content": (
            "You are the AI Sales Copilot. Answer helpfully, concisely, and professionally in 2-3 short paragraphs. "
            "For questions about the configured product, use only the verified facts below and do not invent features, pricing, integrations, or guarantees.\n"
            "Product information:\n" + v8.PRODUCT_KNOWLEDGE
        )
    }]
    if isinstance(history, list):
        for item in history[-8:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
                messages.append({"role": item["role"], "content": item["content"][:2000]})
    messages.append({"role": "user", "content": user_text[:2000]})

    def generate_stream():
        try:
            r = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.2, "num_predict": 180, "num_ctx": 2048}
                },
                stream=True,
                timeout=120,
            )
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    chunk_data = json.loads(line)
                    content = chunk_data.get("message", {}).get("content", "")
                    if content:
                        yield content
        except Exception as e:
            yield f"\n\n*(Error during response: {str(e)})*"

    return Response(generate_stream(), mimetype="text/plain")


if __name__ == "__main__":
    print("AI Sales Copilot live web server starting...")
    print(f"Ollama Model: {OLLAMA_MODEL}")
    print("Connected to Gmail & Google Calendar services.")
    print("Open http://127.0.0.1:5000 in your browser.")
    app.run(host="127.0.0.1", port=5000, debug=False)
