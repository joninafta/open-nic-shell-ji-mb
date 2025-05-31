#!/usr/bin/env python3
# filepath: /Users/jonafta/Dev/open-nic-shell-ji-mb/tb/tests/filter_rx_pipeline/monitor_ci.py
"""
CI/CD Monitoring and Status Dashboard for Filter RX Pipeline
Provides real-time monitoring of test status, performance trends, and system health
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

# Color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def colored_print(text, color=Colors.WHITE):
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.END}")

class CIMonitor:
    """CI/CD monitoring and dashboard."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results_dir = self.project_root / "results"
        self.config_file = self.project_root / ".ci_config.yml"
        
        # Ensure results directory exists
        self.results_dir.mkdir(exist_ok=True)
    
    def get_git_info(self):
        """Get current git information."""
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                cwd=self.project_root,
                text=True
            ).strip()
            
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                cwd=self.project_root,
                text=True
            ).strip()[:8]
            
            # Check for uncommitted changes
            status = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=self.project_root,
                text=True
            ).strip()
            
            return {
                "branch": branch,
                "commit": commit,
                "clean": len(status) == 0,
                "status": status
            }
        except subprocess.CalledProcessError:
            return {
                "branch": "unknown",
                "commit": "unknown",
                "clean": True,
                "status": ""
            }
    
    def get_test_status(self):
        """Get current test execution status."""
        status = {
            "running": False,
            "last_run": None,
            "results": {},
            "performance": {}
        }
        
        # Check for running tests (look for simulator processes)
        try:
            result = subprocess.run(
                ["pgrep", "-f", "verilator|questa|xcelium"],
                capture_output=True,
                text=True
            )
            status["running"] = result.returncode == 0
        except FileNotFoundError:
            # pgrep not available on all systems
            pass
        
        # Load latest test results
        status_file = self.results_dir / "status.json"
        if status_file.exists():
            try:
                with open(status_file) as f:
                    data = json.load(f)
                    status["last_run"] = data.get("timestamp")
                    status["results"] = data
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Load performance data
        benchmark_file = self.results_dir / "benchmark.json"
        if benchmark_file.exists():
            try:
                with open(benchmark_file) as f:
                    status["performance"] = json.load(f)
            except (json.JSONDecodeError, KeyError):
                pass
        
        return status
    
    def get_log_summary(self):
        """Get summary of recent log files."""
        logs = []
        
        # Find recent log files
        for log_file in self.results_dir.glob("*.log"):
            try:
                stat = log_file.stat()
                logs.append({
                    "name": log_file.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "path": str(log_file)
                })
            except OSError:
                continue
        
        # Sort by modification time (newest first)
        logs.sort(key=lambda x: x["modified"], reverse=True)
        
        return logs[:10]  # Return top 10 most recent logs
    
    def display_header(self):
        """Display dashboard header."""
        print("=" * 80)
        colored_print("🚀 Filter RX Pipeline CI/CD Monitor", Colors.BOLD + Colors.CYAN)
        print("=" * 80)
        
        # Current time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"📅 Current Time: {now}")
        
        # Git information
        git_info = self.get_git_info()
        branch_color = Colors.GREEN if git_info["clean"] else Colors.YELLOW
        colored_print(f"🌿 Branch: {git_info['branch']} ({git_info['commit']})", branch_color)
        
        if not git_info["clean"]:
            colored_print("⚠️  Uncommitted changes detected", Colors.YELLOW)
        
        print()
    
    def display_test_status(self):
        """Display current test status."""
        colored_print("🧪 Test Execution Status", Colors.BOLD + Colors.BLUE)
        print("-" * 40)
        
        status = self.get_test_status()
        
        # Running status
        if status["running"]:
            colored_print("🟢 Status: Tests currently running", Colors.GREEN)
        else:
            colored_print("🔴 Status: No tests running", Colors.RED)
        
        # Last run information
        if status["last_run"]:
            try:
                last_run = datetime.fromisoformat(status["last_run"].replace('Z', '+00:00'))
                time_ago = datetime.now() - last_run.replace(tzinfo=None)
                
                if time_ago.days > 0:
                    time_str = f"{time_ago.days} days ago"
                elif time_ago.seconds > 3600:
                    time_str = f"{time_ago.seconds // 3600} hours ago"
                elif time_ago.seconds > 60:
                    time_str = f"{time_ago.seconds // 60} minutes ago"
                else:
                    time_str = "Just now"
                
                print(f"⏰ Last Run: {time_str}")
            except (ValueError, TypeError):
                print(f"⏰ Last Run: {status['last_run']}")
        else:
            print("⏰ Last Run: Never")
        
        # Test results summary
        if status["results"]:
            test_status = status["results"].get("status", "unknown")
            if test_status == "passing":
                colored_print(f"✅ Result: {test_status.upper()}", Colors.GREEN)
            elif test_status == "failing":
                colored_print(f"❌ Result: {test_status.upper()}", Colors.RED)
            else:
                colored_print(f"❓ Result: {test_status.upper()}", Colors.YELLOW)
            
            # Total tests
            total_tests = status["results"].get("total_tests", 0)
            print(f"📊 Total Tests: {total_tests}")
            
            # Simulator
            simulator = status["results"].get("simulator", "unknown")
            print(f"🔧 Simulator: {simulator}")
        
        print()
    
    def display_performance_metrics(self):
        """Display performance metrics."""
        colored_print("⚡ Performance Metrics", Colors.BOLD + Colors.PURPLE)
        print("-" * 40)
        
        status = self.get_test_status()
        perf = status.get("performance", {})
        
        if not perf:
            colored_print("📊 No performance data available", Colors.YELLOW)
            print()
            return
        
        # Throughput
        if "throughput_gbps" in perf:
            throughput = perf["throughput_gbps"]
            if throughput >= 200:
                color = Colors.GREEN
                indicator = "✅"
            elif throughput >= 150:
                color = Colors.YELLOW
                indicator = "⚠️"
            else:
                color = Colors.RED
                indicator = "❌"
            colored_print(f"{indicator} Throughput: {throughput:.1f} Gbps (target: ≥200)", color)
        
        # Latency
        if "latency_cycles" in perf:
            latency = perf["latency_cycles"]
            if latency <= 5:
                color = Colors.GREEN
                indicator = "✅"
            elif latency <= 10:
                color = Colors.YELLOW
                indicator = "⚠️"
            else:
                color = Colors.RED
                indicator = "❌"
            colored_print(f"{indicator} Latency: {latency} cycles (target: ≤10)", color)
        
        # Packet rate
        if "packet_rate_mpps" in perf:
            packet_rate = perf["packet_rate_mpps"]
            if packet_rate >= 100:
                color = Colors.GREEN
                indicator = "✅"
            elif packet_rate >= 75:
                color = Colors.YELLOW
                indicator = "⚠️"
            else:
                color = Colors.RED
                indicator = "❌"
            colored_print(f"{indicator} Packet Rate: {packet_rate:.1f} Mpps (target: ≥100)", color)
        
        # Timestamp
        if "timestamp" in perf:
            try:
                timestamp = datetime.fromtimestamp(perf["timestamp"])
                print(f"📅 Measured: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            except (ValueError, TypeError):
                pass
        
        print()
    
    def display_log_summary(self):
        """Display recent log files summary."""
        colored_print("📝 Recent Log Files", Colors.BOLD + Colors.WHITE)
        print("-" * 40)
        
        logs = self.get_log_summary()
        
        if not logs:
            colored_print("📂 No log files found", Colors.YELLOW)
            print()
            return
        
        for log in logs[:5]:  # Show top 5
            size_kb = log["size"] / 1024
            time_ago = datetime.now() - log["modified"]
            
            if time_ago.seconds < 300:  # Less than 5 minutes
                time_color = Colors.GREEN
            elif time_ago.seconds < 3600:  # Less than 1 hour
                time_color = Colors.YELLOW
            else:
                time_color = Colors.WHITE
            
            colored_print(f"📄 {log['name']}", Colors.CYAN)
            print(f"   Size: {size_kb:.1f} KB")
            colored_print(f"   Modified: {log['modified'].strftime('%H:%M:%S')}", time_color)
            print()
    
    def display_quick_actions(self):
        """Display available quick actions."""
        colored_print("🎯 Quick Actions", Colors.BOLD + Colors.GREEN)
        print("-" * 40)
        
        actions = [
            ("./run_ci_tests.sh --test-suite quick", "Run quick test suite"),
            ("make test_basic", "Run basic functionality tests"),
            ("make test_performance", "Run performance benchmarks"),
            ("python3 validate_tests.py", "Validate test syntax"),
            ("python3 generate_badges.py", "Update status badges"),
            ("make waves", "View waveforms (if available)"),
        ]
        
        for i, (command, description) in enumerate(actions, 1):
            colored_print(f"{i}. {description}", Colors.WHITE)
            colored_print(f"   {command}", Colors.CYAN)
            print()
    
    def run_dashboard(self, refresh_interval=5):
        """Run interactive dashboard with auto-refresh."""
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Display dashboard
                self.display_header()
                self.display_test_status()
                self.display_performance_metrics()
                self.display_log_summary()
                self.display_quick_actions()
                
                colored_print(f"🔄 Auto-refresh in {refresh_interval}s (Ctrl+C to exit)", Colors.YELLOW)
                
                # Wait for refresh interval
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n")
            colored_print("👋 Dashboard stopped", Colors.CYAN)
    
    def run_once(self):
        """Run dashboard once (no auto-refresh)."""
        self.display_header()
        self.display_test_status()
        self.display_performance_metrics()
        self.display_log_summary()
        self.display_quick_actions()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Filter RX Pipeline CI/CD Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 monitor_ci.py                    # Run once
  python3 monitor_ci.py --watch            # Auto-refresh dashboard
  python3 monitor_ci.py --watch --interval 10  # Auto-refresh every 10 seconds
        """
    )
    
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Run with auto-refresh (interactive mode)"
    )
    
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=5,
        help="Refresh interval in seconds (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Create monitor instance
    monitor = CIMonitor()
    
    # Run dashboard
    if args.watch:
        colored_print("🚀 Starting CI/CD Dashboard (auto-refresh mode)", Colors.BOLD + Colors.GREEN)
        print("Press Ctrl+C to exit")
        print()
        time.sleep(2)
        monitor.run_dashboard(args.interval)
    else:
        monitor.run_once()

if __name__ == "__main__":
    main()
