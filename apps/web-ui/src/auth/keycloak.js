import Keycloak from 'keycloak-js';

export function createKeycloakClient(config) {
  return new Keycloak({
    url: config.keycloak_url,
    realm: config.realm,
    clientId: config.client_id,
  });
}

