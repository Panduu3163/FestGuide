#!/usr/bin/env bash
# Publish FestGuide to a Hugging Face Space (docs/deploy.md).
#
#   bash deploy/hf_push.sh Panduu3163/festguide
#
# Hugging Face refuses files over 10 MB and needs a header at the top of README.md, so this does NOT push
# your normal history. It builds ONE fresh commit in a temporary folder:
#   - the current committed code (git archive, so .env and .state can never be included),
#   - without the rulebook PDFs (two are over 10 MB, and the demo uses rulebooks/clean/*.md),
#   - with the Space header added to README.md,
# and force-pushes that single commit to the Space. Your own repo, branches and history are not touched.
# Git asks for your Hugging Face username and, as the password, an access token with WRITE permission
# (huggingface.co/settings/tokens). Type it into the prompt; do not put it in a file.
set -euo pipefail
space="${1:?usage: bash deploy/hf_push.sh <hf-username>/<space-name>}"
root="$(git rev-parse --show-toplevel)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git -C "$root" archive HEAD | tar -x -C "$tmp"
rm -f "$tmp"/rulebooks/*.pdf
rm -rf "$tmp/rulebooks/draft"
{
  printf -- '---\ntitle: FestGuide\nsdk: docker\napp_port: 7860\npinned: false\n'
  printf 'short_description: CSE Fest 2026 rulebook assistant with an organizer approval flow\n---\n\n'
  cat "$tmp/README.md"
} > "$tmp/README.new" && mv "$tmp/README.new" "$tmp/README.md"

cd "$tmp"
git init -q -b main
git config user.name "$(git -C "$root" config user.name)"
git config user.email "$(git -C "$root" config user.email)"
git add -A
git commit -q -m "FestGuide demo snapshot"
git remote add space "https://huggingface.co/spaces/$space"
git push --force space main
echo "Pushed. Watch the build at https://huggingface.co/spaces/$space"
