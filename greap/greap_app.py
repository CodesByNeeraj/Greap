"""Wires every part together and routes each incoming message."""

from openai import AsyncOpenAI

from greap.bulk_classifier import BulkClassifier
from greap.clock import Clock
from greap.config import Settings
from greap.context_store import ContextStore
from greap.greap_agent import GreapAgent
from greap.notifier import Notifier
from greap.orchestrator import Orchestrator
from greap.payment_desk import PaymentDesk
from greap.procurement_order import ProcurementOrder
from greap.procurement_search import ProcurementSearch
from greap.queue_deadlines import expireUnpaid, markShortQueues
from greap.reap_client import ReapClient
from greap.toolbox import Toolbox

WELCOME = "Welcome to Greap. Let's save money together!"
ASK_NAME = "What's your name?"
PAY_COMMAND = "/pay"


class GreapApp:
    """Channel-agnostic core: Telegram and the CLI both call handleMessage."""

    def __init__(self, settings: Settings, notifier: Notifier) -> None:
        llm = AsyncOpenAI(api_key=settings.openaiApiKey)
        reap = ReapClient(settings)
        self.notifier = notifier
        self.clock = Clock()
        self.store = ContextStore(settings.dataDir)
        classifier = BulkClassifier(llm, settings.model, self.store)
        search = ProcurementSearch(reap, classifier, self.store)
        toolbox = Toolbox(self.store, search, self.clock, notifier)
        self.agent = GreapAgent(llm, settings.model, self.store, toolbox)
        self.desk = PaymentDesk(self.store)
        order = ProcurementOrder(reap, settings, notifier, search)
        self.orchestrator = Orchestrator(
            self.store, order, notifier, settings.defaultPhone
        )

    async def handleMessage(self, telegramId: str, text: str) -> list[str]:
        """FR-1.1 to FR-1.5 for the first contact, then payments, then the agent."""
        if not self.store.getUser(telegramId):
            self.store.upsertUser(telegramId)
            # Onboarding comes first (FR-1.2, FR-1.3): welcome, then the name.
            return [WELCOME, ASK_NAME]
        if self.desk.isPaying(telegramId):
            return [await self.handlePaymentText(telegramId, text)]
        if text.strip().lower().startswith(PAY_COMMAND):
            return [self.desk.startPayment(telegramId)]
        return [await self.agent.handleMessage(telegramId, text)]

    async def handlePaymentText(self, telegramId: str, text: str) -> str:
        """FR-5.4 to FR-5.6: check the typed amount, then hand over to Orchestrator."""
        reply, paidEntry = self.desk.handleAmount(telegramId, text)
        if paidEntry:
            await self.orchestrator.onPayment(paidEntry)
        return reply

    async def tick(self) -> None:
        """Deadline checks: unpaid expiry and short queues (FR-5.7, FR-6.1)."""
        now = self.clock.now()
        for telegramId, text in expireUnpaid(self.store, now) + markShortQueues(
            self.store, now
        ):
            await self.notifier.sendUser(telegramId, text)
