#!/bin/bash

# Keycloak Admin API Setup Script
# Run this on the Keycloak server

set -e

KEYCLOAK_URL="http://localhost:8080"
ADMIN_USER="admin"
ADMIN_PASSWORD="admin_password"
REALM="rshAnyGen"

echo "=== Step 1: Getting admin token ==="
ACCESS_TOKEN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASSWORD}" \
  -d "grant_type=password" | jq -r '.access_token')

echo "Token obtained: ${ACCESS_TOKEN:0:50}..."
echo ""

echo "=== Step 2: Creating web-ui client ==="
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "clientId": "web-ui",
    "enabled": true,
    "publicClient": true,
    "redirectUris": ["http://localhost:9300/*"],
    "webOrigins": ["http://localhost:9300"],
    "standardFlowEnabled": true
  }'
echo ""
echo "web-ui client created"
sleep 2
echo ""

echo "=== Step 3: Creating backend-api client ==="
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "clientId": "backend-api",
    "enabled": true,
    "publicClient": false,
    "clientAuthenticatorType": "client-secret",
    "secret": "backend-secret-123456",
    "serviceAccountsEnabled": true,
    "authorizationServicesEnabled": true,
    "directAccessGrantsEnabled": true
  }'
echo ""
echo "backend-api client created"
sleep 2
echo ""

echo "=== Step 4: Listing all clients ==="
curl -s "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[] | {clientId, publicClient}'
echo ""

echo "=== Step 5: Getting backend-api client secret ==="
curl -s "${KEYCLOAK_URL}/admin/realms/${REALM}/clients/backend-api" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.secret'
echo ""

echo "=== Setup complete ==="
