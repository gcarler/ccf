import { defineAuthenticatedModuleRouteSmoke } from '../helpers/moduleRouteSmoke';

const MESSAGING_ROUTES = [
  {
    id: 'messaging-inbox',
    path: '/plataforma/inbox/messages',
    expectedText: /mensajes|conversaciones|nuevo chat|mis mensajes/i,
  },
  {
    id: 'messaging-direct',
    path: '/plataforma/messages',
    expectedText: /mensajes|conversaciones|nueva conversaci[oó]n|chat/i,
  },
  {
    id: 'community-hub',
    path: '/plataforma/community',
    expectedText: /comunidad|mensajes|grupos|eventos|oraci[oó]n/i,
  },
  {
    id: 'community-events',
    path: '/plataforma/community/events',
    expectedText: /calendario de eventos|eventos pr[oó]ximos|comunidad ccf/i,
  },
] as const;

defineAuthenticatedModuleRouteSmoke({
  suiteName: 'messaging/community critical smoke',
  tag: '@messaging',
  routes: MESSAGING_ROUTES,
});
