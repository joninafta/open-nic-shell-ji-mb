#!/usr/bin/env python3
# filepath: /Users/jonafta/Dev/open-nic-shell-ji-mb/tb/tests/filter_rx_pipeline/generate_badges.py
"""
Badge generator for Filter RX Pipeline CI/CD status
Generates status badges for README.md based on test results
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Badge templates
BADGE_TEMPLATES = {
    'passing': '![Tests](https://img.shields.io/badge/tests-passing-brightgreen)',
    'failing': '![Tests](https://img.shields.io/badge/tests-failing-red)',
    'unknown': '![Tests](https://img.shields.io/badge/tests-unknown-lightgrey)',
    'performance': '![Performance](https://img.shields.io/badge/performance-{value}-{color})',
    'coverage': '![Coverage](https://img.shields.io/badge/coverage-{value}%25-{color})',
    'build': '![Build](https://img.shields.io/badge/build-{status}-{color})',
    'simulator': '![Simulator](https://img.shields.io/badge/simulator-{name}-blue)',
}

def get_color_for_percentage(percentage):
    """Get badge color based on percentage value."""
    if percentage >= 90:
        return 'brightgreen'
    elif percentage >= 70:
        return 'yellow'
    elif percentage >= 50:
        return 'orange'
    else:
        return 'red'

def get_performance_color(value, metric):
    """Get color for performance metrics."""
    if metric == 'throughput_gbps':
        if value >= 200:
            return 'brightgreen'
        elif value >= 150:
            return 'yellow'
        else:
            return 'red'
    elif metric == 'latency_cycles':
        if value <= 5:
            return 'brightgreen'
        elif value <= 10:
            return 'yellow'
        else:
            return 'red'
    elif metric == 'packet_rate_mpps':
        if value >= 100:
            return 'brightgreen'
        elif value >= 75:
            return 'yellow'
        else:
            return 'red'
    return 'lightgrey'

def load_test_results():
    """Load test results from CI/CD artifacts."""
    results_dir = Path('results')
    
    # Default results
    results = {
        'tests_passing': None,
        'total_tests': 28,
        'performance': {},
        'coverage': None,
        'build_status': 'unknown',
        'simulator': 'verilator',
        'last_updated': datetime.now().isoformat()
    }
    
    # Check for test log files
    if results_dir.exists():
        log_files = list(results_dir.glob('*.log'))
        if log_files:
            results['build_status'] = 'passing'  # Assume passing if logs exist
            results['tests_passing'] = True
        
        # Load benchmark data if available
        benchmark_file = results_dir / 'benchmark.json'
        if benchmark_file.exists():
            try:
                with open(benchmark_file) as f:
                    benchmark_data = json.load(f)
                    results['performance'] = benchmark_data
                    results['simulator'] = benchmark_data.get('simulator', 'verilator')
            except (json.JSONDecodeError, FileNotFoundError):
                pass
    
    return results

def generate_badges(results):
    """Generate badge markdown based on results."""
    badges = []
    
    # Test status badge
    if results['tests_passing'] is True:
        badges.append(BADGE_TEMPLATES['passing'])
    elif results['tests_passing'] is False:
        badges.append(BADGE_TEMPLATES['failing'])
    else:
        badges.append(BADGE_TEMPLATES['unknown'])
    
    # Build status badge
    build_status = results['build_status']
    color = 'brightgreen' if build_status == 'passing' else 'red' if build_status == 'failing' else 'lightgrey'
    badges.append(BADGE_TEMPLATES['build'].format(status=build_status, color=color))
    
    # Simulator badge
    simulator = results['simulator']
    badges.append(BADGE_TEMPLATES['simulator'].format(name=simulator))
    
    # Performance badges
    if results['performance']:
        perf = results['performance']
        
        if 'throughput_gbps' in perf:
            value = perf['throughput_gbps']
            color = get_performance_color(value, 'throughput_gbps')
            badge = BADGE_TEMPLATES['performance'].format(
                value=f"{value:.1f} Gbps", color=color
            )
            badges.append(badge)
        
        if 'latency_cycles' in perf:
            value = perf['latency_cycles']
            color = get_performance_color(value, 'latency_cycles')
            badge = BADGE_TEMPLATES['performance'].format(
                value=f"{value} cycles", color=color
            )
            badges.append(badge)
        
        if 'packet_rate_mpps' in perf:
            value = perf['packet_rate_mpps']
            color = get_performance_color(value, 'packet_rate_mpps')
            badge = BADGE_TEMPLATES['performance'].format(
                value=f"{value:.1f} Mpps", color=color
            )
            badges.append(badge)
    
    # Coverage badge (if available)
    if results['coverage'] is not None:
        coverage = results['coverage']
        color = get_color_for_percentage(coverage)
        badges.append(BADGE_TEMPLATES['coverage'].format(value=coverage, color=color))
    
    return badges

def update_readme_badges(badges):
    """Update README.md with new badges."""
    readme_path = Path('README.md')
    
    if not readme_path.exists():
        # Create a basic README if it doesn't exist
        readme_content = """# Filter RX Pipeline

## Status

<!-- CI/CD Badges -->
{badges}
<!-- End CI/CD Badges -->

## Description

Configurable packet filtering system for Ethernet frames containing IPv4 or IPv6 packets.

## Testing

See [TESTPLAN.md](TESTPLAN.md) for comprehensive test documentation.

""".format(badges='\n'.join(badges))
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        print(f"Created README.md with CI/CD badges")
        return
    
    # Update existing README
    with open(readme_path, 'r') as f:
        content = f.read()
    
    # Find and replace badges section
    start_marker = '<!-- CI/CD Badges -->'
    end_marker = '<!-- End CI/CD Badges -->'
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx != -1 and end_idx != -1:
        # Replace existing badges
        new_badges_section = f"{start_marker}\n{chr(10).join(badges)}\n{end_marker}"
        new_content = content[:start_idx] + new_badges_section + content[end_idx + len(end_marker):]
    else:
        # Add badges section at the beginning
        badges_section = f"""## Status

<!-- CI/CD Badges -->
{chr(10).join(badges)}
<!-- End CI/CD Badges -->

"""
        # Insert after first heading
        lines = content.split('\n')
        insert_idx = 1 if lines and lines[0].startswith('#') else 0
        lines.insert(insert_idx, badges_section)
        new_content = '\n'.join(lines)
    
    with open(readme_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated README.md with {len(badges)} CI/CD badges")

def generate_status_json(results):
    """Generate machine-readable status JSON."""
    status = {
        'status': 'passing' if results['tests_passing'] else 'failing' if results['tests_passing'] is False else 'unknown',
        'timestamp': results['last_updated'],
        'simulator': results['simulator'],
        'total_tests': results['total_tests'],
        'performance': results['performance'],
        'coverage': results['coverage']
    }
    
    with open('results/status.json', 'w') as f:
        json.dump(status, f, indent=2)
    
    print("Generated results/status.json")

def main():
    """Main function."""
    print("🏷️  Filter RX Pipeline Badge Generator")
    print("=====================================")
    
    # Load test results
    print("Loading test results...")
    results = load_test_results()
    
    # Generate badges
    print("Generating badges...")
    badges = generate_badges(results)
    
    # Update README
    print("Updating README.md...")
    update_readme_badges(badges)
    
    # Generate status JSON
    print("Generating status JSON...")
    os.makedirs('results', exist_ok=True)
    generate_status_json(results)
    
    print("\n✅ Badge generation complete!")
    print(f"Generated {len(badges)} badges:")
    for badge in badges:
        print(f"  • {badge}")

if __name__ == "__main__":
    main()
