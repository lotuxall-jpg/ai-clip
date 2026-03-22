name: AI Clip Generator

on:
  schedule:
    - cron: '0 * * * *'
  workflow_dispatch:

jobs:
  generate-and-post:
    runs-on: ubuntu-latest
    timeout-minutes: 55

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install FFmpeg
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y ffmpeg

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install anthropic openai yt-dlp feedparser requests openai-whisper python-dotenv google-api-python-client google-auth-oauthlib google-auth

      - name: Restore posted log
        uses: actions/cache@v4
        with:
          path: posted_log.json
          key: posted-log-${{ github.run_id }}
          restore-keys: |
            posted-log-

      - name: Create folders
        run: |
          mkdir -p downloads clips output assets/music assets/sfx assets/branding

      - name: Run AI Clip Generator
        run: |
          export ANTHROPIC_API_KEY="${{ secrets.ANTHROPIC_API_KEY }}"
          export AI_PROVIDER="claude"
          export OPENAI_API_KEY="${{ secrets.OPENAI_API_KEY }}"
          export TELEGRAM_BOT_TOKEN="${{ secrets.TELEGRAM_BOT_TOKEN }}"
          export TELEGRAM_CHAT_ID="${{ secrets.TELEGRAM_CHAT_ID }}"
          export TIKTOK_ACCESS_TOKEN="${{ secrets.TIKTOK_ACCESS_TOKEN }}"
          export AUTO_POST_TIKTOK="false"
          export AUTO_POST_YOUTUBE="false"
          export MAX_VIDEOS_PER_RUN="1"
          python main.py

      - name: Save posted log
        if: always()
        uses: actions/cache@v4
        with:
          path: posted_log.json
          key: posted-log-${{ github.run_id }}

      - name: Upload output clips
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: clips-${{ github.run_number }}
          path: output/
          retention-days: 3

      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: logs-${{ github.run_number }}
          path: app.log
          retention-days: 7
