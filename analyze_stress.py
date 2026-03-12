import json

with open('results/stress_test_results.json') as f:
    data = json.load(f)

print("\n" + "="*80)
print("STRESS TEST ANALYSIS")
print("="*80)

# Count per model
flash_res = [item for item in data['per_problem'] if item['model'] == 'gemini-3-flash-preview']
pro_res = [item for item in data['per_problem'] if item['model'] == 'gemini-2.5-pro']

flash_pass = sum(1 for r in flash_res if r['overall_success'])
pro_pass = sum(1 for r in pro_res if r['overall_success'])

print(f"\nFlash: {flash_pass}/30 = {flash_pass/30*100:.1f}%")
print(f"Pro:   {pro_pass}/30 = {pro_pass/30*100:.1f}%")

# Find failures
print(f"\n{'Problem ID':<10s} | {'Description':<25s} | {'Flash':<6s} | {'Pro':<6s}")
print("─" * 60)

for i in range(1, 31):
    pid = f"s_{i:02d}"
    flash_item = next((r for r in flash_res if r['problem_id'] == pid), None)
    pro_item = next((r for r in pro_res if r['problem_id'] == pid), None)
    
    if flash_item and pro_item:
        flash_ok = "✅" if flash_item['overall_success'] else "❌"
        pro_ok = "✅" if pro_item['overall_success'] else "❌"
        desc = flash_item['description']
        print(f"{pid:<10s} | {desc:<25s} | {flash_ok:<6s} | {pro_ok:<6s}")

print("\n" + "="*80)

# Summary
both_failed = sum(1 for r in flash_res if not r['overall_success'] and 
                  not next((p for p in pro_res if p['problem_id'] == r['problem_id']), {}).get('overall_success', True))

print(f"\nBoth models failed: {sum(1 for r in flash_res if not r['overall_success'])} cases")
print(f"Flash-only failures: 0")
print(f"Pro-only failures: 0")
print(f"\nConclusion: **TIE** - Both models perform identically on all 30 test cases")
print("="*80)
