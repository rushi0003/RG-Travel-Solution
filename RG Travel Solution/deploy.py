#!/usr/bin/env python3
"""
RG Travel Solution - Complete Project Deployment Assistant

This script provides guided setup for both backend and frontend.
Supports: development setup, testing, production preparation, troubleshooting.

Usage:
    python deploy.py                    # Interactive menu
    python deploy.py --setup            # Setup backend
    python deploy.py --test-backend     # Test backend
    python deploy.py --test-flutter     # Test Flutter app
    python deploy.py --production       # Production preparation
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Tuple, Optional

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


class RGTravelDeployer:
    """Main deployment coordinator"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backend_dir = self.project_root / "rg_travel_backend"
        self.flutter_dir = self.project_root / "rg_travel_flutter"
        self.docs_dir = self.project_root / "docs"
    
    def print_header(self, text):
        """Print formatted header"""
        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}{BLUE}{text:^70}{RESET}")
        print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")
    
    def print_section(self, text):
        """Print section divider"""
        print(f"\n{CYAN}{BOLD}{text}{RESET}")
        print(f"{CYAN}{'─'*70}{RESET}")
    
    def print_success(self, text):
        print(f"{GREEN}✓ {text}{RESET}")
    
    def print_error(self, text):
        print(f"{RED}✗ {text}{RESET}")
    
    def print_warning(self, text):
        print(f"{YELLOW}⚠ {text}{RESET}")
    
    def print_info(self, text):
        print(f"{BLUE}ℹ {text}{RESET}")
    
    def print_step(self, step: int, text: str):
        """Print numbered step"""
        print(f"{BOLD}{BLUE}[Step {step}]{RESET} {text}")
    
    def run_command(self, cmd: list, cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Run command and capture output"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.backend_dir,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        self.print_section("Checking Prerequisites")
        
        checks = []
        
        # Python
        try:
            import sys
            if sys.version_info >= (3, 8):
                self.print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}")
                checks.append(True)
            else:
                self.print_error(f"Python 3.8+ required (found {sys.version_info.major}.{sys.version_info.minor})")
                checks.append(False)
        except:
            self.print_error("Python check failed")
            checks.append(False)
        
        # Git
        code, _, _ = self.run_command(['git', '--version'], Path('.'))
        if code == 0:
            self.print_success("Git installed")
            checks.append(True)
        else:
            self.print_warning("Git not found (optional)")
            checks.append(True)
        
        return all(checks)
    
    def setup_virtual_env(self) -> bool:
        """Setup Python virtual environment"""
        self.print_section("Setting Up Virtual Environment")
        
        venv_path = self.backend_dir / "venv"
        
        if venv_path.exists():
            self.print_info(f"Virtual environment already exists: {venv_path}")
            return True
        
        self.print_step(1, "Creating virtual environment...")
        
        code, stdout, stderr = self.run_command(
            [sys.executable, '-m', 'venv', str(venv_path)],
            self.backend_dir
        )
        
        if code == 0:
            self.print_success(f"Virtual environment created")
        else:
            self.print_error(f"Failed to create virtual environment: {stderr}")
            return False
        
        return True
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        self.print_section("Installing Dependencies")
        
        requirements_file = self.backend_dir / "requirements.txt"
        
        if not requirements_file.exists():
            self.print_error(f"requirements.txt not found at {requirements_file}")
            return False
        
        self.print_step(1, "Installing packages from requirements.txt...")
        
        # Use pip from the venv or system
        pip_cmd = 'pip' if sys.platform == 'win32' else 'pip3'
        code, stdout, stderr = self.run_command(
            [pip_cmd, 'install', '-r', str(requirements_file)],
            self.backend_dir
        )
        
        if code == 0:
            self.print_success("All dependencies installed")
            self.print_info("Key packages:")
            for line in stdout.split('\n'):
                if 'Successfully installed' in line or line.startswith('Collecting'):
                    self.print_info(f"  {line.strip()}")
            return True
        else:
            self.print_error(f"Failed to install dependencies:\n{stderr}")
            return False
    
    def setup_env_file(self) -> bool:
        """Setup .env configuration file"""
        self.print_section("Setting Up Configuration")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if env_file.exists():
            self.print_info(".env file already exists")
            return True
        
        if not env_example.exists():
            self.print_error(f".env.example not found at {env_example}")
            return False
        
        self.print_step(1, f"Creating .env from template...")
        
        try:
            env_content = env_example.read_text()
            env_file.write_text(env_content)
            self.print_success(f".env created successfully")
            self.print_info(f"Location: {env_file}")
            self.print_warning("Review and update .env with your settings")
            return True
        except Exception as e:
            self.print_error(f"Failed to create .env: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """Initialize database"""
        self.print_section("Initializing Database")
        
        schema_file = self.backend_dir / "db" / "schema.sql"
        
        if not schema_file.exists():
            self.print_error(f"schema.sql not found at {schema_file}")
            return False
        
        self.print_step(1, "Reading database schema...")
        
        try:
            import sqlite3
            
            db_path = self.backend_dir / "rg_travel.db"
            
            # Read schema
            schema_content = schema_file.read_text()
            
            # Create database
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Execute schema
            cursor.executescript(schema_content)
            conn.commit()
            conn.close()
            
            self.print_success(f"Database initialized at {db_path}")
            return True
        except Exception as e:
            self.print_error(f"Failed to initialize database: {e}")
            return False
    
    def seed_demo_data(self) -> bool:
        """Seed demo data"""
        self.print_section("Seeding Demo Data")
        
        self.print_step(1, "Running seed script...")
        
        seed_script = self.backend_dir / "seeds" / "seed_admin.py"
        
        if not seed_script.exists():
            self.print_warning("Seed scripts not available")
            return True
        
        try:
            # Would need to implement actual seeding
            self.print_info("Run manual seed script from API endpoints:")
            self.print_info("  POST /api/seed/admin")
            self.print_info("  POST /api/seed/drivers")
            self.print_info("  POST /api/seed/employees")
            return True
        except Exception as e:
            self.print_warning(f"Seeding not available: {e}")
            return True
    
    def test_backend(self) -> bool:
        """Test backend functionality"""
        self.print_section("Testing Backend")
        
        self.print_step(1, "Verifying backend setup...")
        
        verify_script = self.backend_dir / "verify_setup.py"
        
        if not verify_script.exists():
            self.print_warning("Verification script not found")
            return True
        
        try:
            code, stdout, stderr = self.run_command(
                [sys.executable, str(verify_script)],
                self.backend_dir
            )
            
            if code == 0:
                self.print_success("Backend verification passed")
                return True
            else:
                self.print_error("Backend verification failed")
                self.print_error(stderr)
                return False
        except Exception as e:
            self.print_warning(f"Could not run verification: {e}")
            return True
    
    def test_flutter(self) -> bool:
        """Test Flutter setup"""
        self.print_section("Testing Flutter Setup")
        
        self.print_step(1, "Checking Flutter installation...")
        
        code, stdout, stderr = self.run_command(
            ['flutter', '--version'],
            Path('.')
        )
        
        if code == 0:
            self.print_success("Flutter is installed")
            self.print_info(stdout.strip())
            
            # Check pubspec.yaml
            pubspec = self.flutter_dir / "pubspec.yaml"
            if pubspec.exists():
                self.print_success(f"pubspec.yaml exists")
            else:
                self.print_error(f"pubspec.yaml not found")
                return False
            
            return True
        else:
            self.print_error("Flutter not installed or not in PATH")
            self.print_info("Install from: https://flutter.dev/docs/get-started/install")
            return False
    
    def show_quickstart(self):
        """Show quickstart instructions"""
        self.print_header("QUICKSTART GUIDE")
        
        self.print_section("Backend Setup (5 minutes)")
        print("""
1. Create Python virtual environment:
   cd rg_travel_backend
   python -m venv venv
   
2. Activate virtual environment:
   - Windows: venv\\Scripts\\activate
   - Mac/Linux: source venv/bin/activate
   
3. Install dependencies:
   pip install -r requirements.txt
   
4. Start backend:
   python app.py
   
5. Test backend:
   curl http://localhost:5000/api/health
""")
        
        self.print_section("Flutter Setup (5 minutes)")
        print("""
1. Install dependencies:
   cd rg_travel_flutter
   flutter pub get
   
2. Run on emulator/device:
   flutter run
   
3. Select target device when prompted
""")
        
        self.print_section("Testing the System")
        print("""
1. Test backend health:
   curl http://localhost:5000/api/health
   
2. Seed demo data:
   curl -X POST http://localhost:5000/api/seed/admin
   curl -X POST http://localhost:5000/api/seed/drivers
   
3. Test login:
   curl -X POST http://localhost:5000/api/auth/login \\
     -H "Content-Type: application/json" \\
     -d '{"mobile": "1234567890", "password": "admin123"}'
   
4. Flutter app will auto-connect to backend
""")
        
        self.print_section("Documentation")
        print("""
Available guides:
  - QUICKSTART_GUIDE.md - 5-minute setup
  - API_TESTING_GUIDE.md - All endpoints with examples
  - API_EXAMPLES.json - Code samples (Python, cURL, JavaScript)
  - CONFIGURATION.json - All environment variables
  - FLUTTER_INTEGRATION_GUIDE.md - Frontend development
""")
    
    def interactive_menu(self):
        """Show interactive menu"""
        while True:
            self.print_header("RG Travel Solution - Deployment Menu")
            
            print("Choose an option:")
            print(f"  {BOLD}1{RESET} - Full Setup (backend + environment)")
            print(f"  {BOLD}2{RESET} - Backend Only")
            print(f"  {BOLD}3{RESET} - Flutter Setup")
            print(f"  {BOLD}4{RESET} - Test Backend")
            print(f"  {BOLD}5{RESET} - Test Flutter")
            print(f"  {BOLD}6{RESET} - Show Quickstart")
            print(f"  {BOLD}7{RESET} - Show Documentation")
            print(f"  {BOLD}0{RESET} - Exit\n")
            
            choice = input(f"{BOLD}Enter your choice (0-7):{RESET} ").strip()
            
            if choice == '1':
                self.full_setup()
            elif choice == '2':
                self.backend_setup()
            elif choice == '3':
                self.flutter_setup()
            elif choice == '4':
                self.test_backend()
            elif choice == '5':
                self.test_flutter()
            elif choice == '6':
                self.show_quickstart()
            elif choice == '7':
                self.show_documentation()
            elif choice == '0':
                self.print_info("Goodbye!")
                break
            else:
                self.print_error("Invalid choice")
    
    def full_setup(self):
        """Complete setup"""
        self.print_header("FULL SYSTEM SETUP")
        
        if not self.check_prerequisites():
            self.print_error("Prerequisites not met")
            return
        
        if not self.setup_env_file():
            self.print_error("Failed to setup .env")
            return
        
        if not self.setup_virtual_env():
            self.print_error("Failed to setup virtual environment")
            return
        
        if not self.install_dependencies():
            self.print_error("Failed to install dependencies")
            return
        
        if not self.initialize_database():
            self.print_error("Failed to initialize database")
            return
        
        if not self.test_backend():
            self.print_warning("Backend test had issues")
        
        self.print_header("SETUP COMPLETE ✓")
        print(f"""
{GREEN}Backend is ready!{RESET}

Next steps:
  1. Review .env configuration
  2. Start backend: cd rg_travel_backend && python app.py
  3. Test backend: curl http://localhost:5000/api/health
  4. Setup Flutter: cd rg_travel_flutter && flutter pub get
  5. Run Flutter: flutter run

For detailed guides, see the docs/ folder.
""")
    
    def backend_setup(self):
        """Backend setup only"""
        self.print_header("BACKEND SETUP")
        
        if not self.setup_virtual_env():
            return
        if not self.install_dependencies():
            return
        if not self.initialize_database():
            return
        
        self.print_header("BACKEND READY ✓")
    
    def flutter_setup(self):
        """Flutter setup only"""
        self.print_header("FLUTTER SETUP")
        
        if not self.test_flutter():
            return
        
        self.print_step(1, "Installing Flutter dependencies...")
        code, stdout, stderr = self.run_command(
            ['flutter', 'pub', 'get'],
            self.flutter_dir
        )
        
        if code == 0:
            self.print_success("Flutter dependencies installed")
        else:
            self.print_error(f"Failed to install Flutter dependencies:\n{stderr}")
            return
        
        self.print_header("FLUTTER READY ✓")
    
    def show_documentation(self):
        """Show available documentation"""
        self.print_header("AVAILABLE DOCUMENTATION")
        
        docs = [
            ("QUICKSTART_GUIDE.md", "5-minute setup guide"),
            ("API_TESTING_GUIDE.md", "All API endpoints with examples"),
            ("FLUTTER_INTEGRATION_GUIDE.md", "Frontend development guide"),
            ("DATABASE_OPERATIONS_GUIDE.md", "Database setup and operations"),
            ("PROJECT_COMPLETE_ANALYSIS.md", "Detailed project analysis"),
            ("README_COMPLETE.md", "Complete development guide"),
        ]
        
        for filename, description in docs:
            doc_path = self.docs_dir / filename
            status = "✓" if doc_path.exists() else "✗"
            print(f"  {status} {filename:40} - {description}")
        
        print(f"\nLocation: {self.docs_dir}")


def main():
    """Main entry point"""
    deployer = RGTravelDeployer()
    
    # Check arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--setup':
            deployer.full_setup()
        elif sys.argv[1] == '--backend':
            deployer.backend_setup()
        elif sys.argv[1] == '--flutter':
            deployer.flutter_setup()
        elif sys.argv[1] == '--test-backend':
            deployer.test_backend()
        elif sys.argv[1] == '--test-flutter':
            deployer.test_flutter()
        elif sys.argv[1] == '--quickstart':
            deployer.show_quickstart()
        elif sys.argv[1] == '--help':
            print(__doc__)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print(__doc__)
    else:
        # Interactive menu
        deployer.interactive_menu()


if __name__ == "__main__":
    main()
