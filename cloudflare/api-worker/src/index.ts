export interface Env {
  APP_DATA: R2Bucket;
}

const ALLOWED_APPS = new Set(["breadth", "fear-greed", "exchange"]);
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

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
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
