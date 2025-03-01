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


def node_up(with_bds=False):
    """Start the node"""
    cwd = os.getcwd()
    logger.info("Starting Xian node...")

    if with_bds:
        logger.info("Starting with BDS (Blockchain Data Service)...")
        # Find the simulator path dynamically
        try:
            import xian.services
            simulator_path = os.path.join(os.path.dirname(xian.services.__file__), 'simulator.py')

            # Start the simulator
            run_command(f'pm2 start "{sys.executable} {simulator_path}" --name simulator -f --wait-ready')

        except ImportError:
            logger.error("Could not import xian.services module")
            return False

    # Start Xian ABCI
    run_command(f'cd {cwd}/src/xian && pm2 start xian_abci.py --name xian -f')

    # Start CometBFT
    run_command(f'cd {cwd} && pm2 start "cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft -f')

    logger.info("Node started. Use 'xian logs' to view logs.")
    return True


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
                    Options: 
                      --bds    Start with Blockchain Data Service
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

    if command == 'up':
        # Check for --bds flag
        with_bds = '--bds' in sys.argv
        node_up(with_bds)
        return

    commands = {
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


if __name__ == '__main__':
    main()