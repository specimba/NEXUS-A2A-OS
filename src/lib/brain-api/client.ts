import { BRAIN_API_BASE, brainApiEndpoints } from './contract';

export type HealthStatus = 'OK' | 'OFFLINE' | 'UNKNOWN' | 'DEGRADED';

export type EndpointStatus = {
  path: string;
  method: string;
  status: HealthStatus;
  httpStatus?: number;
  reason?: string;
};

export type BrainApiFetchResult = {
  ok: boolean;
  status: number | null;
  contentType: string;
  data: unknown;
  textPreview: string;
  error?: string;
};

export async function fetchBrainApi(path: string, init?: RequestInit): Promise<BrainApiFetchResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(`${BRAIN_API_BASE.replace(/\/$/, '')}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.headers || {}),
      },
      signal: controller.signal,
      cache: 'no-store',
    });
    const contentType = response.headers.get('content-type') || '';
    const text = await response.text();
    let data: unknown = null;
    if (contentType.includes('application/json') && text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
    return {
      ok: response.ok,
      status: response.status,
      contentType,
      data,
      textPreview: text.slice(0, 240),
    };
  } catch (error) {
    return {
      ok: false,
      status: null,
      contentType: '',
      data: null,
      textPreview: '',
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

export class BrainClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor(apiKey?: string, baseUrl = BRAIN_API_BASE) {
    this.apiKey = apiKey || process.env.NEXUS_BRAIN_API_KEY || '';
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async fetchJson<T>(path: string, init?: RequestInit): Promise<{ data?: T; status: number; ok: boolean }> {
    const headers = new Headers(init?.headers);
    if (this.apiKey) {
      headers.set('Authorization', `Bearer ${this.apiKey}`);
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers,
        signal: controller.signal,
      });
      const contentType = response.headers.get('content-type') || '';
      const data = contentType.includes('application/json') ? await response.json() as T : undefined;
      return { data, status: response.status, ok: response.ok };
    } finally {
      clearTimeout(timeout);
    }
  }

  private async probeEndpoint(path: string, method: string): Promise<EndpointStatus> {
    try {
      const response = await this.fetchJson<unknown>(path, { method });
      if (response.ok) {
        return { path, method, status: 'OK', httpStatus: response.status };
      }
      if (response.status === 401 || response.status === 403) {
        return { path, method, status: 'DEGRADED', httpStatus: response.status, reason: 'Authentication required' };
      }
      if (response.status >= 500) {
        return { path, method, status: 'OFFLINE', httpStatus: response.status, reason: 'Brain API service error' };
      }
      return { path, method, status: 'UNKNOWN', httpStatus: response.status, reason: `Unexpected HTTP ${response.status}` };
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      return { path, method, status: 'OFFLINE', reason };
    }
  }

  async probeAllEndpoints(): Promise<EndpointStatus[]> {
    return Promise.all(
      brainApiEndpoints.map((endpoint) => this.probeEndpoint(endpoint.path, endpoint.method)),
    );
  }

  async getHealth(): Promise<EndpointStatus> {
    return this.probeEndpoint('/health', 'GET');
  }

  async getHealthReady(): Promise<EndpointStatus> {
    return this.probeEndpoint('/health/ready', 'GET');
  }

  async getProviderDetail(providerId: string): Promise<EndpointStatus> {
    return this.probeEndpoint(`/api/providers/${providerId}`, 'GET');
  }

  async relayHealth(): Promise<EndpointStatus> {
    return this.probeEndpoint('/api/relay/health', 'GET');
  }
}
