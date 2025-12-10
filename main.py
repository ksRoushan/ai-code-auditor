import json
import os
# Ensure this import matches your filename
from graphs.full_pipeline import build_full_pipeline

# Build the graph
app = build_full_pipeline()

print("🚀 Starting Autonomous Code Review Pipeline...")
print("------------------------------------------------")
print("1️⃣  Repo Reader")
print("2️⃣  Static Analyzer")
print("3️⃣  LLM Architect")
print("4️⃣  Issue Categorizer")
print("5️⃣  Priority Agent")
print("6️⃣  Final Aggregator")
print("------------------------------------------------\n")

# Run!
result = app.invoke({
    "repo_input": r"C:\Users\rksin\OneDrive\Desktop\lang_graph_tut\test_file.zip"
})

# Extract final clean output
final_report = result.get("final_output", {})

print("\n✨ PIPELINE FINISHED! HERE IS THE JSON REPORT:\n")
print(json.dumps(final_report, indent=2))

# Optional: Save to file
with open("audit_report.json", "w") as f:
    json.dump(final_report, f, indent=2)
print("\n✅ Report saved to audit_report.json")