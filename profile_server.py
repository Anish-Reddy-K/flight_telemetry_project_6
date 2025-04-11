"""
This file will profile the entire server.py line by line.
Save this as profile_server.py and run it with: python profile_server.py
"""
from memory_profiler import LineProfiler
import server  # Import the original server.py module

# Create a LineProfiler object
profile = LineProfiler()

# Add all functions from the server module to be profiled
profile.add_module(server)

# Wrap the main function with the profiler
wrapped_start_server = profile(server.start_server)

# Run the wrapped function
try:
    wrapped_start_server()
except KeyboardInterrupt:
    # Allow clean exit with Ctrl+C
    pass
finally:
    # Print the profiling results
    profile.print_stats()
    
    # Optionally save results to a file
    with open('memory_profile_results.txt', 'w') as f:
        profile.print_stats(stream=f)
        print("Detailed memory profile saved to memory_profile_results.txt")