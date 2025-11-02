#!/usr/bin/env python
"""
Simple test script to verify Real ADK implementation
Run this to check if everything is working correctly
"""

import sys
import os
from pathlib import Path

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_header(msg):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{msg}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def test_imports():
    """Test 1: Check if all imports work"""
    print_header("TEST 1: Checking Imports")

    try:
        print_info("Importing google.adk...")
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        print_success("Google ADK imports successful")
    except ImportError as e:
        print_error(f"Google ADK import failed: {e}")
        print_info("Fix: pip install google-adk")
        return False

    try:
        print_info("Importing config...")
        from config import ADKConfig
        print_success("Config import successful")
    except ImportError as e:
        print_error(f"Config import failed: {e}")
        return False

    try:
        print_info("Importing tools...")
        from tools import (
            upload_to_gcs,
            parse_document_with_docai,
            analyze_with_gemini,
            compare_benchmarks,
            generate_evaluation_report
        )
        print_success("All 5 main tools imported successfully")
    except ImportError as e:
        print_error(f"Tools import failed: {e}")
        return False

    try:
        print_info("Importing agents...")
        from agents import get_startup_eval_agent, list_agent_capabilities
        print_success("Agent imports successful")
    except ImportError as e:
        print_error(f"Agents import failed: {e}")
        return False

    return True


def test_configuration():
    """Test 2: Check configuration"""
    print_header("TEST 2: Checking Configuration")

    try:
        from config import ADKConfig

        config = ADKConfig.to_dict()
        print_info(f"Configuration loaded:")
        for key, value in config.items():
            if 'configured' in key:
                status = "✓" if value else "✗"
                print(f"  {status} {key}: {value}")
            else:
                print(f"    {key}: {value}")

        # Validate required fields
        is_valid, error = ADKConfig.validate()
        if is_valid:
            print_success("Configuration is valid")
            return True
        else:
            print_error(f"Configuration validation failed: {error}")
            print_info("Check your .env file")
            return False

    except Exception as e:
        print_error(f"Configuration check failed: {e}")
        return False


def test_agent_creation():
    """Test 3: Create agents"""
    print_header("TEST 3: Creating Agents")

    try:
        print_info("Creating startup evaluation agent...")
        from agents import get_startup_eval_agent, list_agent_capabilities

        agent = get_startup_eval_agent()
        print_success(f"Root agent created: {agent.name}")

        # Check sub-agents
        if hasattr(agent, 'sub_agents') and agent.sub_agents:
            print_success(f"Sub-agents loaded: {len(agent.sub_agents)} agents")
            for sub_agent in agent.sub_agents:
                print(f"    - {sub_agent.name}")
        else:
            print_warning("No sub-agents found")

        # List capabilities
        print_info("Checking agent capabilities...")
        capabilities = list_agent_capabilities()

        agent_count = len(capabilities)
        print_success(f"{agent_count} agent types registered")

        tool_count = sum(len(agent.get('tools', [])) for agent in capabilities.values())
        print_success(f"{tool_count} tools available")

        return True

    except Exception as e:
        print_error(f"Agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gemini_api():
    """Test 4: Test Gemini API"""
    print_header("TEST 4: Testing Gemini API")

    try:
        print_info("Testing Gemini API connection...")
        import google.generativeai as genai
        from config import ADKConfig

        if not ADKConfig.GEMINI_API_KEY:
            print_error("GEMINI_API_KEY not configured")
            return False

        genai.configure(api_key=ADKConfig.GEMINI_API_KEY)
        model = genai.GenerativeModel(ADKConfig.MODEL_NAME)

        print_info(f"Sending test request to {ADKConfig.MODEL_NAME}...")
        response = model.generate_content("Say 'Hello, ADK!'")

        if response.text:
            print_success(f"Gemini API working!")
            print(f"    Response: {response.text[:100]}...")
            return True
        else:
            print_error("Gemini API returned empty response")
            return False

    except Exception as e:
        print_error(f"Gemini API test failed: {e}")
        print_info("Check your GEMINI_API_KEY in .env")
        return False


def test_runner():
    """Test 5: Test ADK Runner"""
    print_header("TEST 5: Testing ADK Runner")

    try:
        print_info("Creating ADK Runner...")
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from agents import get_startup_eval_agent

        agent = get_startup_eval_agent()
        session_service = InMemorySessionService()
        runner = Runner(agent=agent, session_service=session_service)

        print_success("Runner created successfully")

        print_info("Testing simple prompt...")
        response = runner.run(
            user_id="test_user",
            prompt="Explain what you do in one sentence."
        )

        if response:
            print_success("Runner executed successfully")
            print(f"    Session ID: {response.session.session_id if hasattr(response, 'session') else 'N/A'}")
            return True
        else:
            print_error("Runner returned no response")
            return False

    except Exception as e:
        print_error(f"Runner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_handling():
    """Test 6: Test file handling"""
    print_header("TEST 6: Testing File Handling")

    try:
        print_info("Creating test file...")
        test_file = Path("test_startup_sample.txt")
        test_file.write_text("""
Company: TestStartup Inc.
Sector: SaaS
Stage: Seed
ARR: $1.2M
MRR: $100K
Customers: 50
Growth Rate: 20% MoM

We are a B2B SaaS platform for small businesses.
Market size is $50B and growing at 15% annually.
        """)

        print_success("Test file created")

        # Test with tools
        print_info("Testing metric extraction...")
        from tools import extract_financial_metrics

        text = test_file.read_text()
        metrics = extract_financial_metrics(text)

        if metrics:
            print_success(f"Extracted {len(metrics)} metrics")
            for key, value in list(metrics.items())[:3]:
                print(f"    - {key}: {value}")

        # Cleanup
        test_file.unlink()
        print_info("Test file cleaned up")

        return True

    except Exception as e:
        print_error(f"File handling test failed: {e}")
        return False


def main():
    """Run all tests"""
    print_header("🧪 Real ADK Implementation Test Suite")
    print_info("This will test if your ADK implementation is working correctly\n")

    results = []

    # Run all tests
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_configuration()))
    results.append(("Agent Creation", test_agent_creation()))
    results.append(("Gemini API", test_gemini_api()))
    results.append(("ADK Runner", test_runner()))
    results.append(("File Handling", test_file_handling()))

    # Summary
    print_header("📊 Test Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status}  {test_name}")

    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}\n")

    if passed == total:
        print_success("🎉 All tests passed! Your ADK implementation is working correctly!")
        print_info("\nNext steps:")
        print("  1. Start the server: python -m real_adk.app --mode server")
        print("  2. Test the API: curl http://localhost:8080/api/adk/health")
        print("  3. Try evaluation: curl -X POST http://localhost:8080/api/adk/evaluate -F 'files=@your_doc.pdf'")
        return 0
    else:
        print_error(f"⚠️  {total - passed} test(s) failed. Check the errors above.")
        print_info("\nCommon fixes:")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Configuration: Check your .env file")
        print("  - API keys: Verify GEMINI_API_KEY at https://makersuite.google.com/")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}⚠️  Test interrupted{RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
