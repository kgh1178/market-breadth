export interface Env {
  APP_DATA: R2Bucket;
  LOTOPICK_ORIGIN?: string;
}

const ALLOWED_APPS = new Set(["breadth", "fear-greed", "exchange"]);
const LOTOPICK_PUBLIC_BASE = "/lotopick";
const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "public, max-age=300",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: JSON_HEADERS,
  });
}

function notFound(message: string): Response {
  return jsonResponse({ error: message }, 404);
}

function serviceUnavailable(message: string): Response {
  return new Response(message, {
    status: 503,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function isLotopickPath(pathname: string): boolean {
  return pathname === LOTOPICK_PUBLIC_BASE || pathname.startsWith(`${LOTOPICK_PUBLIC_BASE}/`);
}

function buildLotopickUpstreamUrl(request: Request, env: Env): URL | null {
  if (!env.LOTOPICK_ORIGIN) {
    return null;
  }

  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL(env.LOTOPICK_ORIGIN);

  upstreamUrl.pathname = requestUrl.pathname;
  upstreamUrl.search = requestUrl.search;

  return upstreamUrl;
}

async function proxyLotopickRequest(request: Request, env: Env): Promise<Response> {
  const upstreamUrl = buildLotopickUpstreamUrl(request, env);

  if (upstreamUrl === null) {
    return serviceUnavailable("LotoPick origin is not configured");
  }

  const forwardedHeaders = new Headers(request.headers);
  forwardedHeaders.set("x-lotopick-public-origin", new URL(request.url).origin);
  const upstreamRequest = new Request(upstreamUrl.toString(), {
    method: request.method,
    headers: forwardedHeaders,
    body: request.body,
    redirect: request.redirect,
  });
  const upstreamResponse = await fetch(upstreamRequest);
  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: new Headers(upstreamResponse.headers),
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (isLotopickPath(url.pathname)) {
      return proxyLotopickRequest(request, env);
    }

    const match = url.pathname.match(/^\/([^/]+)\/api\/(.+)$/);
    if (!match) {
      return notFound("API route not found");
    }

    const [, app, rest] = match;
    if (!ALLOWED_APPS.has(app)) {
      return notFound(`Unknown app: ${app}`);
    }

    const key = `${app}/${rest}`;
    const object = await env.APP_DATA.get(key);
    if (!object) {
      return notFound(`Missing object: ${key}`);
    }

    return new Response(object.body, {
      headers: {
        ...JSON_HEADERS,
        etag: object.httpEtag,
      },
    });
  },
};
