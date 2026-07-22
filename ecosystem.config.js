module.exports = {
  apps: [
    {
      name: "expense-bot",
      script: "venv/bin/python",
      args: "-m bot.main",
      cwd: "/opt/expense-bot",
      interpreter: "none",
      env: {
        PATH: "/opt/expense-bot/venv/bin:/usr/bin:/bin",
      },
      watch: false,
      autorestart: true,
      restart_delay: 10000,
      max_restarts: 10,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "/var/log/expense-bot/error.log",
      out_file: "/var/log/expense-bot/out.log",
      merge_logs: true,
    },
  ],
};
