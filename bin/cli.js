#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn, execSync } = require('child_process');

const REPO_ROOT = path.resolve(__dirname, '..');
const HOME = os.homedir();
const PLUGIN_TARGET = path.join(HOME, '.gemini', 'config', 'plugins', 'agy-rich-presence');
const CONFIG_DIR = path.join(HOME, '.gemini', 'antigravity-cli');
const PID_FILE = path.join(CONFIG_DIR, 'discord_rpc_daemon.pid');
const STATE_FILE = path.join(CONFIG_DIR, 'discord_rpc_state.json');

const args = process.argv.slice(2);
const command = args[0] || 'install';

function copyRecursive(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    if (['.git', 'node_modules', '.github'].includes(entry.name)) continue;
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyRecursive(s, d);
    } else {
      fs.copyFileSync(s, d);
      if (['.py', '.sh', '.js'].some(ext => entry.name.endsWith(ext))) {
        try { fs.chmodSync(d, 0o755); } catch {}
      }
    }
  }
}

function getPythonCommand() {
  if (process.platform === 'win32') {
    try {
      execSync('python --version', { stdio: 'ignore' });
      return 'python';
    } catch {}
    try {
      execSync('py -3 --version', { stdio: 'ignore' });
      return 'py';
    } catch {}
    return 'python';
  }
  return 'python3';
}

