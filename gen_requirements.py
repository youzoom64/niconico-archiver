import os
import re
import sys

def collect_imports_from_file(filepath):
    imports = set()
    pattern = re.compile(r'^(?:from|import)\s+([a-zA-Z0-9_\.]+)')
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            m = pattern.match(line)
            if m:
                module = m.group(1).split('.')[0]  # サブモジュールを切り落とす
                imports.add(module)
    return imports

def main():
    py_files = [f for f in os.listdir('.') if f.endswith('.py')]
    all_imports = set()

    for py in py_files:
        all_imports |= collect_imports_from_file(py)

    # 標準ライブラリ一覧（Python3.10+）
    stdlib_modules = set(sys.stdlib_module_names)

    # 外部モジュールだけに絞る
    external_modules = sorted(all_imports - stdlib_modules)

    with open('requirements.txt', 'w', encoding='utf-8') as f:
        for module in external_modules:
            f.write(module + '\n')

    print("requirements.txt を作成しました。")

if __name__ == "__main__":
    main()
