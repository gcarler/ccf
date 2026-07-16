import { expect, test, type Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

const CURRENT_USER_ID = 'e2e-user';

const BASE_CONVERSATIONS = [
  {
    id: 101,
    participants: [
      {
        persona_id: CURRENT_USER_ID,
        username: 'pastor.e2e',
        last_read_at: '2026-07-16T09:00:00Z',
      },
      {
        persona_id: 'persona-abigail',
        username: 'Abigail Monsalve',
        last_read_at: '2026-07-16T08:55:00Z',
      },
    ],
    last_message_content: 'Nos vemos en el seguimiento de esta tarde.',
    last_message_at: '2026-07-16T08:58:00Z',
    last_sender_id: 'persona-abigail',
    unread_count: 2,
    created_at: '2026-07-15T10:00:00Z',
  },
  {
    id: 102,
    participants: [
      {
        persona_id: CURRENT_USER_ID,
        username: 'pastor.e2e',
        last_read_at: '2026-07-16T09:00:00Z',
      },
      {
        persona_id: 'persona-carlos',
        username: 'Carlos Rueda',
        last_read_at: '2026-07-16T08:00:00Z',
      },
    ],
    last_message_content: 'Gracias por el recurso compartido.',
    last_message_at: '2026-07-16T07:30:00Z',
    last_sender_id: CURRENT_USER_ID,
    unread_count: 0,
    created_at: '2026-07-10T10:00:00Z',
  },
];

const MESSAGE_SEED: Record<number, Array<{
  id: number;
  sender_id: string;
  sender_name: string;
  content: string;
  created_at: string;
  is_read: boolean;
}>> = {
  101: [
    {
      id: 5001,
      sender_id: 'persona-abigail',
      sender_name: 'Abigail Monsalve',
      content: 'Hola, ¿ya quedó lista la reunión de seguimiento?',
      created_at: '2026-07-16T08:52:00Z',
      is_read: true,
    },
    {
      id: 5002,
      sender_id: CURRENT_USER_ID,
      sender_name: 'pastor.e2e',
      content: 'Sí, la dejamos para las 6:00 PM.',
      created_at: '2026-07-16T08:55:00Z',
      is_read: true,
    },
    {
      id: 5003,
      sender_id: 'persona-abigail',
      sender_name: 'Abigail Monsalve',
      content: 'Nos vemos en el seguimiento de esta tarde.',
      created_at: '2026-07-16T08:58:00Z',
      is_read: false,
    },
  ],
  102: [
    {
      id: 5101,
      sender_id: CURRENT_USER_ID,
      sender_name: 'pastor.e2e',
      content: 'Te compartí el recurso de liderazgo.',
      created_at: '2026-07-16T07:20:00Z',
      is_read: true,
    },
    {
      id: 5102,
      sender_id: 'persona-carlos',
      sender_name: 'Carlos Rueda',
      content: 'Gracias por el recurso compartido.',
      created_at: '2026-07-16T07:30:00Z',
      is_read: true,
    },
  ],
};

const SEARCH_RESULTS = [
  {
    id: 'persona-maria',
    username: 'María Salcedo',
    email: 'maria.salcedo@ccf.local',
    avatar_url: null,
  },
];

async function installMessagingDeepMocks(page: Page) {
  let conversationsState = BASE_CONVERSATIONS.map((conv) => ({
    ...conv,
    participants: conv.participants.map((participant) => ({ ...participant })),
  }));
  const messagesState = Object.fromEntries(
    Object.entries(MESSAGE_SEED).map(([key, messages]) => [
      Number(key),
      messages.map((message) => ({ ...message })),
    ]),
  ) as typeof MESSAGE_SEED;
  let nextConversationId = 200;
  let nextMessageId = 9000;

  await installMockPlatformSession(page, {
    role: 'admin',
    permissions: {
      'messaging:read': 'allow',
      'messaging:send': 'allow',
      'community:read': 'allow',
    },
  });

  await page.addInitScript(() => {
    class FakeWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;
      readyState = FakeWebSocket.OPEN;
      onopen: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;

      constructor() {
        setTimeout(() => this.onopen?.(new Event('open')), 0);
      }

      send() {}
      close() {
        this.readyState = FakeWebSocket.CLOSED;
        this.onclose?.(new CloseEvent('close'));
      }
      addEventListener() {}
      removeEventListener() {}
      dispatchEvent() {
        return true;
      }
    }

    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      writable: true,
      value: FakeWebSocket,
    });
  });

  await page.route('**/api/chat/conversations', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { participant_ids: string[] };
      const participantId = body.participant_ids[0];
      const persona =
        SEARCH_RESULTS.find((item) => item.id === participantId) ?? {
          id: participantId,
          username: 'Usuario nuevo',
          email: 'nuevo@ccf.local',
          avatar_url: null,
        };
      const createdConversation = {
        id: nextConversationId++,
        participants: [
          {
            persona_id: CURRENT_USER_ID,
            username: 'pastor.e2e',
            last_read_at: '2026-07-16T09:00:00Z',
          },
          {
            persona_id: persona.id,
            username: persona.username,
            last_read_at: null,
          },
        ],
        last_message_content: null,
        last_message_at: null,
        last_sender_id: null,
        unread_count: 0,
        created_at: '2026-07-16T10:00:00Z',
      };
      conversationsState = [createdConversation, ...conversationsState];
      messagesState[createdConversation.id] = [];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createdConversation),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(conversationsState),
    });
  });

  await page.route('**/api/chat/conversations/*/messages**', async (route) => {
    const conversationId = Number(route.request().url().split('/conversations/')[1]?.split('/messages')[0]);
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { content: string };
      const createdMessage = {
        id: nextMessageId++,
        sender_id: CURRENT_USER_ID,
        sender_name: 'pastor.e2e',
        content: body.content,
        created_at: '2026-07-16T10:05:00Z',
        is_read: false,
      };
      messagesState[conversationId] = [...(messagesState[conversationId] ?? []), createdMessage];
      conversationsState = conversationsState.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              last_message_content: createdMessage.content,
              last_message_at: createdMessage.created_at,
              last_sender_id: createdMessage.sender_id,
            }
          : conversation,
      );
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createdMessage),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(messagesState[conversationId] ?? []),
    });
  });

  await page.route('**/api/chat/conversations/*/read', async (route) => {
    const conversationId = Number(route.request().url().split('/conversations/')[1]?.split('/read')[0]);
    conversationsState = conversationsState.map((conversation) =>
      conversation.id === conversationId
        ? { ...conversation, unread_count: 0 }
        : conversation,
    );
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.route('**/api/chat/users/search**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(SEARCH_RESULTS),
    });
  });
}

