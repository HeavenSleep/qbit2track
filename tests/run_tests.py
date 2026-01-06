#!/usr/bin/env python3
"""
Test runner for qbit2track tests
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_complete_workflow import WorkflowTester

def main():
    """Run all tests"""
    print("qbit2track Test Runner")
    print("=" * 50)
    
    # Initialize workflow tester
    tester = WorkflowTester()
    
    try:
        # Run complete workflow test
        success = tester.run_complete_test()
        
        if success:
            print("\n✅ All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        return 1
    finally:
        # Always cleanup
        tester.cleanup()

if __name__ == "__main__":
    sys.exit(main())
