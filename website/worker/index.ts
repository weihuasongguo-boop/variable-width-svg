interface Env { ASSETS: { fetch(request: Request): Promise<Response> } }
export default {
  fetch(request: Request, env: Env): Promise<Response> {
    const path = new URL(request.url).pathname;
    if (path === '/variable-width' || path.startsWith('/variable-width/')) {
      return env.ASSETS.fetch(request);
    }
    // The route's wildcard also matches longer prefixes. Pass those to the
    // existing origin so this project never takes ownership of unrelated URLs.
    return fetch(request);
  },
};
