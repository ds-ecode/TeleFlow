<div align="center">

# ⚡ TeleFlow ⚡
### *Resilient, Zero-Cost Automated Media Pipeline for Telegram*

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Asyncio](https://img.shields.io/badge/Async-Telethon-orange.svg)](https://docs.telethon.dev/)
[![Cloud Ready](https://img.shields.io/badge/Cloud-Kaggle%20Compatible-success.svg)](https://www.kaggle.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 🚀 Overview
**TeleFlow** is a fault-tolerant, asynchronous Python pipeline designed to ingest, normalize, rename, and re-upload large-scale media libraries across Telegram group chats. Optimized for unattended cloud execution (such as Kaggle background commits), it features built-in anti-ban throttling, session management via `StringSession`, and intelligent state persistence.

---

## 📊 Core Architecture Flow
```text
[ Telegram Group ] 
       │ (Async Iteration)
       ▼
[ Kaggle Cloud Engine ] ──(State Check)──> [ processed_ids.txt ]
       │
       ├─> [ Robust Chunked Download ] (With 25m Timeout & Auto-Reconnect)
       ├─> [ Normalization ] (.mp4 enforcement)
       └─> [ Paced Re-Upload ] (Random 8s-15s Human Cooldowns)
```

✨ Key Features


Stateless Cloud Auth: Utilizes Telethon's StringSession to run securely in headless environments without interactive terminal prompts.

Zero-Duplication Ledger: Maintains an automated state log (processed_ids.txt) to seamlessly resume where it left off across execution cycles.

Network Resilience: Structured multi-attempt retry wrappers with automated socket tear-down to survive large file stalls near completion.

Anti-Ban Guardrails: Randomized human pacing intervals and native FloodWaitError penalty handling.

📦 Quick Setup Guide


Clone or Download this repository.

Install Dependencies:


Bash

<code>pip install telethon nest_asyncio</code>

```
Create a config.py file in your root folder (this is ignored by Git to protect your keys):
```

```
Python

API_ID = your_api_id
API_HASH = "your_api_hash"
GROUP_TARGET = -1002223726175
STRING_SESSION = "your_generated_string_session"
Run the Pipeline:

```
Bash


<code>python main.py</code>
