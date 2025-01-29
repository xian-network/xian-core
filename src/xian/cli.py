import os
import subprocess
import sys
from loguru import logger

def run_command(command):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        return False

def node_up():
    """Start the node"""
    cwd = os.getcwd()
    logger.info("Starting Xian node...")
    run_command(f'cd {cwd} && pm2 start "python -m xian.xian_abci" --name xian -f')
    run_command(f'cd {cwd} && pm2 start "cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft -f')
    logger.info("Node started. Use 'xian logs' to view logs.")

def node_down():
    """Stop the node"""
    logger.info("Stopping all services...")
    run_command("pm2 delete all")

def show_logs():
    """Show node logs"""
    run_command("pm2 logs")

def init_node():
    """Initialize the node"""
    logger.info("Initializing CometBFT...")
    run_command("cometbft init")

def get_node_id():
    """Get node ID"""
    run_command("cometbft show-node-id")

def wipe_data():
    """Wipe blockchain data"""
    logger.info("Wiping blockchain data...")
    run_command("rm -rf ~/.cometbft/xian")
    run_command("cometbft unsafe-reset-all")

def help():
    """Show help message"""
    print("""
Xian Node Management Commands:
    up          Start the node
    down        Stop the node
    logs        View node logs
    init        Initialize the node
    node-id     Show node ID
    wipe        Wipe blockchain data
    help        Show this help message
    """)

def main():
    if len(sys.argv) < 2 or sys.argv[1] == 'help':
        help()
        return

    command = sys.argv[1]
    
    commands = {
        'up': node_up,
        'down': node_down,
        'logs': show_logs,
        'init': init_node,
        'node-id': get_node_id,
        'wipe': wipe_data,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        help()