function isRunning(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function getDaemonPid() {
  if (fs.existsSync(PID_FILE)) {
    try {
      const pid = parseInt(fs.readFileSync(PID_FILE, 'utf-8').trim(), 10);
      if (isRunning(pid)) return pid;
    } catch {}
  }
  return null;
}

function startDaemon() {
  const daemonScript = path.join(PLUGIN_TARGET, 'scripts', 'discord_rpc_daemon.py');
  if (!fs.existsSync(daemonScript)) {
    console.error(`❌ Daemon script not found at ${daemonScript}`);
    return;
  }
  const pid = getDaemonPid();
  if (pid) {
    console.log(`ℹ️  Daemon is already running (PID: ${pid})`);
    return;
  }
  const pyCmd = getPythonCommand();
  const spawnOpts = {
    detached: true,
    stdio: 'ignore'
  };
  if (process.platform === 'win32') {
    spawnOpts.windowsHide = true;
  } else {
    const env = Object.assign({}, process.env);
    if (!env.DISPLAY) env.DISPLAY = ':0';
    if (!env.XAUTHORITY) env.XAUTHORITY = path.join(HOME, '.Xauthority');
    spawnOpts.env = env;
  }

  const child = spawn(pyCmd, [daemonScript], spawnOpts);
  child.unref();
  console.log('🚀 Started Discord RPC daemon in background.');
}

function stopDaemon() {
  const pid = getDaemonPid();
  if (pid) {
    try {
      if (process.platform === 'win32') {
        try { execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' }); } catch {}
      } else {
        process.kill(pid, 'SIGTERM');
      }
      console.log(`🛑 Stopped daemon (PID: ${pid})`);
    } catch (e) {
      console.error(`Error stopping daemon: ${e.message}`);
    }
  } else {
    console.log('ℹ️  Daemon is not currently running.');
  }
}

function checkDiscord() {
  if (process.platform === 'win32') {
    for (let i = 0; i < 10; i++) {
      const pipe = `\\\\.\\pipe\\discord-ipc-${i}`;
      if (fs.existsSync(pipe)) return pipe;
    }
    return null;
  }
  const uid = process.getuid ? process.getuid() : 1000;
  const sockets = [
    `/run/user/${uid}/app/com.discordapp.Discord/discord-ipc-0`,
    `/run/user/${uid}/discord-ipc-0`,
    `/tmp/discord-ipc-0`
  ];
  return sockets.find(s => fs.existsSync(s)) || null;
}

switch (command) {
  case 'install':
  case 'setup': {
    console.log('\n🌟 Installing Antigravity Discord Rich Presence...\n');
    copyRecursive(REPO_ROOT, PLUGIN_TARGET);

    // Adapt hooks.json for Windows if necessary
    if (process.platform === 'win32') {
      const targetHooks = path.join(PLUGIN_TARGET, 'hooks.json');
      if (fs.existsSync(targetHooks)) {
        try {
          const pyCmd = getPythonCommand();
          let content = fs.readFileSync(targetHooks, 'utf-8');
          content = content.replace(/python3/g, pyCmd);
          fs.writeFileSync(targetHooks, content);
        } catch {}
      }
    }

    console.log(`✅ Plugin files installed to:`);
    console.log(`   ${PLUGIN_TARGET}\n`);

    const discSock = checkDiscord();
    if (discSock) {
      console.log(`✅ Discord IPC detected: ${discSock}`);
    } else {
      console.log(`⚠️  Discord is not running right now. Open Discord to see your rich presence.`);
    }

    startDaemon();

    console.log('\n🎉 Installation complete!');
    console.log('✨ Now whenever you open "agy" in any terminal, Discord will show your status automatically.\n');
    break;
  }

  case 'status': {
    console.log('\n📊 Antigravity Discord RPC Status:');
    const pid = getDaemonPid();
    console.log(`   Daemon Running : ${pid ? `Yes (PID: ${pid})` : 'No'}`);
    const sock = checkDiscord();
    console.log(`   Discord Socket : ${sock ? `Connected (${sock})` : 'Not found (Is Discord open?)'}`);
    if (fs.existsSync(STATE_FILE)) {
      try {
        const state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
        console.log(`   Active Sessions:`, Object.keys(state.sessions || {}).length);
      } catch {}
    }
    console.log('');
    break;
  }

  case 'start':
    startDaemon();
    break;

  case 'stop':
    stopDaemon();
    break;

  case 'restart':
    stopDaemon();
    setTimeout(startDaemon, 500);
    break;

  case 'icon': {
    const choice = (args[1] || '').toLowerCase().trim();
    const cfgFile = path.join(CONFIG_DIR, 'discord_rpc_config.json');
    let currentCfg = { client_id: '1552488482918899722', app_name: 'Antigravity', icon: 'antigravity' };
    if (fs.existsSync(cfgFile)) {
      try {
        currentCfg = JSON.parse(fs.readFileSync(cfgFile, 'utf-8'));
      } catch {}
    }

    if (!choice) {
      const currentIcon = currentCfg.icon || 'antigravity';
      console.log(`\n🎨 Current Presence Icon: ${currentIcon.toUpperCase()}`);
      console.log(`Available options:`);
      console.log(`   - antigravity (Official Google Antigravity arch logo)`);
      console.log(`   - gemini      (Google Gemini 4-pointed star)`);
      console.log(`\nUsage: npx agy-rich-presence icon <antigravity|gemini>\n`);
      break;
    }

    if (choice !== 'antigravity' && choice !== 'gemini') {
      console.error(`\n❌ Invalid icon "${choice}". Please choose either "antigravity" or "gemini".\n`);
      break;
    }

    if (!fs.existsSync(CONFIG_DIR)) {
      fs.mkdirSync(CONFIG_DIR, { recursive: true });
    }
    currentCfg.icon = choice;
    fs.writeFileSync(cfgFile, JSON.stringify(currentCfg, null, 2));
    console.log(`\n✅ Presence icon updated to: ${choice.toUpperCase()}`);
    console.log(`✨ The background daemon will hot-reload automatically!\n`);
    break;
  }

  case 'config':
  case 'set': {
    const newClientId = args[1];
    const newAppName = args[2] && !['antigravity', 'gemini'].includes(args[2].toLowerCase()) ? args[2] : undefined;
    const newIcon = [args[2], args[3]].find(a => a && ['antigravity', 'gemini'].includes(a.toLowerCase()));

    if (!newClientId) {
      console.log('\n⚙️  Current Configuration:');
      const cfgFile = path.join(CONFIG_DIR, 'discord_rpc_config.json');
      if (fs.existsSync(cfgFile)) {
        try {
          const cfg = JSON.parse(fs.readFileSync(cfgFile, 'utf-8'));
          console.log(`   Client ID : ${cfg.client_id || 'Default'}`);
          console.log(`   App Name  : ${cfg.app_name || 'Default'}`);
          console.log(`   Icon      : ${cfg.icon || 'antigravity'}`);
        } catch {
          console.log('   (Unable to read config file)');
        }
      } else {
        console.log('   (Using default configuration)');
      }
      console.log('\nUsage: npx agy-rich-presence config <client_id> [app_name] [antigravity|gemini]\n');
      break;
    }

    if (!fs.existsSync(CONFIG_DIR)) {
      fs.mkdirSync(CONFIG_DIR, { recursive: true });
    }
    const cfgFile = path.join(CONFIG_DIR, 'discord_rpc_config.json');
    let currentCfg = { client_id: newClientId, app_name: 'Antigravity', icon: 'antigravity' };
    if (fs.existsSync(cfgFile)) {
      try {
        currentCfg = JSON.parse(fs.readFileSync(cfgFile, 'utf-8'));
      } catch {}
    }
    currentCfg.client_id = newClientId;
    if (newAppName) {
      currentCfg.app_name = newAppName;
    }
    if (newIcon) {
      currentCfg.icon = newIcon.toLowerCase();
    }
    fs.writeFileSync(cfgFile, JSON.stringify(currentCfg, null, 2));
    console.log(`\n✅ Configuration updated:`);
    console.log(`   Client ID : ${currentCfg.client_id}`);
    console.log(`   App Name  : ${currentCfg.app_name}`);
    console.log(`   Icon      : ${currentCfg.icon || 'antigravity'}`);
    console.log(`✨ The background daemon will hot-reload automatically!\n`);
    break;
  }

  case 'uninstall':
    console.log('\n🗑️  Uninstalling Antigravity Discord RPC...');
    stopDaemon();
    if (fs.existsSync(PLUGIN_TARGET)) {
      fs.rmSync(PLUGIN_TARGET, { recursive: true, force: true });
      console.log(`✅ Removed ${PLUGIN_TARGET}`);
    }
    console.log('🎉 Uninstalled successfully.\n');
    break;

  case 'help':
  case '--help':
  default:
    console.log(`
Usage: npx agy-rich-presence [command]

Commands:
  install      Install plugin to ~/.gemini/config/plugins/agy-rich-presence (default)
  status       Check status of daemon and Discord connection
  start        Start background daemon
  stop         Stop background daemon
  restart      Restart background daemon
  icon         Switch presence icon (antigravity or gemini)
  config       View or update client_id, app_name, and icon
  uninstall    Completely remove plugin
    `);
    break;
}
