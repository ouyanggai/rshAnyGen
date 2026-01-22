let _accessToken = null;

export function setAccessToken(token) {
  _accessToken = token || null;
}

export function getAccessToken() {
  return _accessToken;
}

