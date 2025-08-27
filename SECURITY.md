# 🔒 Security Configuration Guide

## ⚠️ IMPORTANT SECURITY NOTICE

This project requires API keys and tokens that should **NEVER** be committed to version control.

## 🔑 Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Copy from .env.example and fill in your actual values

# GitHub Personal Access Token (for LLM access)
GITHUB_TOKEN=ghp_your_actual_token_here

# Murf AI API Key (for voice synthesis)
MURF_API_KEY=ap2_your_actual_key_here

# OpenAI API Key (optional, for enhanced LLM)
OPENAI_API_KEY=sk-your_actual_key_here
```

## 🛡️ Security Best Practices

### 1. Environment File Protection
- The `.env` file is already in `.gitignore`
- Never commit `.env` to version control
- Use `.env.example` as a template

### 2. API Key Security
- Keep API keys secure and rotate them regularly
- Use different keys for development and production
- Monitor API key usage in your provider dashboards

### 3. GitHub Token Permissions
Your GitHub token needs these minimum permissions:
- `repo` (if accessing private repos)
- `read:user` (for basic authentication)

### 4. Murf AI Key Setup
1. Sign up at https://murf.ai
2. Get your API key from the dashboard
3. Add to `.env` file as `MURF_API_KEY`

## 🚨 If Tokens Are Exposed

If you accidentally commit API keys:

1. **Immediately revoke the exposed tokens**:
   - GitHub: Go to Settings > Developer settings > Personal access tokens
   - Murf AI: Go to your dashboard and regenerate API key

2. **Remove from git history**:
   ```bash
   git reset --soft HEAD~1  # Undo last commit
   # Fix the files
   git add .
   git commit -m "Add secure configuration"
   ```

3. **Generate new tokens** and update your local `.env`

## ✅ Setup Instructions

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual API keys:
   ```bash
   nano .env  # or use your preferred editor
   ```

3. Verify `.env` is in `.gitignore`:
   ```bash
   grep -n "\.env" .gitignore
   ```

4. Test the application:
   ```bash
   uv run streamlit run multi_agent_app.py --server.port 8504
   ```

## 🔍 Verification

Your `.env` file should look like this (with your actual values):

```bash
GITHUB_TOKEN=ghp_1234567890abcdef...
MURF_API_KEY=ap2_12345678-1234-1234-1234-123456789abc
OPENAI_API_KEY=sk-proj-1234567890abcdef...
```

## 📞 Support

If you have security concerns or questions:
1. Check the documentation files
2. Ensure all tokens are properly configured
3. Test the application locally before deployment

**Remember: Security is paramount. When in doubt, regenerate your API keys.**
