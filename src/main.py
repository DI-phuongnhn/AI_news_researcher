"""
AI News Researcher - Main Entry Point.

This is the central execution script for the AI News Research Agent. 
It initializes the orchestration pipeline, handles global error catching 
to ensure graceful exits, and provides basic terminal feedback for the 
ongoing research process.
"""

import os
import sys

# --- Environment Configuration ---
# We inject the project root into sys.path to allow the 'src' package 
# to be discoverable regardless of how the script is launched (e.g. from 
# terminal, vs-code runner, or cron job).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.pipeline import ResearchPipeline

def main():
    """
    Orchestration Entry Point.
    
    1. Initializes the ResearchPipeline instance.
    2. Triggers the .run() method which executes discovery -> fetching -> processing -> reporting.
    3. Logs success or failure metrics to the console.
    """
    print("--- Starting AI News Research Pipeline ---")
    
    # --- Block: Argument Parsing ---
    # Simple check for CLI flags.
    preview_mode = "--preview" in sys.argv
    
    try:
        # Initialize the stateful pipeline.
        pipeline = ResearchPipeline()
        
        # Execute the end-to-end flow.
        report = pipeline.run(preview_mode=preview_mode)
        
        # Log basic success metrics.
        processed_count = len(report.get('reports', []))
        
        if preview_mode:
            print(f"\n--- PREVIEW MODE: Processed {processed_count} items. Results saved in data/latest_news.json ---")
            print("--- Review the results and run without --preview to send to Teams. ---")
        else:
            print(f"--- Pipeline Finished Successfully. Processed {processed_count} items. ---")
            
    except Exception as e:
        print(f"--- FATAL ERROR: Pipeline execution halted: {str(e)} ---")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
