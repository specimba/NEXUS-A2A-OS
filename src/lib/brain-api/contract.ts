export const BRAIN_API_BASE = process.env.NEXUS_BRAIN_API_BASE || 'http://localhost:7352';

export type BrainRouteStatus = 'LIVE' | 'MOCK' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';

export interface BrainApiRoute {
  id: string;
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  description: string;
  lane: string;
  kind: 'read' | 'mutate' | 'websocket';
}

export const brainApiEndpoints: BrainApiRoute[] = [
  { id: 'health', path: '/health', method: 'GET', description: 'Health check', lane: 'brain-api', kind: 'read' },
  { id: 'agents', path: '/api/agents', method: 'GET', description: 'List agents', lane: 'agents', kind: 'read' },
  { id: 'tasks', path: '/api/tasks', method: 'GET', description: 'List tasks', lane: 'tasks', kind: 'read' },
  { id: 'models', path: '/api/models', method: 'GET', description: 'List models', lane: 'models', kind: 'read' },
  { id: 'providers', path: '/api/providers', method: 'GET', description: 'Provider health', lane: 'providers', kind: 'read' },
  { id: 'relay-health', path: '/api/relay/health', method: 'GET', description: 'Relay health', lane: 'modelrelay', kind: 'read' },
];

export const READ_ONLY_BRAIN_ROUTES = brainApiEndpoints.filter(
  (route) => route.kind === 'read' && route.method === 'GET',
);

export const BRAIN_API_ROUTES = brainApiEndpoints;
