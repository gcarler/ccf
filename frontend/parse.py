import json
import sys


def main():
    try:
        with open("eslint_report.json", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading json: {e}")
        try:
            with open("eslint_report.json", encoding="utf-16le") as f:
                data = json.load(f)
        except Exception as e2:
            print(f"Error loading json utf-16: {e2}")
            return

    for entry in data:
        if entry["errorCount"] > 0 or entry["warningCount"] > 0:
            print(entry["filePath"])
            for msg in entry["messages"]:
                severity = "Error" if msg["severity"] == 2 else "Warning"
                print(
                    f"  {msg.get('line', '?')}:{msg.get('column', '?')} {severity} {msg.get('message')} ({msg.get('ruleId')})"
                )


if __name__ == "__main__":
    main()
