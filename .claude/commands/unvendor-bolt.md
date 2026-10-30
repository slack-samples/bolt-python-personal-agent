Switch from the vendored bolt-python wheel to the latest published `slack-bolt` package on PyPI.

## Steps

1. Look up the latest published version of `slack-bolt`:
   ```
   curl -s https://pypi.org/pypi/slack-bolt/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
   ```

2. Delete the `vendor/` directory:
   ```
   rm -rf vendor
   ```

3. In `openai-agents-sdk/requirements.txt`, replace the `../vendor/slack_bolt-*.whl` line with `slack-bolt>=<version>` using the version from step 1.

4. In `openai-agents-sdk/pyproject.toml`, replace the comment `# slack-bolt is installed from a vendored whl — see ../vendor/` with an actual dependency `"slack-bolt>=<version>"` using the version from step 1.

5. If a `.venv` virtual environment exists in `openai-agents-sdk/`, activate it and install the updated requirements:
   ```
   if [ -f openai-agents-sdk/.venv/bin/activate ]; then
     source openai-agents-sdk/.venv/bin/activate && pip install -r openai-agents-sdk/requirements.txt
   fi
   ```

6. If `.github/dependabot.yml` has an `ignore` rule for `slack-bolt`, remove it so Dependabot can manage updates.

7. Update `README.md` — replace the "Local Development" section that describes vendored bolt with:
   ```
   ## Local Development

   This repo uses [`slack-bolt`](https://pypi.org/project/slack-bolt/) from PyPI.
   ```

8. Report the version change to the user. Do NOT commit — let the user review first.
