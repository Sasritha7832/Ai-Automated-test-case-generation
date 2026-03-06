import subprocess
result = subprocess.run(["python", "test_pipeline.py"], capture_output=True, text=True)
with open("captured_error.log", "w", encoding="utf-8") as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\nSTDERR:\n")
    f.write(result.stderr)
print("Log written to captured_error.log")
