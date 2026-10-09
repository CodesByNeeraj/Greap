# Greap

Greap is a project for the **Reap × 65labs Agentic Buildathon**. Its goal is to turn the event brief into a working, useful agentic payments demo.

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
