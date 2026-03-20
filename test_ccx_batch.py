#!/usr/bin/env python3
"""Batch test script for ccx_2.23.test files"""
import subprocess
import os
import sys
from pathlib import Path

TEST_DIR = Path("ccx_2.23.test/CalculiX/ccx_2.23/test")
PYTHON = "C:/Users/yd576/AppData/Local/Programs/Python/Python310/python.exe"
MAIN = "cae/main.py"

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

def run_cmd(args, timeout=30):
    try:
        r = subprocess.run(
            [PYTHON] + args,
            capture_output=True, text=True, timeout=timeout,
            env=env, encoding="utf-8", errors="replace"
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -2, "", str(e)

def test_inp_info(f):
    code, out, err = run_cmd([MAIN, "inp", "info", str(f)], timeout=10)
    if code == 0 and "关键词统计" in out:
        return "OK", out
    return "FAIL", err[:100]

def test_solve(f, out_dir):
    code, out, err = run_cmd([MAIN, "solve", str(f), "-o", str(out_dir)], timeout=60)
    if code == 0 and "求解完成" in out:
        return "OK", out
    return "FAIL", err[:200] if err else out[:200]

def test_convert(frd_file):
    code, out, err = run_cmd([MAIN, "convert", str(frd_file)], timeout=30)
    if code == 0 and "转换完成" in out:
        return "OK", out
    return "FAIL", err[:100] if err else out[:100]

def main():
    inp_files = sorted(TEST_DIR.glob("*.inp"))
    print(f"Found {len(inp_files)} .inp files in {TEST_DIR}")
    print()

    # Phase 1: Test inp info on all files
    print("=" * 60)
    print("Phase 1: Testing inp info on all files...")
    print("=" * 60)
    results = {"OK": [], "FAIL": []}
    for i, f in enumerate(inp_files):
        status, msg = test_inp_info(f)
        results[status].append(f.name)
        if status == "OK":
            print(f"  [{i+1}/{len(inp_files)}] OK: {f.name}")
        else:
            print(f"  [{i+1}/{len(inp_files)}] FAIL: {f.name} - {msg}")
    print(f"\nPhase 1 Results: OK={len(results['OK'])}, FAIL={len(results['FAIL'])}")

    # Phase 2: Test solve on sample files
    print()
    print("=" * 60)
    print("Phase 2: Testing solve on sample files (10)...")
    print("=" * 60)
    sample = results["OK"][:10]
    solve_results = {"OK": [], "FAIL": []}
    for i, name in enumerate(sample):
        f = TEST_DIR / name
        out_dir = Path("results_test") / f.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        status, msg = test_solve(f, out_dir)
        solve_results[status].append(name)
        print(f"  [{i+1}/10] {name}: {status}")
        if status == "FAIL":
            print(f"       {msg[:150]}")

        # Clean up results
        if status == "OK":
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)

    print(f"\nPhase 2 Results: OK={len(solve_results['OK'])}, FAIL={len(solve_results['FAIL'])}")

    # Phase 3: Test convert on solved files
    print()
    print("=" * 60)
    print("Phase 3: Testing convert on solved files...")
    print("=" * 60)
    # Solve first, then convert
    convert_results = {"OK": [], "FAIL": []}
    for i, name in enumerate(sample):
        f = TEST_DIR / name
        out_dir = Path("results_test") / f.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        # Solve first
        status, _ = test_solve(f, out_dir)
        if status != "OK":
            convert_results["FAIL"].append(name)
            print(f"  [{i+1}/10] SKIP (solve failed): {name}")
            continue

        # Find frd file
        frd_files = list(out_dir.glob("*.frd"))
        if not frd_files:
            convert_results["FAIL"].append(name)
            print(f"  [{i+1}/10] SKIP (no frd): {name}")
            continue

        # Convert
        status, msg = test_convert(frd_files[0])
        convert_results[status].append(name)
        print(f"  [{i+1}/10] {name}: {status}")
        if status == "FAIL":
            print(f"       {msg[:150]}")

        # Clean up
        import shutil
        shutil.rmtree(out_dir, ignore_errors=True)

    print(f"\nPhase 3 Results: OK={len(convert_results['OK'])}, FAIL={len(convert_results['FAIL'])}")

    # Final Summary
    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total files tested: {len(inp_files)}")
    print(f"Phase 1 (inp info): OK={len(results['OK'])}, FAIL={len(results['FAIL'])}")
    print(f"Phase 2 (solve):     OK={len(solve_results['OK'])}, FAIL={len(solve_results['FAIL'])}")
    print(f"Phase 3 (convert):   OK={len(convert_results['OK'])}, FAIL={len(convert_results['FAIL'])}")

    if results["FAIL"]:
        print(f"\nFailed inp info files:")
        for name in results["FAIL"][:10]:
            print(f"  - {name}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
