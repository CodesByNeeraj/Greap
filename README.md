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

The bot only replies while this process is running. To test without Telegram:

```
.venv/bin/python -m greap.cli_chat
```

In the terminal chat, `/as <id>` switches user, `/advance <hours>` skips time (useful for 5-day deadlines), `/tick` runs the deadline checks and `/pay` pays.

### Real checkout needs a card, once

Reap checkout needs an enrolled card, and enrollment can only be completed on Reap's hosted page. Run this once, open the link it prints, enter the sandbox card and use OTP `456789`:

```
.venv/bin/python -m greap.enroll_card
```

The enrollment is saved to `data/reap-enrollment.json` and reused for every order. Without a card, use `GREAP_DRY_RUN=1` to test the whole journey.

### Demo helper

To show the happy flow live, fill an open queue as if other shoppers had joined and paid. Stop the bot first, then restart it afterwards:

```
.venv/bin/python -m greap.simulate_fill "Box of 6 Mixed Cookies"
```

## Tests and code quality

```
.venv/bin/python -m pytest
.venv/bin/black greap tests
.venv/bin/flake8 greap tests
```

The tests cover queue joining and overflow, locking, the sad flow, unpaid expiry and the exact-amount payment rule. See `AGENTS.md` for the coding conventions.

## Known limitations

- **Card enrollment is manual.** Reap's hosted page is the only way to enroll a card, and the sandbox has no shortcut.
- **Shipping and tax are not charged to users.** Users pay the unit price only. Reap's quote adds shipping and tax on top of the carton price.
- **Rounding.** Unit prices are rounded to cents, so a queue's payments can differ from the carton price by a few cents.
- **Shipping address.** Each carton ships to the first user who joined its queue.
- **Spending limits.** Reap's mandates are not live in the sandbox, so approval and limits are enforced in Greap, not by Reap.
- **Search cap.** Search shows every sellable result up to 50 products.
- **Single process.** State is a JSON file held in memory by one running process. Do not edit it while the bot runs.
- **Bulk sizes come from an LLM** reading product names, so a misread name can misclassify a product.

## Hackathon brief

Build an experience where an AI agent can help someone discover a product, check pricing, and complete a checkout with the person's permission and spending limits. The agent's reasoning and user experience are up to the team; the payment flow must use one of the supported Reap paths below.

### Required payment path and boundaries

- Use Reap's Agentic module, Payward's Kwal wallet with Agentic, or both.
- Build and test in the sandbox. Checkout is simulated: purchases and deliveries are not real.
- Use test assets when funding Kwal. Kwal uses a user-owned, non-custodial wallet and a funded vault in its card payment flow.
- Do not bypass Agentic by scraping checkout or provide raw card details to an AI model.
- Check that the intended merchant and market are supported. Travel booking and restricted categories, including gambling and adult content, are out of scope.

### Suggested problem areas

The brief suggests business spending, everyday purchases, commerce inside chats or apps, and stablecoin payments or agent economies. These are starting points; judging focuses on the value of the problem and the bridge between onchain systems and real-world spending.

## Event requirements

- **Team size:** 2–4 people. Register once per team by **4:30 pm SGT** to receive Reap sandbox access; arrivals after 4:30 pm cannot participate.
- **Submission:** Due **9:00 pm SGT sharp** on Friday, 9 October. The organizers provide the portal and instructions at the event.
- **Schedule:** Event runs 3:00–10:00 pm SGT at SQ Collective, 65 Mohamed Sultan Rd, Singapore. Dinner is at 7:00 pm; optional demos run 9:00–10:00 pm.
- **Prizes:** Two tracks, each with $500 cash and $500 in credits: *Most Worthwhile Problem* and *Best Bridge Between Onchain and Real World*.

## Build direction

Greap should demonstrate a complete, understandable user journey: the person states a goal, the agent finds an eligible product, explains the price, requests approval within a clear budget, and completes the sandbox checkout through the supported payment integration. Keep consent and spending limits visible, and make failures or unavailable merchants clear to the user.

## References

- [Hackathon participant guide](https://reap-hackathon-microsite.vercel.app/)
- [Reap Agentic Payments documentation](https://docs.reap.global/agentic-payments/overview)
- [Reap API documentation](https://docs.reap.global/)
- [Kwal agent skill](https://github.com/payward/kwal-skill)
- [Reap supported merchant sheet](https://docs.google.com/spreadsheets/d/1pqb1Jlx1sycembPcjMZ4dxhwzVWXfK7k8RtfNMhb_cs/edit?usp=sharing)

The site describes the event held on Friday, 9 October; confirm current dates, deadlines, prize fulfilment details, merchant availability, and access instructions with the organizers before relying on them.
