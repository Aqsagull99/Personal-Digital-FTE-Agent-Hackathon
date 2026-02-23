module.exports = {
  apps: [
    {
      name: "cloud-gmail-watcher",
      script: "watchers/gmail_watcher.py",
      interpreter: "python3",
      args: "AI_Employee_Vault",
      autorestart: true,
      max_restarts: 20,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
        AGENT_ROLE: "cloud"
      }
    },
    {
      name: "cloud-twitter-watcher",
      script: "watchers/twitter_watcher.py",
      interpreter: "python3",
      args: "AI_Employee_Vault",
      autorestart: true,
      max_restarts: 20,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
        AGENT_ROLE: "cloud"
      }
    },
    {
      name: "cloud-facebook-watcher",
      script: "watchers/facebook_watcher.py",
      interpreter: "python3",
      args: "AI_Employee_Vault",
      autorestart: true,
      max_restarts: 20,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
        AGENT_ROLE: "cloud"
      }
    },
    {
      name: "cloud-instagram-watcher",
      script: "watchers/instagram_watcher.py",
      interpreter: "python3",
      args: "AI_Employee_Vault",
      autorestart: true,
      max_restarts: 20,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
        AGENT_ROLE: "cloud"
      }
    },
    {
      name: "cloud-draft-worker",
      script: "scripts/cloud/cloud_draft_worker.py",
      interpreter: "python3",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: "1",
        CLOUD_DRAFT_POLL_SECONDS: "20",
        AGENT_ROLE: "cloud"
      }
    },
    {
      name: "cloud-odoo-mcp",
      script: "scripts/cloud/odoo_mcp_cloud_service.py",
      interpreter: "python3",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: "1",
        AGENT_ROLE: "cloud",
        CLOUD_DRAFT_ONLY: "true",
        CLOUD_ODOO_POLL_SECONDS: "30"
      }
    },
    {
      name: "cloud-odoo-health",
      script: "scripts/cloud/odoo_health_monitor.sh",
      interpreter: "bash",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 3000,
      env: {
        ODOO_HEALTH_INTERVAL_SECONDS: "60"
      }
    },
    {
      name: "cloud-git-sync",
      script: "scripts/cloud/cloud_git_sync.sh",
      interpreter: "bash",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 3000,
      env: {
        CLOUD_SYNC_SECONDS: "60",
        CLOUD_SYNC_BRANCH: "main",
        CLOUD_SYNC_REMOTE: "origin",
        AGENT_ROLE: "cloud"
      }
    },
    {
      name: "cloud-watchdog",
      script: "scripts/cloud/watchdog_watchers.sh",
      interpreter: "bash",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 3000,
      env: {
        WATCHDOG_INTERVAL_SECONDS: "30"
      }
    }
  ]
};
