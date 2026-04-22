#!/bin/bash
set -e

echo "=== Integration Tests ==="

# Registrar usuario normal
RESP=$(curl -s -X POST http://localhost:8005/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"123456","role":"user"}')
echo "Signup: $RESP"

# Login
LOGIN_RESP=$(curl -s -X POST http://localhost:8005/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"testuser","password":"123456"}')
TOKEN=$(echo $LOGIN_RESP | jq -r '.access_token')
if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "ERROR: No se pudo obtener token"
  exit 1
fi
echo "Token obtenido"

# Crear orden
ORDER_RESP=$(curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"items":[{"sku":"LAP001","qty":1}]}')
ORDER_ID=$(echo $ORDER_RESP | jq -r '.order_id')
if [ "$ORDER_ID" = "null" ] || [ -z "$ORDER_ID" ]; then
  echo "ERROR: No se pudo crear orden"
  exit 1
fi
echo "Orden creada: $ORDER_ID"

# Verificar que usuario normal no puede ver stock (debe dar 403)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET http://localhost:8000/stock \
  -H "Authorization: Bearer $TOKEN")
if [ "$HTTP_CODE" != "403" ]; then
  echo "ERROR: Usuario normal pudo acceder a /stock (código $HTTP_CODE)"
  exit 1
fi
echo "Test de permisos OK"

echo "Todos los tests pasaron correctamente"