test.describe('Messaging direct messages deep smoke', () => {
  test.beforeEach(async ({ page }) => {
    await installMessagingDeepMocks(page);
  });

  test('renders conversations, filters them and opens an existing thread', async ({ page }) => {
    await page.goto('/plataforma/messages', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText(/Mensajes/i);
    await expect(page.locator('body')).toContainText(/Abigail Monsalve/i);
    await expect(page.locator('body')).toContainText(/Carlos Rueda/i);

    await page.getByPlaceholder(/Buscar/i).fill('abigail');
    await expect(page.locator('body')).toContainText(/Abigail Monsalve/i);
    await expect(page.locator('body')).not.toContainText(/Carlos Rueda/i);

    await page.getByPlaceholder(/Buscar/i).fill('');
    await page.getByRole('button', { name: /Abigail Monsalve/i }).click();

    await expect(page.locator('body')).toContainText(/Hola, ¿ya quedó lista la reunión de seguimiento/i);
    await expect(page.locator('body')).toContainText(/Sí, la dejamos para las 6:00 PM/i);
    await expect(page.locator('body')).toContainText(/Nos vemos en el seguimiento de esta tarde/i);
  });

  test('searches a user and creates a new direct conversation', async ({ page }) => {
    await page.goto('/plataforma/messages', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByRole('button', { name: /Nueva conversación/i }).first().click();
    await expect(page.locator('body')).toContainText(/Busca un usuario para iniciar un chat/i);

    await page.getByPlaceholder(/Buscar por nombre o email/i).fill('maria');
    await expect(page.locator('body')).toContainText(/María Salcedo/i);
    await expect(page.locator('body')).toContainText(/maria.salcedo@ccf.local/i);

    await page.getByRole('button', { name: /María Salcedo/i }).click();
    await expect(page.locator('body')).toContainText(/María Salcedo/i);
    await expect(page.locator('body')).toContainText(/Sin mensajes aún/i);
  });

  test('sends a message inside an active conversation and updates the thread', async ({ page }) => {
    await page.goto('/plataforma/messages', { waitUntil: 'load' });
    await page.waitForLoadState('domcontentloaded');

    await page.getByRole('button', { name: /Abigail Monsalve/i }).click();
    await page.getByPlaceholder(/Escribe un mensaje/i).fill('Queda confirmado el acompañamiento.');
    await page.getByRole('button', { name: /^$/ }).last().click();

    await expect(page.locator('body')).toContainText(/Queda confirmado el acompañamiento/i);
    await expect(page.locator('body')).toContainText(/✓/i);
  });
});
