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
echo "For zhengpinzhong@outlook.com, the recommended defaults are:"
echo "  EMAIL_BACKEND=smtp"
echo "  SMTP_HOST=smtp-mail.outlook.com"
echo "  SMTP_USERNAME=zhengpinzhong@outlook.com"
echo "  MAIL_FROM=zhengpinzhong@outlook.com"
echo "  MAIL_TO=zhengpinzhong@outlook.com"
echo

read -r -p "EMAIL_BACKEND [smtp]: " email_backend
email_backend="${email_backend:-smtp}"

read -r -p "SMTP_HOST [smtp-mail.outlook.com]: " smtp_host
smtp_host="${smtp_host:-smtp-mail.outlook.com}"

read -r -p "SMTP_USERNAME [zhengpinzhong@outlook.com]: " smtp_username
smtp_username="${smtp_username:-zhengpinzhong@outlook.com}"

read -r -s -p "SMTP_PASSWORD (input hidden): " smtp_password
echo

read -r -p "MAIL_FROM [zhengpinzhong@outlook.com]: " mail_from
mail_from="${mail_from:-zhengpinzhong@outlook.com}"

read -r -p "MAIL_TO [zhengpinzhong@outlook.com]: " mail_to
mail_to="${mail_to:-zhengpinzhong@outlook.com}"

printf '%s' "${email_backend}" | gh secret set EMAIL_BACKEND --repo "${repo}" --body -
printf '%s' "${smtp_host}" | gh secret set SMTP_HOST --repo "${repo}" --body -
printf '%s' "${smtp_username}" | gh secret set SMTP_USERNAME --repo "${repo}" --body -
printf '%s' "${smtp_password}" | gh secret set SMTP_PASSWORD --repo "${repo}" --body -
printf '%s' "${mail_from}" | gh secret set MAIL_FROM --repo "${repo}" --body -
printf '%s' "${mail_to}" | gh secret set MAIL_TO --repo "${repo}" --body -

echo
echo "Done. The following secrets were set for ${repo}:"
echo "  EMAIL_BACKEND"
echo "  SMTP_HOST"
echo "  SMTP_USERNAME"
echo "  SMTP_PASSWORD"
echo "  MAIL_FROM"
echo "  MAIL_TO"
echo
echo "Next step:"
echo "  gh workflow run \"StormWatch Daily\""
