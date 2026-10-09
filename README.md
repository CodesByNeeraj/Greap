# Greap

Greap is a Telegram shopping agent that helps people save money by buying in bulk together. It was built for the **Reap × 65labs Agentic Buildathon** and pays through Reap's Agentic module in the sandbox.

Suppliers on Reap sell in bulk units that differ by product: a carton of 24, a box, a bag. Greap lets several people join a shared queue for one bulk unit and pay only for the units they need. When the queue fills a carton, the carton is bought and split.

## How it works

1. **Onboarding.** A new user gets a welcome message, then the agent asks for their name and shipping address, one question at a time.
2. **Search.** The user says what they want. Greap searches Reap's merchant catalog and lists every sellable result. An LLM reads each product name and works out its bulk unit and units per bulk unit, since Reap has no MOQ field. Items with no bulk size are shown as direct purchase only.
3. **Join a queue or buy a carton.** The user either joins the product's queue with a number of units, or buys whole cartons directly. The unit price is the carton price divided by the carton size. The agent shows the product, units, unit price, total and deadline, and only saves the entry after a clear yes. No payment is taken at this point.
4. **Queue filling.** Each product has one open queue at a time. If a join overfills the carton, the extra units start the next carton's queue. A queue waits up to 5 days from its first entry.
5. **Happy flow.** When a queue fills, it locks and every user is told what they owe. Users pay with `/pay` by typing the exact amount due. Unpaid entries are cancelled after 24 hours and the queue reopens. Once every entry in a queue is paid, Greap quotes and orders the carton from Reap.
6. **Sad flow.** If a queue is still short at its deadline, each user can buy the remaining units, extend 5 more days, or cancel.

## Architecture

| Part | Role |
|---|---|
| Greap Agent | The conversation. An LLM with tool calling (search, join, buy, status, cancel and so on). |
| Orchestrator | Receives confirmed payments, moves paid items into history, and triggers the order once a queue is fully paid. |
| Procurement | Searches Reap, classifies bulk units, and places orders through Reap's quote and checkout endpoints. |
| Context store | One JSON file holding users, queues, entries and cached classifications. Per-user `cart.md` and `history.md` views are written beside it. |

Code lives in `greap/`. Entry points are `telegram_bot.py` (the real channel), `cli_chat.py` (a terminal chat for testing) and `enroll_card.py` (one-time card setup).

## Setup

You need Python 3.10 or newer (tested on 3.14), a Reap sandbox API key, an OpenAI API key and a Telegram bot token.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

| Variable | Needed | Purpose |
|---|---|---|
| `REAP_API_KEY` | yes | Reap sandbox key |
| `OPEN_API_KEY` | yes | OpenAI key used by the agent and the classifier |
| `TELEGRAM_BOT_TOKEN` | for Telegram | Create a bot with @BotFather and paste its token |
| `GREAP_OPS_TELEGRAM_ID` | optional | Your Telegram user id. Reap card-entry and approval links and order failures go to this chat. Without it they print in the terminal. |
| `GREAP_DRY_RUN` | optional | Set to `1` to take a real Reap quote but skip the card and the charge |
| `GREAP_MODEL` | optional | OpenAI model, default `gpt-5.4-mini` |
| `REAP_COUNTRY`, `REAP_CURRENCY` | optional | Catalog market, default `SG` and `SGD` |
| `GREAP_ORDER_EMAIL`, `GREAP_DEFAULT_PHONE` | optional | Contact details sent with sandbox orders |
| `GREAP_DATA_DIR` | optional | Where data is stored, default `data/` |

`CARD_NUMBER`, `EXPIRY` and `CVV` in `.env.example` are Reap's public sandbox test card. The code never reads them. Reap's API has no way to accept card details, so they are only typed into Reap's hosted card page.

## Run

```
.venv/bin/python -m greap.telegram_bot
```

### Real checkout needs a card, once

Reap checkout needs an enrolled card, and enrollment can only be completed on Reap's hosted page. Run this once, open the link it prints, enter the sandbox card and use OTP `456789`:

```
.venv/bin/python -m greap.enroll_card
```

The enrollment is saved to `data/reap-enrollment.json` and reused for every order. Without a card, use `GREAP_DRY_RUN=1` to test the whole journey.

## Tests and code quality

```
.venv/bin/python -m pytest
.venv/bin/black greap tests
.venv/bin/flake8 greap tests
```

The tests cover queue joining and overflow, locking, the sad flow, unpaid expiry and the exact-amount payment rule. See `AGENTS.md` for the coding conventions.
