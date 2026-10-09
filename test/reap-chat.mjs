// Terminal chatbot that drives Reap's Agentic flow end to end in the sandbox:
// search -> details -> quote -> (enroll card) -> checkout -> approval -> order.
// Run: node --env-file=.env test/reap-chat.mjs
import { randomUUID } from "node:crypto";
import { exec } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { createInterface } from "node:readline/promises";

const BASE = process.env.REAP_BASE_URL || "https://sandbox.api.reap.global";
const VERSION = process.env.REAP_VERSION || "2025-02-14";
const KEY = process.env.REAP_API_KEY;
const CUSTOMER_ID = process.env.REAP_CUSTOMER_ID || "greap-test-user";
const EMAIL = process.env.REAP_EMAIL || "test@example.com";
const RETURN_URL = "https://example.com/done"; // Reap requires HTTPS; we poll instead of waiting for the redirect
// Mock address for sandbox quotes; required whenever an item ships.
const SHIPPING_ADDRESS = {
  firstName: "Test",
  lastName: "User",
  phone: "+14155550123",
  addressLine1: "1 Market Street",
  city: "San Francisco",
  region: "CA",
  postalCode: "94105",
  country: "US",
};
const ENROLLMENT_FILE = new URL("./.enrollment.json", import.meta.url);

if (!KEY) {
  console.error("REAP_API_KEY is missing. Run with: node --env-file=.env test/reap-chat.mjs");
  process.exit(1);
}

async function reap(method, path, body, extraHeaders = {}) {
  const headers = {
    Authorization: `Bearer ${KEY}`,
    "Reap-Version": VERSION,
    ...extraHeaders,
  };
  if (body) {
    headers["Content-Type"] = "application/json";
    if (method === "POST") headers["Idempotency-Key"] = randomUUID();
  }
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    throw new Error(`${method} ${path} -> ${res.status}\n${JSON.stringify(data, null, 2)}`);
  }
  return data;
}

const money = (m) => (m ? `${m.amount} ${m.currency}` : "n/a");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const openBrowser = (url) => exec(`open "${url}"`); // macOS

const rl = createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => rl.question(q);

async function ensureEnrollment() {
  let id = process.env.REAP_ENROLLMENT_ID;
  if (!id && existsSync(ENROLLMENT_FILE)) {
    id = JSON.parse(readFileSync(ENROLLMENT_FILE, "utf8")).id;
  }
  if (id) {
    const e = await reap("GET", `/agentic/enrollments/${id}`);
    if (e.status === "ACTIVE") return id;
    console.log(`Saved enrollment ${id} is ${e.status}, creating a new one.`);
  }

  const e = await reap("POST", "/agentic/enrollments", {
    source: "EXTERNAL",
    owner: { type: "CLIENT_REFERENCE", id: CUSTOMER_ID, email: EMAIL },
    presentation: { type: "REDIRECT", returnUrl: RETURN_URL },
  });
  writeFileSync(ENROLLMENT_FILE, JSON.stringify({ id: e.id }));

  console.log("\nCard entry needed. Opening Reap's hosted page (card details never touch this script):");
  console.log(e.nextAction.url);
  console.log("Use the card from your .env (or a sandbox test card). OTP is 456789.");
  openBrowser(e.nextAction.url);

  for (let i = 0; i < 90; i++) {
    await sleep(2000);
    const cur = await reap("GET", `/agentic/enrollments/${e.id}`);
    if (cur.status === "ACTIVE") {
      console.log("Card enrolled.\n");
      return e.id;
    }
    if (["FAILED", "REVOKED", "EXPIRED"].includes(cur.status)) {
      throw new Error(`Enrollment ended as ${cur.status}`);
    }
  }
  throw new Error("Timed out waiting for card enrollment.");
}

async function pick(prompt, max) {
  while (true) {
    const a = (await ask(prompt)).trim().toLowerCase();
    if (a === "q") return null;
    const n = Number(a);
    if (Number.isInteger(n) && n >= 1 && n <= max) return n - 1;
    console.log(`Enter a number 1-${max}, or q to cancel.`);
  }
}

