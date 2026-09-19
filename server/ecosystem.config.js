// pm2 でフィードバックAPIを起動する設定。
//
// パスはこのファイルの位置から解決するので、設置先がどこでもそのまま動く。
// 期待するレイアウト:
//
//   <root>/
//   ├── api/      app.py, start.sh, .venv/
//   └── server/   ecosystem.config.js  <- このファイル
//
// 他サービスと同居している既定の pm2 デーモン (~/.pm2) とは分離するため、
// 必ず PM2_HOME を指定して実行する。こうすると dump.pm2 もプロセス一覧も
// このアプリ専用になり、他アプリの操作と干渉しない。
//
//   export PM2_HOME=<root>/api/.pm2
//   pm2 start <root>/server/ecosystem.config.js
//   pm2 save
//
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const API = path.join(ROOT, "api");

module.exports = {
  apps: [
    {
      name: "calc-dojo-feedback",
      cwd: API,
      // start.sh が unix socket の作成と権限調整まで行う
      script: path.join(API, "start.sh"),
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000
    }
  ]
};
