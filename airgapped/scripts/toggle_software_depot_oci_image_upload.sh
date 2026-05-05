#!/usr/bin/env bash
#
# Toggle Software Depot OCI image upload (offlineWriteEnabled) on the
# vcf-fleet-depot component via the VSP / Platform Components API.
#
# Usage:
#   ./toggle_software_depot_oci_image_upload.sh <enable|disable> \
#       --vsp-host           vsp.example.com \
#       --ops-admin-username admin@vsp.local \
#       --ops-admin-password '...'
#
# --vsp-host accepts a hostname (with optional :port and path); the script
# always uses https://<host>. Any leading scheme you pass is stripped.
#
# Notes:
#   * enable  -> sets spec.configuration.oci.offlineWriteEnabled = true
#   * disable -> sets spec.configuration.oci.offlineWriteEnabled = false
#

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  toggle_software_depot_oci_image_upload.sh <enable|disable> \
      --vsp-host           <vsp-host>                  \
      --ops-admin-username <user@domain>                    \
      --ops-admin-password <password>

Options:
  -h, --help                 Show this help.

Notes:
  * --vsp-host should be a hostname (e.g. vsp-10-1-2-3.example.com).
    The script will use https://<host>; any leading scheme you pass is stripped.

Operation:
  enable   -> spec.configuration.oci.offlineWriteEnabled = true
  disable  -> spec.configuration.oci.offlineWriteEnabled = false
EOF
}

MODE=""
VSP_HOST=""
OPS_ADMIN_USERNAME=""
OPS_ADMIN_PASSWORD=""

# First positional must be enable|disable; everything else is --flag value
while [[ $# -gt 0 ]]; do
  case "$1" in
    enable|disable)
      if [[ -n "$MODE" ]]; then
        echo "Error: mode specified twice ('$MODE' then '$1')." >&2
        exit 1
      fi
      MODE="$1"; shift ;;
    --vsp-host)
      VSP_HOST="${2:-}"; shift 2 ;;
    --ops-admin-username)
      OPS_ADMIN_USERNAME="${2:-}"; shift 2 ;;
    --ops-admin-password)
      OPS_ADMIN_PASSWORD="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Error: unknown argument '$1'." >&2
      usage >&2
      exit 1 ;;
  esac
done

if [[ -z "$MODE" || -z "$VSP_HOST" || -z "$OPS_ADMIN_USERNAME" || -z "$OPS_ADMIN_PASSWORD" ]]; then
  echo "Error: missing required arguments." >&2
  usage >&2
  exit 1
fi

for cmd in curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: required command '$cmd' is not in PATH." >&2
    exit 1
  fi
done

case "$MODE" in
  enable)  OFFLINE_WRITE_ENABLED=true  ;;
  disable) OFFLINE_WRITE_ENABLED=false ;;
esac

VSP_HOST="${VSP_HOST#http://}"
VSP_HOST="${VSP_HOST#https://}"
VSP_HOST="${VSP_HOST%/}"
VSP_URL="https://${VSP_HOST}"

CONFIG_JSON="$(mktemp -t depot-oci-config.XXXXXX.json)"
trap 'rm -f "$CONFIG_JSON"' EXIT

cat > "$CONFIG_JSON" <<EOF
{
  "spec": {
    "configuration": {
      "oci": {
        "offlineWriteEnabled": ${OFFLINE_WRITE_ENABLED}
      }
    }
  }
}
EOF

echo "Mode: ${MODE} (offlineWriteEnabled=${OFFLINE_WRITE_ENABLED})"
echo "VSP URL: ${VSP_URL}"
echo "Payload:"
cat "$CONFIG_JSON"
echo

echo "==> Logging in to obtain access token..."
TOKEN="$(curl -k -sS -XPOST "${VSP_URL}/api/v1/identity/token" \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data grant_type=password \
  --data "username=${OPS_ADMIN_USERNAME}" \
  --data "password=${OPS_ADMIN_PASSWORD}" \
  | jq -r '.access_token // empty')"

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "Error: failed to obtain access token from ${VSP_URL}" >&2
  exit 1
fi
export TOKEN

echo "==> Looking up vcf-fleet-depot component id..."
VCF_FLEET_DEPOT_COMPONENT_ID="$(curl -k -sS -H "Authorization: Bearer ${TOKEN}" \
  "${VSP_URL}/api/v1/components" \
  | jq -r '.components[] | select(.name == "vcf-fleet-depot") | .id')"

if [[ -z "$VCF_FLEET_DEPOT_COMPONENT_ID" || "$VCF_FLEET_DEPOT_COMPONENT_ID" == "null" ]]; then
  echo "Error: could not find component 'vcf-fleet-depot' in ${VSP_URL}/api/v1/components" >&2
  exit 1
fi
export VCF_FLEET_DEPOT_COMPONENT_ID
echo "    vcf-fleet-depot id: ${VCF_FLEET_DEPOT_COMPONENT_ID}"

echo "==> Applying configuration update..."
TASK_ID="$(curl -k -sS -XPOST -H "Authorization: Bearer ${TOKEN}" \
  "${VSP_URL}/api/v1/components/${VCF_FLEET_DEPOT_COMPONENT_ID}?action=apply" \
  -d @"${CONFIG_JSON}" \
  | jq -r '.id // empty')"

if [[ -z "$TASK_ID" || "$TASK_ID" == "null" ]]; then
  echo "Error: apply request did not return a task id." >&2
  exit 1
fi
export TASK_ID
echo "    task id: ${TASK_ID}"

echo "==> Waiting for task to complete..."
SLEEP_SECS=10
MAX_WAIT_SECS=600
DEADLINE=$(( $(date +%s) + MAX_WAIT_SECS ))

while true; do
  STATUS="$(curl -ks -H "Authorization: Bearer ${TOKEN}" \
    "${VSP_URL}/api/v1/tasks/${TASK_ID}" \
    | jq -r '.status // empty')"

  case "$STATUS" in
    Succeeded)
      echo "Software Depot config update is success!"
      exit 0
      ;;
    Failed|Cancelled|Error)
      echo "Error: task ${TASK_ID} ended with status '${STATUS}'." >&2
      curl -ks -H "Authorization: Bearer ${TOKEN}" \
        "${VSP_URL}/api/v1/tasks/${TASK_ID}" | jq . >&2 || true
      exit 1
      ;;
    "")
      echo "Warning: empty status from task ${TASK_ID}, retrying..." >&2
      ;;
    *)
      echo "Still waiting for task to be done... (current status: ${STATUS})"
      ;;
  esac

  if (( $(date +%s) >= DEADLINE )); then
    echo "Error: task ${TASK_ID} did not reach Succeeded within ${MAX_WAIT_SECS}s (last status: '${STATUS}')." >&2
    exit 1
  fi

  sleep "$SLEEP_SECS"
done