async function buy(product) {
  const { products } = await reap("POST", "/agentic/products/details", { productIds: [product.id] });
  const detail = products?.[0];
  const variant = detail?.defaultVariant ?? product.previewVariant;
  if (!variant?.available) {
    console.log("That product has no available variant.");
    return;
  }
  if (detail?.options?.length) {
    const opts = detail.options.map((o) => `${o.name}: ${o.values.map((v) => v.label).join("/")}`);
    console.log(`Options exist (${opts.join("; ")}) but this test uses the default variant.`);
  }

  const qtyRaw = (await ask(`Quantity for "${product.name}" at ${money(variant.price)} [1]: `)).trim();
  const quantity = Number(qtyRaw || 1);
  if (!Number.isInteger(quantity) || quantity < 1) return console.log("Invalid quantity.");

  let quote = await reap("POST", "/agentic/quotes", {
    items: [{ variantId: variant.id, quantity }],
    email: EMAIL,
    ...(variant.requiresShipping !== false ? { shippingAddress: SHIPPING_ADDRESS } : {}),
  });

  if (quote.shippingOptions?.length > 1) {
    console.log("\nShipping options:");
    quote.shippingOptions.forEach((s, i) =>
      console.log(`  ${i + 1}. ${s.name} - ${money(s.price)}${s.selected ? " (selected)" : ""}`),
    );
    const i = await pick("Choose shipping (q to cancel): ", quote.shippingOptions.length);
    if (i === null) return;
    quote = await reap("POST", `/agentic/quotes/${quote.id}/shipping-option`, {
      shippingOptionId: quote.shippingOptions[i].id,
    });
  }

  const b = quote.amountBreakdown;
  console.log("\nQuote:");
  console.log(`  Items:    ${money(b.itemsSubtotal)}`);
  console.log(`  Shipping: ${money(b.shipping)}`);
  console.log(`  Tax:      ${money(b.tax?.amount)}`);
  console.log(`  TOTAL:    ${money(b.finalAmount)}  (expires ${quote.expiresAt})`);

  if ((await ask("Approve this purchase? (yes/no): ")).trim().toLowerCase() !== "yes") {
    console.log("Cancelled, nothing was charged.");
    return;
  }

  const enrollmentId = await ensureEnrollment();
  const checkout = await reap(
    "POST",
    "/agentic/checkouts",
    {
      quoteId: quote.id,
      enrollmentId,
      presentation: { type: "REDIRECT", returnUrl: RETURN_URL },
    },
    { "X-Simulate-Checkout": "COMPLETED" },
  );

  if (checkout.nextAction?.url) {
    console.log("\nApproval needed on Reap's hosted page:");
    console.log(checkout.nextAction.url);
    openBrowser(checkout.nextAction.url);
  }

  for (let i = 0; i < 90; i++) {
    const c = await reap("GET", `/agentic/checkouts/${checkout.id}`);
    if (c.status !== "REQUIRES_ACTION") {
      console.log(`\nCheckout ${c.status}`);
      console.log(JSON.stringify(c, null, 2));
      return;
    }
    await sleep(2000);
  }
  console.log("Timed out waiting for approval.");
}

async function main() {
  console.log(`Reap Agentic test chatbot (${BASE}, version ${VERSION})`);
  console.log('Describe what you want, e.g. "wireless headphones under 200". Type "exit" to quit.\n');

  while (true) {
    const query = (await ask("you> ")).trim();
    if (!query) continue;
    if (query === "exit") break;

    try {
      const maxMatch = query.match(/under\s+\$?(\d+(?:\.\d+)?)/i);
      const search = await reap("POST", "/agentic/products/search", {
        query,
        context: { country: process.env.REAP_COUNTRY || "US", currency: process.env.REAP_CURRENCY || "USD" },
        filters: {
          availability: "AVAILABLE_ONLY",
          ...(maxMatch ? { price: { max: maxMatch[1] } } : {}),
        },
        pagination: { limit: 10 },
      });

      if (!search.products?.length) {
        console.log("bot> No available products found. Try a different query.\n");
        continue;
      }
      if (search.warnings?.length) console.log("warnings:", search.warnings);

      console.log(`bot> Found ${search.products.length} product(s):`);
      search.products.forEach((p, i) => {
        const r = p.priceRange;
        const price = r ? `${money(r.min)}${r.max && r.max.amount !== r.min.amount ? ` - ${money(r.max)}` : ""}` : "n/a";
        console.log(`  ${i + 1}. ${p.name} | ${p.merchant?.name ?? "unknown merchant"} | ${price}`);
      });

      const i = await pick("Pick one to buy (q to skip): ", search.products.length);
      if (i !== null) await buy(search.products[i]);
      console.log();
    } catch (err) {
      console.error(`bot> Error: ${err.message}\n`);
    }
  }
  rl.close();
}

main();
