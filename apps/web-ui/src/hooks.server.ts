import { json } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit';
import { building } from '$app/environment';

// Backend services configuration
const BACKEND_GATEWAY = process.env.BACKEND_GATEWAY || 'http://localhost:9301';
const BACKEND_ORCHESTRATOR = process.env.BACKEND_ORCHESTRATOR || 'http://localhost:9302';

/**
 * Forward requests to the backend API gateway
 */
async function proxyRequest(
	path: string,
	request: Request,
	env: 'gateway' | 'orchestrator' = 'gateway'
): Promise<Response> {
	const target = env === 'gateway' ? BACKEND_GATEWAY : BACKEND_ORCHESTRATOR;
	const url = new URL(path, target);

	// Copy headers and set new host
	const headers = new Headers(request.headers);
	headers.set('Host', url.host);
	headers.set('Origin', target);

	// Forward the request
	const proxyRequest = new Request(url, {
		method: request.method,
		headers,
		body: request.body,
		// @ts-ignore - duplex is not in the Request type definition but is needed
		duplex: 'half'
	});

	try {
		const response = await fetch(proxyRequest);

		// Copy response headers
		const proxyHeaders = new Headers();
		response.headers.forEach((value, key) => {
			// Skip certain headers
			if (
				!['content-encoding', 'content-length', 'transfer-encoding', 'connection'].includes(key)
			) {
				proxyHeaders.set(key, value);
			}
		});

		// Handle SSE (Server-Sent Events) streaming
		if (response.headers.get('content-type')?.includes('text/event-stream')) {
			return new Response(response.body, {
				status: response.status,
				headers: {
					'Content-Type': 'text/event-stream',
					'Cache-Control': 'no-cache',
					'Connection': 'keep-alive',
					'X-Accel-Buffering': 'no'
				}
			});
		}

		return new Response(response.body, {
			status: response.status,
			headers: proxyHeaders
		});
	} catch (error) {
		console.error(`Proxy error for ${path}:`, error);
		return json(
			{ error: 'Backend service unavailable', details: error instanceof Error ? error.message : 'Unknown error' },
			{ status: 503 }
		);
	}
}

/**
 * Handle API requests - SvelteKit hooks
 */
export const handle: Handle = async ({ event, request }) => {
	const url = new URL(request.url);
	const path = url.pathname + url.search;

	// Skip proxy during build
	if (building) {
		return await event.fetch(request);
	}

	// Proxy API requests to backend
	if (url.pathname.startsWith('/api/')) {
		const apiPath = url.pathname.replace(/^\/api\//, '/');
		return await proxyRequest(apiPath, request, 'gateway');
	}

	// Proxy WebSocket requests to backend
	if (url.pathname.startsWith('/ws/')) {
		const wsPath = url.pathname.replace(/^\/ws\//, '/');
		return await proxyRequest(wsPath, request, 'gateway');
	}

	// Handle all other requests normally
	return await event.fetch(request);
};

// Type export for SvelteKit
export type Handle = typeof handle;
