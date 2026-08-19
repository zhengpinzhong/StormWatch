#!/usr/bin/env bash

set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: GitHub CLI 'gh' is not installed."
  echo "Install it first: https://cli.github.com/"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated."
  echo "Run: gh auth login"
  exit 1
fi

repo="$(git remote get-url origin 2>/dev/null | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
if [[ -z "${repo}" ]]; then
  echo "Error: could not determine GitHub repo from origin remote."
  exit 1
fi

echo "Configuring GitHub Actions secrets for repo: ${repo}"
echo
echo "Recommended Bark defaults:"
echo "  EMAIL_BACKEND=bark"
echo "  BARK_DEVICE_KEY=<your Bark device key>"
echo "You can paste either the full Bark URL or just the device key."
echo

read -r -p "EMAIL_BACKEND [bark]: " email_backend
email_backend="${email_backend:-bark}"

read -r -s -p "BARK URL or device key (input hidden): " bark_device_input
echo

bark_device_input="${bark_device_input%/}"
if [[ "${bark_device_input}" == http://* || "${bark_device_input}" == https://* ]]; then
  bark_device_key="${bark_device_input##*/}"
else
  bark_device_key="${bark_device_input}"
fi

if [[ -z "${bark_device_key}" ]]; then
  echo "Error: Bark device key is empty."
  exit 1
fi

printf '%s' "${email_backend}" | gh secret set EMAIL_BACKEND --repo "${repo}" --body -
printf '%s' "${bark_device_key}" | gh secret set BARK_DEVICE_KEY --repo "${repo}" --body -

echo
echo "Done. The following secrets were set for ${repo}:"
echo "  EMAIL_BACKEND"
echo "  BARK_DEVICE_KEY"
echo
echo "Next step:"
echo "  gh workflow run \"StormWatch Daily\""
