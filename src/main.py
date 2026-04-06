"""
AI News Researcher - Main Entry Point.
This is the slim orchestrator that initializes and runs the ResearchPipeline.
"""

import os
import sys

# Ensure project root is in sys.path for 'src' package resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.pipeline import ResearchPipeline

def main():
    """
    Main entry point for the AI News Research Agent.
    """
    print("--- Starting AI News Research Pipeline ---")
    try:
        pipeline = ResearchPipeline()
        report = pipeline.run()
        print(f"--- Pipeline Finished Successfully. Processed {len(report.get('reports', []))} items. ---")
    except Exception as e:
        print(f"--- ERROR: Pipeline failed: {str(e)} ---")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
