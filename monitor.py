#!/usr/bin/env python3

import json
import time
import os
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_progress():
    """Display current bot progress"""
    try:
        results_dir = Path("results")
        
        # Find the most recent results and summary files
        if not results_dir.exists():
            print(f"{Fore.YELLOW}⏳ Waiting for bot to start...")
            print(f"{Fore.CYAN}Results directory: {results_dir.absolute()}")
            return
        
        # Get the most recent results and summary files
        result_files = list(results_dir.glob("session_results_*.json"))
        summary_files = list(results_dir.glob("session_summary_*.json"))
        
        if not result_files:
            print(f"{Fore.YELLOW}⏳ Waiting for bot to start...")
            print(f"{Fore.CYAN}Results directory: {results_dir.absolute()}")
            return
        
        # Get the most recent files
        latest_results_file = max(result_files, key=lambda x: x.stat().st_mtime)
        latest_summary_file = max(summary_files, key=lambda x: x.stat().st_mtime) if summary_files else None
        
        # Load summary data
        if latest_summary_file and latest_summary_file.exists():
            with open(latest_summary_file, 'r') as f:
                summary = json.load(f)
        else:
            return
        
        # Load full results for recent activity
        with open(latest_results_file, 'r') as f:
            all_results = json.load(f)
        
        # Display header
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
        print(f"{Fore.GREEN}{Style.BRIGHT}🤖 WEB AUTOMATION BOT - LIVE PROGRESS")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
        print(f"{Fore.WHITE}Monitoring: {Fore.CYAN}{latest_results_file.name}")
        print(f"{Fore.WHITE}Summary: {Fore.CYAN}{latest_summary_file.name if latest_summary_file else 'N/A'}")
        
        # Display summary stats
        print(f"\n{Fore.YELLOW}📊 SUMMARY STATISTICS")
        print(f"{Fore.WHITE}Total Sessions Completed: {Fore.GREEN}{summary['total_sessions_completed']}")
        print(f"{Fore.WHITE}Successful Sessions: {Fore.GREEN}{summary['successful_sessions']}")
        print(f"{Fore.WHITE}Failed Sessions: {Fore.RED}{summary['failed_sessions']}")
        print(f"{Fore.WHITE}Success Rate: {Fore.CYAN}{summary['success_rate_percent']}%")
        print(f"{Fore.WHITE}Last Updated: {Fore.YELLOW}{summary['last_updated']}")
        
        # Display latest session
        if 'latest_session' in summary:
            latest = summary['latest_session']
            print(f"\n{Fore.YELLOW}🎯 LATEST SESSION")
            print(f"{Fore.WHITE}Session: {Fore.CYAN}{latest['session_number']}/{latest['total_sessions']}")
            print(f"{Fore.WHITE}Browser: {Fore.MAGENTA}{latest['browser'].title()}")
            print(f"{Fore.WHITE}IP: {Fore.BLUE}{latest['ip_address']}")
            print(f"{Fore.WHITE}Location: {Fore.BLUE}{latest['ip_location']}")
            print(f"{Fore.WHITE}Route: {Fore.MAGENTA}{latest['web_route'].title()}")
            print(f"{Fore.WHITE}Time on Site: {Fore.GREEN}{latest['time_on_target_url']}s")
            print(f"{Fore.WHITE}Clicks: {Fore.GREEN}{latest['clicks']}")
            
            status_color = Fore.GREEN if latest['success'] else Fore.RED
            status_text = "✅ SUCCESS" if latest['success'] else f"❌ FAILED: {latest['failure_reason']}"
            print(f"{Fore.WHITE}Status: {status_color}{status_text}")
        
        # Display recent activity (last 5 sessions)
        print(f"\n{Fore.YELLOW}📋 RECENT ACTIVITY (Last 5 Sessions)")
        print(f"{Fore.CYAN}{'Session':<8} {'Browser':<8} {'Route':<8} {'Status':<10} {'Time':<8}")
        print(f"{Fore.CYAN}{'-'*50}")
        
        recent_sessions = all_results[-5:] if len(all_results) >= 5 else all_results
        for session in recent_sessions:
            session_num = f"{session['session_number']:03d}"
            browser = session['browser'][:7]
            route = session['web_route'][:7]
            status = "✅ PASS" if session['success'] else "❌ FAIL"
            time_str = f"{session['time_on_target_url']:.1f}s"
            
            status_color = Fore.GREEN if session['success'] else Fore.RED
            print(f"{Fore.WHITE}{session_num:<8} {browser:<8} {route:<8} {status_color}{status:<10} {Fore.WHITE}{time_str:<8}")
        
        # Display browser distribution
        if all_results:
            browsers = {}
            routes = {}
            for session in all_results:
                browser = session['browser']
                route = session['web_route']
                browsers[browser] = browsers.get(browser, 0) + 1
                routes[route] = routes.get(route, 0) + 1
            
            print(f"\n{Fore.YELLOW}🌐 BROWSER DISTRIBUTION")
            for browser, count in browsers.items():
                percentage = (count / len(all_results)) * 100
                print(f"{Fore.WHITE}{browser.title()}: {Fore.CYAN}{count} sessions ({percentage:.1f}%)")
            
            print(f"\n{Fore.YELLOW}🔍 ROUTE DISTRIBUTION")
            for route, count in routes.items():
                percentage = (count / len(all_results)) * 100
                print(f"{Fore.WHITE}{route.title()}: {Fore.CYAN}{count} sessions ({percentage:.1f}%)")
        
        # Progress bar
        if 'latest_session' in summary:
            current = summary['latest_session']['session_number']
            total = summary['latest_session']['total_sessions']
            progress = (current / total) * 100
            
            print(f"\n{Fore.YELLOW}📈 DAILY PROGRESS")
            bar_length = 40
            filled_length = int(bar_length * current // total)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            print(f"{Fore.WHITE}Progress: {Fore.CYAN}[{bar}] {progress:.1f}% ({current}/{total})")
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}⟳ Refreshing every 10 seconds... (Ctrl+C to exit)")
        
    except FileNotFoundError:
        print(f"{Fore.YELLOW}⏳ Waiting for bot to create results file...")
    except json.JSONDecodeError:
        print(f"{Fore.RED}❌ Error reading results file (may be corrupted)")
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}")

def main():
    """Main monitoring loop"""
    print(f"{Fore.GREEN}🔍 Bot Progress Monitor Starting...")
    print(f"{Fore.YELLOW}Monitoring: {Path('session_results.json').absolute()}")
    print(f"{Fore.CYAN}Press Ctrl+C to exit\n")
    
    try:
        while True:
            clear_screen()
            display_progress()
            time.sleep(10)  # Refresh every 10 seconds
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Monitor stopped by user")
    except Exception as e:
        print(f"\n{Fore.RED}Monitor error: {e}")

if __name__ == "__main__":
    main()
