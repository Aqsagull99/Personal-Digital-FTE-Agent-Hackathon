module.exports = {
  apps: [
    {
      name: "local-executive-agent",
      script: "scripts/local/local_executive_agent.py",
      interpreter: "python3",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: "1",
        LOCAL_EXEC_POLL_SECONDS: "20",
        LOCAL_WHATSAPP_HEADLESS: "false",
        LOCAL_EXEC_AGENT: "1"
      }
    }
  ]
};
