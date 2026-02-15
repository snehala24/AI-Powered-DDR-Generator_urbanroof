from ddr_generator.main import DDRPipeline
import sys
import os

print(f"Loading from: {os.path.abspath('ddr_generator/main.py')}")

try:
    pipeline = DDRPipeline()
    print("Pipeline instantiated")
    print(f"Has process? {hasattr(pipeline, 'process')}")
    print(f"Has process_files? {hasattr(pipeline, 'process_files')}")
    
    # Check source code of process
    import inspect
    print("\nSource of process:")
    print(inspect.getsource(pipeline.process))
except Exception as e:
    print(f"Error: {e}")
