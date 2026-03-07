export type MessageRole = 'user' | 'assistant' | 'system';

export class ToolRunOut {
  tool_name: string;
  status: string;
  request_payload: Record<string, unknown> | null;
  response_payload: Record<string, unknown> | null;
  latency_ms: number | null;

  constructor(params: {
    tool_name: string;
    status: string;
    request_payload?: Record<string, unknown> | null;
    response_payload?: Record<string, unknown> | null;
    latency_ms?: number | null;
  }) {
    this.tool_name = params.tool_name;
    this.status = params.status;
    this.request_payload = params.request_payload ?? null;
    this.response_payload = params.response_payload ?? null;
    this.latency_ms = params.latency_ms ?? null;
  }

  static fromApi(raw: unknown): ToolRunOut {
    const obj = (raw ?? {}) as Record<string, unknown>;
    return new ToolRunOut({
      tool_name: String(obj.tool_name ?? ''),
      status: String(obj.status ?? ''),
      request_payload: (obj.request_payload as Record<string, unknown> | null) ?? null,
      response_payload: (obj.response_payload as Record<string, unknown> | null) ?? null,
      latency_ms: typeof obj.latency_ms === 'number' ? obj.latency_ms : null,
    });
  }
}

export class MessageOut {
  id: string;
  role: MessageRole;
  content: Record<string, unknown>;
  tool_runs: ToolRunOut[];
  created_at: string;

  constructor(params: {
    id: string;
    role: MessageRole;
    content: Record<string, unknown>;
    tool_runs?: ToolRunOut[];
    created_at: string;
  }) {
    this.id = params.id;
    this.role = params.role;
    this.content = params.content;
    this.tool_runs = params.tool_runs ?? [];
    this.created_at = params.created_at;
  }

  static fromApi(raw: unknown): MessageOut {
    const obj = (raw ?? {}) as Record<string, unknown>;
    const toolRunsRaw = Array.isArray(obj.tool_runs) ? obj.tool_runs : [];

    const roleValue = String(obj.role ?? 'assistant');
    const role: MessageRole =
      roleValue === 'user' || roleValue === 'assistant' || roleValue === 'system'
        ? roleValue
        : 'assistant';

    return new MessageOut({
      id: String(obj.id ?? ''),
      role,
      content: (obj.content as Record<string, unknown>) ?? {},
      tool_runs: toolRunsRaw.map((item) => ToolRunOut.fromApi(item)),
      created_at: String(obj.created_at ?? ''),
    });
  }
}
